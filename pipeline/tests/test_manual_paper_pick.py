import copy
from datetime import datetime, timedelta, timezone
import unittest

from models.paper_trial import settle
from models.trial_study import studies
from scripts.record_manual_paper_pick import build_trial


class ManualPickTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.fixture = {'match_id': 123, 'home_team': 'Coventry City FC',
                        'away_team': 'Newcastle United FC',
                        'kickoff': (self.now + timedelta(hours=1)).isoformat(),
                        'prediction': {'status': 'current', 'model_version': '2.0.0',
                                       'probabilities': {'home_win': .2, 'draw': .3, 'away_win': .5}},
                        'market': {'quotes': [{'bookmaker': 'A', 'fresh': True,
                                              'observed_at': self.now.isoformat(),
                                              'prices': {'home_win': 3., 'draw': 3.5, 'away_win': 2.05}}]}}

    def test_rejects_started_fixture_and_stale_quotes(self):
        fixture = copy.deepcopy(self.fixture)
        fixture['kickoff'] = self.now.isoformat()
        with self.assertRaisesRegex(ValueError, 'before kickoff'):
            build_trial(fixture, 'away_win', self.now)
        self.fixture['market']['quotes'][0]['observed_at'] = (self.now - timedelta(minutes=16)).isoformat()
        with self.assertRaisesRegex(ValueError, '15 minutes'):
            build_trial(self.fixture, 'away_win', self.now)

    def test_uses_best_eligible_actual_price_and_manual_policy(self):
        quote = copy.deepcopy(self.fixture['market']['quotes'][0])
        quote.update(bookmaker='B', prices={'home_win': 3., 'draw': 3.5, 'away_win': 2.1})
        self.fixture['market']['quotes'].append(quote)
        trial = build_trial(self.fixture, 'away_win', self.now)
        self.assertEqual(trial['fixtures'][0]['bookmaker'], 'B')
        self.assertEqual(trial['policy']['selection'], 'user_selected')
        self.assertEqual(trial['fixtures'][0]['outcomes']['away_win']['decimal_odds'], 2.1)

    def test_manual_pick_settles_but_does_not_join_frozen_study(self):
        recorded = self.now - timedelta(hours=3)
        self.fixture['kickoff'] = (self.now - timedelta(hours=2)).isoformat()
        self.fixture['market']['quotes'][0]['observed_at'] = recorded.isoformat()
        manual = build_trial(self.fixture, 'away_win', recorded)
        result = {'home_team': self.fixture['home_team'], 'away_team': self.fixture['away_team'],
                  'commence_time': self.fixture['kickoff'], 'home_score': 0, 'away_score': 1,
                  'status': 'FINISHED', 'settlement_rule': 'REGULATION_TIME',
                  'observed_at': self.now.isoformat(), 'source_url': 'https://example.test/official'}
        receipt = settle(manual, [result])
        self.assertEqual(receipt['settled_selections'], 1)
        self.assertAlmostEqual(receipt['profit_units'], 1.05)
        original = copy.deepcopy(manual)
        original['policy']['selection'] = 'largest_stressed_ev'
        groups = studies([{'trial': manual, 'receipt': receipt, 'trial_sha256': 'manual'},
                          {'trial': original, 'receipt': receipt, 'trial_sha256': 'original'}])
        self.assertEqual(len(groups), 2)
        self.assertTrue(all(group['settled_selections'] == 1 for group in groups))
        self.assertFalse(any(group['assessment_ready'] for group in groups))


if __name__ == '__main__':
    unittest.main()
