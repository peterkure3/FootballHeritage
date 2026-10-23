import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import refresh_regional_pipeline as refresh


class TrialContinuationWindowTests(unittest.TestCase):
    def test_future_trials_stay_pending_without_provider_result_requests(self):
        day = (datetime.now(timezone.utc) + timedelta(days=2)).date().isoformat()
        trial = {'pending_forecasts': 1, 'trial_sha256': 'trial',
                 'fixtures': [{'kickoff': day + 'T14:00:00Z', 'status': 'recorded_pregame'}]}
        with patch.object(refresh, 'dashboard', return_value={'trials': [trial]}), \
                patch.object(refresh, 'collect_results') as collect, \
                patch.object(refresh, 'settle_directory', return_value={'pending_forecasts': 1}) as settle:
            result = refresh.refresh_trial_results()
        collect.assert_not_called()
        self.assertEqual(settle.call_args.args[1], [])
        self.assertEqual(result['provider_errors'], {})

    def test_upcoming_days_are_unique_bounded_and_primary_only(self):
        base = {'bookmaker': 'bovada', 'country': 'England', 'competition': 'Premier League'}
        records = [base | {'commence_time': day + 'T14:00:00Z'}
                   for day in ['2026-10-14', '2026-10-15', '2026-10-17', '2026-10-17', '2026-10-29', '2026-10-30']]
        records += [base | {'bookmaker': 'betpawa', 'commence_time': '2026-10-16T14:00:00Z'},
                    base | {'competition': 'Other', 'commence_time': '2026-10-16T14:00:00Z'}]
        with TemporaryDirectory() as temporary:
            capture = Path(temporary)
            (capture / 'odds_snapshots.jsonl').write_text('\n'.join(map(json.dumps, records)), encoding='utf-8')
            with patch.object(refresh, 'continue_frozen_trial', return_value={'status': 'recorded'}) as record:
                result = refresh.continue_upcoming_trials(capture, capture, '2026-10-15', 'stamp')
            self.assertEqual([row['match_date'] for row in result], ['2026-10-15', '2026-10-17', '2026-10-29'])
            self.assertEqual(record.call_count, 3)
            self.assertEqual(len({call.args[3] for call in record.call_args_list}), 3)


if __name__ == '__main__':
    unittest.main()
