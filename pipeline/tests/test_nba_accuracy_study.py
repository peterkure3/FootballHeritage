from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

import pandas as pd

from scripts.assess_nba_accuracy_study import combine_nba, latest_evidence, run
from scripts.reconcile_nba_research_results import capture_days
from scripts.evaluate_nba_freshness_shadow import run as evaluate


class NbaAccuracyStudyTests(unittest.TestCase):
    def test_reconciliation_dates_follow_new_results_and_cover_us_date_boundary(self):
        days = capture_days([{'date': '2026-11-05T02:00:00Z'}, {'date': '2026-11-06T23:00:00Z'}])
        self.assertEqual([d.strftime('%Y%m%d') for d in days], ['20261104', '20261105', '20261106'])
        with self.assertRaises(ValueError):
            capture_days([{'date': '2026-11-05T02:00:00'}])

    def trial(self):
        return {'status': 'prospective_NBA_model_shadow', 'classes': ['away_win', 'home_win'],
            'baseline_history_sha256': 'history', 'model_hashes': {'baseline': 'old', 'candidate': 'new'},
            'feature_contract': {'schema': 'frozen'}, 'policy': {'frozen': True},
            'fixtures': [{'id': '1', 'kickoff': '2026-11-02T22:00:00Z', 'generated_at': '2026-11-01T10:00:00Z',
                          'probabilities': {'baseline': [.4, .6], 'candidate': [.3, .7]}}]}

    def test_earliest_forecast_retained_and_new_fixtures_accumulate(self):
        first = self.trial(); later = deepcopy(first)
        later['fixtures'][0]['generated_at'] = '2026-11-01T12:00:00Z'
        later['fixtures'][0]['probabilities']['candidate'] = [.2, .8]
        new = deepcopy(first['fixtures'][0]); new['id'] = '2'; later['fixtures'].append(new)
        combined, duplicates = combine_nba([later, first])
        self.assertEqual(duplicates, 1)
        self.assertEqual(len(combined['fixtures']), 2)
        self.assertEqual(combined['fixtures'][0], first['fixtures'][0])

    def test_changed_hypothesis_models_features_or_policy_require_separate_study(self):
        for key, value in [('status', 'prospective_NBA_freshness_shadow'), ('model_hashes', {}),
                           ('feature_contract', {'schema': 'changed'}), ('policy', {'frozen': False})]:
            changed = deepcopy(self.trial()); changed[key] = value
            with self.assertRaisesRegex(ValueError, 'separate study'):
                combine_nba([self.trial(), changed])

    def test_conflicting_simultaneous_forecast_is_rejected(self):
        changed = deepcopy(self.trial()); changed['fixtures'][0]['probabilities']['candidate'] = [.8, .2]
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            combine_nba([self.trial(), changed])

    def test_latest_observation_wins_and_same_time_conflicts_remain_ambiguous(self):
        evidence = {}; earlier = pd.Timestamp('2026-11-01T12:00:00Z'); later = earlier+pd.Timedelta(hours=1)
        original = {'id': 'espn1', 'score': 10}; revised = {'id': 'espn1', 'score': 11}
        latest_evidence(evidence, original, earlier); latest_evidence(evidence, revised, later)
        latest_evidence(evidence, original, earlier)
        self.assertEqual(evidence['espn1'][1], [revised])
        latest_evidence(evidence, original, later)
        self.assertEqual(len(evidence['espn1'][1]), 2)

    def test_full_study_recomputes_raw_results_and_detects_tampering(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); batch = root/'batch'; receipt = batch/'assessments'/'first'
            receipt.mkdir(parents=True)
            trial = self.trial()
            trial['policy'] = {'settlement': 'INCLUDING_OVERTIME', 'minimum_settled': 200, 'minimum_match_days': 20}
            fixture = trial['fixtures'][0]
            fixture.update(home='Washington Wizards', away='Charlotte Hornets', kickoff='2020-01-02T02:00:00Z',
                generated_at='2020-01-01T12:00:00Z', feature_cutoff='2020-01-01T11:59:00Z')
            def write(path, data):
                path.write_text(json.dumps(data))
                return hashlib.sha256(path.read_bytes()).hexdigest()
            trial['schedule_sources'] = [{'file': 'schedule.json', 'sha256': write(batch/'schedule.json', {})}]
            digest = write(batch/'trial.json', trial); (batch/'trial.sha256').write_text(digest)
            event = {'id': 'espn1', 'date': fixture['kickoff'], 'season': {'type': 2},
                'status': {'period': 4, 'type': {'completed': True}}, 'competitions': [{'competitors': [
                    {'homeAway': 'home', 'team': {'displayName': fixture['home']}, 'score': '103'},
                    {'homeAway': 'away', 'team': {'displayName': fixture['away']}, 'score': '99'}]}]}
            source = {'file': 'results.json', 'observed_at': '2020-01-03T12:00:00Z', 'status': 200,
                      'sha256': write(receipt/'results.json', {'events': [event]})}
            write(receipt/'assessment.json', {'trial_sha256': digest, 'settled': 999, 'result_sources': [source]})
            def response(url, params, timeout):
                payload = {'events': [event] if params['dates'] == '20200101' else []}
                return SimpleNamespace(status_code=200, content=json.dumps(payload).encode(),
                                       url=url, json=lambda: payload)
            with patch('scripts.evaluate_nba_freshness_shadow.requests.get', side_effect=response) as request:
                self.assertEqual(evaluate(batch)['settled'], 1)
                self.assertEqual({call.kwargs['params']['dates'] for call in request.call_args_list},
                                 {'20200101', '20200102'})
            result = run(root, root/'study.json')
            self.assertEqual(result['settled'], 1)
            self.assertEqual(result['metrics']['candidate']['accuracy'], 1)
            write(receipt/'results.json', {'events': []})
            with self.assertRaisesRegex(ValueError, 'Checksum'):
                run(root, root/'tampered-study.json')
