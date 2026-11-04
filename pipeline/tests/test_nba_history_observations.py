from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.merge_nba_research_history import combine, load_capture, run


class NbaHistoryObservationsTests(unittest.TestCase):
    def capture(self, day, score=100):
        return {'created_at': f'2020-01-{day:02d}T12:00:00Z', 'reference': {'directory': str(day)}, 'rows': [{
            'provider_event_id': '1', 'date': '2020-01-01T00:00:00Z', 'league': 'basketball_nba',
            'home_team': 'A', 'away_team': 'B', 'home_score': score, 'away_score': 90, 'completed': True,
            'result_available_at': f'2020-01-{day:02d}T11:00:00Z'}]}

    def test_unchanged_result_retains_first_verified_availability(self):
        rows, summary = combine([self.capture(3), self.capture(2)])
        self.assertEqual(rows[0]['result_available_at'], '2020-01-02T11:00:00Z')
        self.assertEqual(rows[0]['first_observation_capture']['directory'], '2')
        self.assertEqual(summary['earlier_times_preserved'], 1)

    def test_correction_and_reversion_cannot_inherit_old_availability(self):
        rows, summary = combine([self.capture(2), self.capture(3, 101), self.capture(4)])
        self.assertEqual(rows[0]['result_available_at'], '2020-01-04T11:00:00Z')
        self.assertEqual(len(summary['revisions']), 2)
        with self.assertRaisesRegex(ValueError, 'correction'):
            combine([self.capture(2), self.capture(2, 101)])

    def test_new_exclusion_quarantines_previously_accepted_result(self):
        excluded = self.capture(3); excluded['rows'] = []
        excluded['excluded'] = [{'id': '1', 'reason': 'independent_score_disagreement'}]
        rows, summary = combine([self.capture(2), excluded])
        self.assertEqual(rows, [])
        self.assertEqual(summary['quarantined'][0]['id'], '1')

    def test_duplicates_and_naive_observations_fail(self):
        duplicate = self.capture(2); duplicate['rows'] *= 2
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            combine([duplicate])
        naive = self.capture(2); naive['rows'][0]['result_available_at'] = '2020-01-02T11:00:00'
        with self.assertRaisesRegex(ValueError, 'timezone'):
            combine([naive])

    def test_merge_keeps_verifiable_source_links_and_rejects_modified_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); folders = []
            for day in [2, 3]:
                folder = root/str(day); folder.mkdir(); folders.append(folder)
                normalized = folder/'reconciled.jsonl'
                normalized.write_text(json.dumps(self.capture(day)['rows'][0])+'\n')
                (folder/'raw.json').write_text('{}')
                manifest = {'kind': 'nba_history_observations_v1', 'created_at': self.capture(day)['created_at'],
                    'normalized_sha256': hashlib.sha256(normalized.read_bytes()).hexdigest(), 'sources': [
                        {'file': 'raw.json', 'sha256': hashlib.sha256((folder/'raw.json').read_bytes()).hexdigest()}]}
                (folder/'manifest.json').write_text(json.dumps(manifest))
            run(folders, root/'merged')
            loaded, _ = load_capture(root/'merged')
            self.assertEqual(loaded['rows'][0]['result_available_at'], '2020-01-02T11:00:00Z')
            (folders[0]/'raw.json').write_text('{"modified":true}')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                load_capture(root/'merged')
