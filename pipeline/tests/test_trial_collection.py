import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import pandas as pd
from unittest.mock import patch
from unittest.mock import MagicMock

from scripts import run_trial_collection as job
from scripts import refresh_trial_fixtures as fixtures


class TrialCollectionTests(unittest.TestCase):
    def response(self, status='TIMED', competition='PL'):
        response = MagicMock(status_code=200)
        payload = {'matches': [{'id': 1, 'competition': {'code': competition, 'name': 'Premier League'},
            'utcDate': '2026-10-10T14:00:00Z', 'status': status,
            'homeTeam': {'name': 'Arsenal FC'}, 'awayTeam': {'name': 'Leeds United FC'},
            'season': {'startDate': '2026-08-01'},
            'score': {'fullTime': {'home': 1, 'away': 0}}}]}
        response.json.return_value = payload
        response.content = json.dumps(payload).encode()
        return response

    def test_fixture_refresh_is_bounded_and_does_not_label_unfinished_scores(self):
        with TemporaryDirectory() as root, patch.object(fixtures, 'RAW_DATA_DIR', Path(root)), \
                patch.object(fixtures.requests, 'Session') as session, \
                patch.object(fixtures, 'upsert_matches') as upsert:
            get = session.return_value.__enter__.return_value.get
            get.return_value = self.response('IN_PLAY')
            report = fixtures.run()
            self.assertEqual(report['fixtures'], 1)
            self.assertTrue(get.call_args.args[0].endswith('/competitions/PL/matches'))
            frame = upsert.call_args.args[0]
            self.assertTrue(pd.isna(frame.iloc[0].result))
            self.assertTrue(frame.iloc[0].home_score != frame.iloc[0].home_score)

    def test_fixture_refresh_rejects_wrong_competition_before_database_write(self):
        with patch.object(fixtures.requests, 'Session') as session, \
                patch.object(fixtures, 'upsert_matches') as upsert:
            session.return_value.__enter__.return_value.get.return_value = self.response(competition='PD')
            with self.assertRaises(ValueError):
                fixtures.run()
            upsert.assert_not_called()

    def test_lock_prevents_overlap_and_releases_after_exit(self):
        with TemporaryDirectory() as root:
            path = Path(root) / 'lock'
            with job.exclusive_run(path) as first:
                self.assertTrue(first)
                with job.exclusive_run(path) as second:
                    self.assertFalse(second)
            with job.exclusive_run(path) as again:
                self.assertTrue(again)

    def test_ingestion_once_per_utc_day_and_failure_health(self):
        with TemporaryDirectory() as root, patch.object(job, 'LOGS', Path(root)), \
                patch.object(job, 'execute', return_value=True) as execute:
            self.assertEqual(job.main(), 0)
            self.assertEqual(execute.call_count, 3)
            execute.reset_mock()
            self.assertEqual(job.main(), 0)
            self.assertEqual(execute.call_count, 2)
            execute.side_effect = [False, True]
            self.assertEqual(job.main(), 1)
            state = json.loads((Path(root) / 'edge_trial_status.json').read_text())
            self.assertEqual(state['outcome'], 'failed')
            self.assertTrue(state['last_success_at'])
            self.assertEqual(state['failed_steps'], ['scripts.refresh_regional_pipeline'])

    def test_ingestion_failure_does_not_skip_settlement_and_assessment(self):
        with TemporaryDirectory() as root, patch.object(job, 'LOGS', Path(root)), \
                patch.object(job, 'execute', side_effect=[False, True, True]) as execute:
            self.assertEqual(job.main(), 1)
            self.assertEqual([c.args[0] for c in execute.call_args_list],
                ['scripts.refresh_trial_fixtures', 'scripts.refresh_regional_pipeline', 'scripts.assess_paper_trial'])


if __name__ == '__main__':
    unittest.main()
