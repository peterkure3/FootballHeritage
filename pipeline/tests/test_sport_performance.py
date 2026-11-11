"""Settlement evidence, denominator and gateway contracts for basketball history."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.sport_performance import evaluate, read_forecasts, retain
from api.routers.betting_intel import router
from sync.gateway import contract

NOW = datetime(2026, 11, 8, tzinfo=timezone.utc)
TIP = NOW - timedelta(days=2)


def forecast(sport='nba', **changes):
    row = {'fixture_id': 'source:one', 'sport': sport, 'home_team': 'Home', 'away_team': 'Away',
           'kickoff': TIP.isoformat(), 'recorded_at': (TIP - timedelta(hours=1)).isoformat(),
           'settlement_rule': 'INCLUDING_OVERTIME', 'prediction': {
               'generated_at': (TIP - timedelta(hours=2)).isoformat(), 'model_version': 'candidate-1',
               'probabilities': {'home_win': .75, 'away_win': .25}, 'winner': 'home_win', 'status': 'candidate_preview'}}
    row.update(changes)
    return row


def final(sport='nba', **changes):
    row = {'date': TIP.isoformat(), 'home_team': 'Home', 'away_team': 'Away',
           'league': 'basketball_nba' if sport == 'nba' else 'basketball_ncaab',
           'completed': True, 'date_precision': 'TIMESTAMP', 'settlement_rule': 'INCLUDING_OVERTIME',
           'result_available_at': (TIP + timedelta(hours=4)).isoformat(), 'home_score': 110, 'away_score': 105}
    row.update(changes)
    return row


class SportPerformanceTests(unittest.TestCase):
    def test_sport_isolation_and_two_way_probability_scores(self):
        for sport in ['nba', 'ncaab']:
            data = evaluate(sport, [forecast('nba'), forecast('ncaab')], [final('nba'), final('ncaab')], NOW)
            self.assertEqual(data['sport'], sport)
            self.assertEqual(data['summary']['total_predictions'], 1)
            self.assertEqual(data['summary']['overall_accuracy'], 100)
            self.assertAlmostEqual(data['summary']['brier_score'], .125)
            self.assertIsNone(data['history']['predictions'][0]['draw_prob'])

    def test_no_pregame_record_or_invalid_probabilities_never_score(self):
        bad = []
        for field, value in [('recorded_at', TIP.isoformat()), ('recorded_at', (NOW + timedelta(days=1)).isoformat())]:
            bad.append(forecast(**{field: value}))
        for changes in [{'generated_at': TIP.isoformat()}, {'probabilities': {'home_win': .8, 'away_win': .8}},
                        {'feature_cutoff': NOW.isoformat()}, {'probabilities': {'home_win': float('nan'), 'away_win': .2}}]:
            row = forecast()
            row['prediction'].update(changes)
            bad.append(row)
        data = evaluate('nba', bad, [final()], NOW)
        self.assertEqual(data['summary']['total_predictions'], 0)
        self.assertIsNone(data['summary']['log_loss'])
        self.assertEqual(data['summary']['excluded']['invalid_forecast'], len(bad))

    def test_pending_ambiguous_ties_and_imprecise_results_do_not_count(self):
        for results, reason in [([], 'pending'), ([final(), final(home_score=111)], 'ambiguous_result'),
                                ([final(home_score=105)], 'invalid_result'),
                                ([final(completed=False)], 'pending'), ([final(date_precision='DAY')], 'pending'),
                                ([final(settlement_rule='REGULATION_TIME')], 'pending'),
                                ([final(result_available_at=(NOW + timedelta(days=1)).isoformat())], 'pending'),
                                ([final(date=(TIP + timedelta(minutes=1)).isoformat())], 'pending')]:
            data = evaluate('nba', [forecast()], results, NOW)
            self.assertEqual(data['summary']['total_predictions'], 0)
            self.assertEqual(data['summary']['excluded'][reason], 1)

    def test_duplicates_latest_model_and_table_filter_preserve_denominator(self):
        first = forecast()
        latest = deepcopy(first)
        latest['prediction'].update(generated_at=(TIP - timedelta(minutes=90)).isoformat(), model_version='candidate-2', winner='away_win')
        other = forecast(home_team='Another')
        rows = [first, deepcopy(first), latest, other]
        results = [final(), final(home_team='Another')]
        data = evaluate('nba', rows, results, NOW, result_filter='correct', page_size=1)
        self.assertEqual(data['summary']['total_predictions'], 2)
        self.assertEqual(data['summary']['overall_accuracy'], 50)
        self.assertEqual(data['history']['total_count'], 1)
        data = evaluate('nba', rows, results, NOW, model_version='candidate-1')
        self.assertEqual(data['summary']['overall_accuracy'], 100)
        self.assertEqual(data['summary']['total_predictions'], 2)
        self.assertEqual(evaluate('nba', rows, results, NOW, days=1)['summary']['total_predictions'], 0)

    def test_same_version_same_timestamp_conflict_is_quarantined(self):
        row = forecast()
        conflict = deepcopy(row)
        conflict['prediction']['probabilities'] = {'home_win': .5, 'away_win': .5}
        data = evaluate('nba', [row, conflict], [final()], NOW)
        self.assertEqual(data['summary']['total_predictions'], 0)

    def test_retention_cannot_backdate_and_hash_tampering_fails(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            retain({'fixtures': [forecast('ncaab')]}, root, NOW)
            self.assertEqual(list(root.glob('*.json')), [])
            retain({'fixtures': [forecast('ncaab')]}, root, TIP - timedelta(minutes=30))
            self.assertEqual(len(read_forecasts('ncaab', root)), 1)
            path = next(root.glob('*.json'))
            path.write_bytes(path.read_bytes() + b' ')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                read_forecasts('ncaab', root)

    def test_http_and_gateway_validate_scope_and_filters(self):
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        for sport in ['nba', 'ncaab']:
            rule = contract('GET', f'betting-intel/{sport}/settled-performance')
            self.assertFalse(rule['side_effect'])
            with patch('api.sport_performance.feed', return_value={'sport': sport}) as read:
                response = client.get(f'/betting-intel/{sport}/settled-performance?page=2&result_filter=incorrect')
                self.assertEqual(response.json()['sport'], sport)
                self.assertEqual(read.call_args.kwargs['page'], 2)
        self.assertEqual(client.get('/betting-intel/football/settled-performance').status_code, 404)
        self.assertEqual(client.get('/betting-intel/nba/settled-performance?page_size=0').status_code, 422)
        self.assertEqual(client.get('/betting-intel/nba/settled-performance?start_date=2026-11-09&end_date=2026-11-01').status_code, 422)
