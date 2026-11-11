"""Duplicate provider rows must not become duplicate NBA grid entries."""
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.betting_intel import build_intelligence, merge_fixtures
from api.routers.betting_intel import router


NOW = datetime(2026, 11, 11, 10, tzinfo=timezone.utc)


def game(fixture_id='provider:a', **changes):
    return {
        'fixture_id': fixture_id, 'sport': 'nba', 'competition': 'NBA',
        'home_team': 'Los Angeles Lakers', 'away_team': 'Boston Celtics',
        'kickoff': (NOW + timedelta(hours=8)).isoformat(), 'status': 'SCHEDULED',
        'settlement_rule': 'INCLUDING_OVERTIME', 'offers': [], **changes,
    }


def offers(book='a', prices=(2.0, 2.0), age=60):
    return [{'bookmaker': book, 'market': 'h2h', 'selection': selection,
             'decimal_odds': price, 'observed_at': (NOW - timedelta(seconds=age)).isoformat()}
            for selection, price in zip(('home_win', 'away_win'), prices)]


def forecast(age=60, probabilities=None):
    return {'probabilities': probabilities or {'home_win': .6, 'away_win': .4},
            'generated_at': (NOW - timedelta(seconds=age)).isoformat(),
            'settlement_rule': 'INCLUDING_OVERTIME', 'model_version': 'test-only',
            'status': 'candidate_preview'}


class NbaGridDuplicateTests(unittest.TestCase):
    def test_saved_duplicate_snapshot_is_deduplicated_over_http(self):
        row = game(offers=offers(), prediction=forecast())
        app = FastAPI()
        app.include_router(router)
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / 'snapshot.json'
            snapshot.write_text(json.dumps({'schema_version': 1, 'snapshot_at': NOW.isoformat(),
                                           'fixtures': [row, row]}), encoding='utf-8')
            with patch('api.routers.betting_intel.SNAPSHOT_PATH', snapshot), \
                    patch('api.routers.betting_intel.datetime') as clock, TestClient(app) as client:
                clock.now.return_value = NOW
                response = client.get('/betting-intel/nba')
                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertEqual(payload['summary']['fixtures'], 1)
                self.assertEqual(len(payload['predictions']), 1)
                self.assertEqual(len(payload['devigged_odds']), 1)
                overview = client.get('/betting-intel').json()
                nba = next(row for row in overview['sports'] if row['sport'] == 'nba')
                self.assertEqual(nba['summary'], payload['summary'])

    def test_repeated_provider_rows_produce_one_game_and_one_quote(self):
        row = game(offers=offers(), prediction=forecast())
        before = copy.deepcopy(row)
        result = build_intelligence('nba', [row, copy.deepcopy(row)], NOW)
        for section in ('predictions', 'ai_picks', 'devigged_odds'):
            self.assertEqual(len(result[section]), 1)
        self.assertEqual(result['summary']['fixtures'], 1)
        self.assertEqual(row, before)

    def test_aliases_and_equivalent_utc_times_merge_without_losing_books(self):
        rows = [game(offers=offers('a')), game('provider:b', home_team=' LA Lakers ',
                kickoff='2026-11-11T21:00:00+03:00', offers=offers('b'))]
        result = build_intelligence('nba', rows, NOW)
        self.assertEqual(result['summary']['fixtures'], 1)
        self.assertEqual({row['bookmaker'] for row in result['devigged_odds']}, {'a', 'b'})
        self.assertEqual({row['fixture_id'] for row in result['devigged_odds']}, {'provider:a'})

    def test_rematches_orientation_and_settlement_remain_distinct(self):
        rows = [game(), game('later', kickoff=(NOW + timedelta(days=1)).isoformat()),
                game('reversed', home_team='Boston Celtics', away_team='Los Angeles Lakers'),
                game('regulation', settlement_rule='REGULATION_ONLY')]
        self.assertEqual(len(merge_fixtures(rows)), 4)
        self.assertEqual(build_intelligence('nba', rows, NOW)['summary']['fixtures'], 4)

    def test_latest_valid_prediction_survives_duplicate_order(self):
        rows = [game(), game('old', prediction=forecast(age=120)),
                game('latest', prediction=forecast()),
                game('invalid', prediction=forecast(age=-60))]
        for ordered in (rows, list(reversed(rows))):
            result = build_intelligence('nba', ordered, NOW)
            self.assertEqual(len(result['predictions']), 1)
            self.assertEqual(result['predictions'][0]['generated_at'], forecast()['generated_at'])

    def test_conflicting_same_time_prices_are_still_rejected(self):
        result = build_intelligence('nba', [game(offers=offers()),
                    game('other', offers=offers(prices=(2.5, 1.8)))], NOW)
        self.assertEqual(result['summary']['fixtures'], 1)
        self.assertEqual(result['devigged_odds'], [])

    def test_newest_prices_replace_older_duplicate_evidence(self):
        result = build_intelligence('nba', [game(offers=offers(age=120)),
                    game('other', offers=offers(prices=(2.5, 1.8)))], NOW)
        self.assertEqual(len(result['devigged_odds']), 1)
        self.assertEqual(result['devigged_odds'][0]['legs']['home_win']['decimal_odds'], 2.5)

    def test_ineligible_rows_do_not_contribute_prices_or_forecasts(self):
        rows = [game(), game('cancelled', status='CANCELLED', offers=offers(), prediction=forecast()),
                game('foreign', sport='wnba'), game('invalid', kickoff='invalid')]
        result = build_intelligence('nba', rows, NOW)
        self.assertEqual(result['summary']['fixtures'], 1)
        self.assertEqual(result['devigged_odds'], [])
        self.assertEqual(result['predictions'], [])


if __name__ == '__main__':
    unittest.main()
