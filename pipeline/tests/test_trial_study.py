from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from models.paper_trial import dashboard, import_trial, settle, settle_directory
from models.trial_study import PROTOCOL, assess, assess_once, digest, studies
from scripts.record_edge_trial import price_analysis
from scripts.assess_paper_trial import verify_result_sources


def batch(days=60, per_day=4, win=True):
    start = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    policy = {'minimum_stressed_ev': .05, 'payout_haircut': .02, 'units_per_selection': 1,
        'max_selections_per_fixture': 1, 'settlement': 'REGULATION_TIME',
        'selection': 'largest_stressed_ev', 'max_quote_age_seconds': 900, 'no_threshold_tuning': True}
    trial = {'candidate_id': 'frozen', 'candidate_checksums': {k: 'a' * 64 for k in
        ['dataset.parquet', 'model_v2.1.0.pkl', 'metrics_v2.1.0.json']}, 'policy': policy,
        'status': 'prospective_paper_trial', 'profitable_edge_established': False,
        'limits': [], 'fixtures': []}
    results = []
    for day in range(days):
        kickoff = start + timedelta(days=day)
        for fixture in range(per_day):
            home, away = f'Home {day} {fixture}', f'Away {day} {fixture}'
            row = {'home': home, 'away': away, 'kickoff': kickoff.isoformat(),
                'observed_at': (kickoff - timedelta(minutes=10)).isoformat(),
                'generated_at': (kickoff - timedelta(minutes=9)).isoformat(),
                'bookmaker': 'bovada', 'selected_outcome': 'home_win', 'status': 'recorded_pregame',
                'outcomes': price_analysis({'home_win': .6, 'draw': .2, 'away_win': .2},
                    {'home_win': 2., 'draw': 3.5, 'away_win': 4.})}
            trial['fixtures'].append(row)
            results.append({'home_team': home, 'away_team': away, 'commence_time': kickoff.isoformat(),
                'home_score': 2 if win else 0, 'away_score': 0 if win else 2,
                'status': 'FINISHED', 'settlement_rule': 'REGULATION_TIME',
                'observed_at': (kickoff + timedelta(hours=3)).isoformat(), 'source_url': 'https://example.org/result'})
    return {'trial': trial, 'receipt': settle(trial, results), 'trial_sha256': digest(trial)}


class TrialStudyTests(unittest.TestCase):
    def test_formal_source_check_rejects_changed_capture_or_score(self):
        entry = studies([batch(1, 1)])[0]['entries'][0]
        source = entry['settlement']['result_source']
        event = {'id': 42, 'status': 'FINISHED', 'utcDate': source['commence_time'],
            'homeTeam': {'name': source['home_team']}, 'awayTeam': {'name': source['away_team']},
            'score': {'duration': 'REGULAR', 'fullTime': {'home': source['home_score'], 'away': source['away_score']}}}
        with TemporaryDirectory() as root:
            path = Path(root) / 'results.json'
            payload = json.dumps({'matches': [event]}).encode()
            path.write_bytes(payload)
            source.update(raw_capture_ref=str(path), provider_event_id=42,
                          source_sha256=hashlib.sha256(payload).hexdigest())
            verify_result_sources([entry])
            source['home_score'] = 100
            with self.assertRaises(ValueError):
                verify_result_sources([entry])
            source['home_score'] = 2
            path.write_bytes(b'{}')
            with self.assertRaises(ValueError):
                verify_result_sources([entry])

    def test_both_thresholds_required_and_no_interim_interval(self):
        for days, per_day in [(1, 250), (60, 1)]:
            study = studies([batch(days, per_day)])[0]
            self.assertFalse(study['assessment_ready'])
            with TemporaryDirectory() as root:
                self.assertIsNone(assess_once(study, Path(root)))
                self.assertFalse((Path(root) / '_assessments').exists())

    def test_duplicate_batches_do_not_inflate_progress(self):
        item = batch(1, 4)
        study = studies([item, deepcopy(item)])[0]
        self.assertEqual(study['settled_selections'], 4)
        self.assertEqual(study['fixture_days'], 1)
        self.assertEqual(study['batch_count'], 2)

    def test_conflicting_forecasts_rejected(self):
        first = batch(1, 1)
        second = deepcopy(first)
        second['trial']['fixtures'][0]['outcomes']['home_win']['probability'] = .5
        with self.assertRaises(ValueError):
            studies([first, second])

    def test_models_policies_and_books_are_separate(self):
        first = batch(1, 2)
        for change in ['candidate', 'policy', 'book']:
            second = deepcopy(first)
            if change == 'candidate':
                second['trial']['candidate_checksums']['model_v2.1.0.pkl'] = 'b' * 64
            elif change == 'policy':
                second['trial']['policy']['minimum_stressed_ev'] = .1
            else:
                second['trial']['fixtures'][0]['bookmaker'] = 'betpawa'
            self.assertEqual(len(studies([first, second])), 2)

    def test_pending_earlier_selection_blocks_cohort(self):
        item = batch(61, 4)
        item['receipt']['fixtures'][0]['settlement_status'] = 'pending'
        study = studies([item])[0]
        self.assertGreaterEqual(study['settled_selections'], 200)
        self.assertGreaterEqual(study['fixture_days'], 60)
        self.assertFalse(study['assessment_ready'])

    def test_one_assessment_freezes_full_first_qualifying_day(self):
        study = studies([batch(61, 4)])[0]
        with TemporaryDirectory() as root:
            first = assess_once(study, Path(root))
            self.assertEqual(first['selections'], 240)
            self.assertEqual(first['fixture_days'], 60)
            self.assertTrue(first['paper_evidence_passed'])
            self.assertFalse(first['profitable_edge_established'])
            later = studies([batch(70, 4, win=False)])[0]
            self.assertEqual(first, assess_once(later, Path(root)))
            path = Path(root) / '_assessments' / study['study_id'] / 'cohort.json'
            manifest = json.loads(path.read_text())
            manifest['entries'][0]['settlement']['profit_units'] = 100
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                assess_once(study, Path(root))

    def test_negative_result_remains_final_and_bootstrap_is_reproducible(self):
        study = studies([batch(win=False)])[0]
        with TemporaryDirectory() as root:
            result = assess_once(study, Path(root))
            self.assertEqual(result['status'], 'paper_evidence_not_established')
            self.assertEqual(result['stressed_roi_ci95'], [-1., -1.])
            self.assertEqual(result, assess_once(studies([batch(win=True)])[0], Path(root)))
        entries = study['entries']
        a, b = assess(entries), assess(entries)
        self.assertEqual(a, b)
        self.assertEqual(a['protocol'], PROTOCOL)

    def test_dashboard_aggregates_real_imports_and_recomputes_receipt_totals(self):
        item = batch(1, 4)
        with TemporaryDirectory() as root:
            root = Path(root)
            source = root / 'source.json'
            source.write_text(json.dumps(item['trial']))
            directory = import_trial(source, root / 'trials')
            results = [r['result_source'] for r in item['receipt']['fixtures']]
            settle_directory(directory, results)
            path = next(directory.glob('settlement_*.json'))
            payload = json.loads(path.read_text())
            payload['roi'] = 999
            payload['settled_selections'] = 999
            path.write_text(json.dumps(payload))
            result = dashboard(root / 'trials')
            self.assertEqual(result['studies'][0]['settled_selections'], 4)
            self.assertEqual(result['studies'][0]['roi'], 1.)


if __name__ == '__main__':
    unittest.main()
