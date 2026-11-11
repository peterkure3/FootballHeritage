"""Schedules retain scope, exact UTC identity and verified final-score evidence."""
from datetime import date, datetime, timedelta, timezone
from unittest import TestCase
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from api.sport_schedule import build_schedule
from api.routers.sport_schedule import router
from sync.gateway import contract, PREWARM

NOW = datetime(2026, 11, 11, 12, tzinfo=timezone.utc)
START, END = date(2026, 11, 10), date(2026, 11, 13)


def upcoming(**changes):
    return {'sport': 'nba', 'fixture_id': 'source:a', 'home_team': 'Los Angeles Lakers',
            'away_team': 'Boston Celtics', 'kickoff': (NOW + timedelta(hours=8)).isoformat(),
            'competition': 'NBA', 'status': 'SCHEDULED', **changes}


def final(**changes):
    return {'league': 'basketball_nba', 'home_team': 'Atlanta Hawks', 'away_team': 'Los Angeles Lakers',
            'date': (NOW - timedelta(days=1)).isoformat(), 'result_available_at': NOW.isoformat(),
            'completed': True, 'date_precision': 'TIMESTAMP', 'home_score': 114, 'away_score': 124, **changes}


class SportScheduleTests(TestCase):
    def test_scoped_upcoming_and_verified_finals_are_sorted(self):
        result = build_schedule('nba', [upcoming(), upcoming(sport='wnba')],
                                [final(), final(league='basketball_ncaab')], START, END, NOW)
        self.assertEqual(len(result['items']), 2)
        self.assertEqual([row['status'] for row in result['items']], ['FINISHED', 'SCHEDULED'])
        self.assertEqual(result['items'][0]['away_score'], 124)

    def test_aliases_and_offsets_merge_without_merging_rematches(self):
        result = build_schedule('nba', [upcoming(), upcoming(fixture_id='b', home_team='LA Lakers',
            kickoff='2026-11-11T23:00:00+03:00'), upcoming(kickoff='2026-11-12T20:00:00Z')], [], START, END, NOW)
        self.assertEqual(len(result['items']), 2)
        self.assertNotEqual(result['items'][0]['id'], result['items'][1]['id'])

    def test_repeated_finals_merge_and_conflicts_are_quarantined(self):
        result = build_schedule('nba', [], [final(), final()], START, END, NOW)
        self.assertEqual(len(result['items']), 1)
        result = build_schedule('nba', [], [final(), final(home_score=115)], START, END, NOW)
        self.assertEqual(result['items'], [])
        self.assertEqual(result['excluded_conflicting_finals'], 1)

    def test_invalid_unobserved_or_day_precision_finals_are_excluded(self):
        invalid = [final(completed=False), final(date_precision='DAY'), final(home_score=float('nan')),
                   final(away_score=True), final(home_score=-1), final(home_score=114.5),
                   final(result_available_at=None), final(result_available_at=(NOW + timedelta(seconds=1)).isoformat()),
                   final(home_team=''), final(home_team='Los Angeles Lakers'), final(home_score=124)]
        self.assertEqual(build_schedule('nba', [], invalid, START, END, NOW)['items'], [])

    def test_date_boundaries_and_started_schedules_are_excluded(self):
        rows = [upcoming(kickoff=NOW.isoformat()), upcoming(kickoff='invalid'),
                upcoming(kickoff='2026-11-14T00:00:00Z'), upcoming(home_team='Boston Celtics')]
        self.assertEqual(build_schedule('nba', rows, [], START, END, NOW)['items'], [])

    def test_http_date_validation_partial_coverage_and_manifest(self):
        app = FastAPI()
        app.include_router(router)
        with TestClient(app) as client, patch('api.routers.sport_schedule.read_snapshot', return_value={'fixtures': []}), \
                patch('api.routers.sport_schedule.load_recent_results', return_value=[]):
            self.assertEqual(client.get('/sport-schedule/nba?start_date=2026-11-11&end_date=2026-11-10').status_code, 422)
            self.assertEqual(client.get('/sport-schedule/nba?start_date=2026-10-01&end_date=2026-12-01').status_code, 422)
            self.assertEqual(client.get('/sport-schedule/nba?start_date=not-a-date').status_code, 422)
            self.assertEqual(client.get('/sport-schedule/unknown').status_code, 404)
            self.assertEqual(client.get('/sport-schedule/nba').json()['sport'], 'nba')
            with patch('api.routers.sport_schedule.read_snapshot', side_effect=HTTPException(503)):
                self.assertEqual(len(client.get('/sport-schedule/nba').json()['source_issues']), 1)
                with patch('api.routers.sport_schedule.load_recent_results', side_effect=ValueError):
                    self.assertEqual(client.get('/sport-schedule/nba').status_code, 503)
        self.assertFalse(contract('GET', 'sport-schedule/nba')['side_effect'])
        self.assertTrue(any(path == 'sport-schedule/nba' for path, _ in PREWARM))
