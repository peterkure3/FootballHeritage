from copy import deepcopy
import unittest

from etl.fetch_nba_results_research import normalize


class NbaResearchResultsTests(unittest.TestCase):
    def game(self):
        return {'id':1,'datetime':'2026-10-30T23:00:00Z','season':2026,'postseason':False,
            'status':'Final','status_state':'final','period':4,'postponed':False,
            'home_team':{'full_name':'Washington Wizards'},'visitor_team':{'full_name':'Charlotte Hornets'},
            'home_team_score':95,'visitor_team_score':79,
            'home_q1':22,'home_q2':29,'home_q3':28,'home_q4':16,
            'visitor_q1':26,'visitor_q2':20,'visitor_q3':13,'visitor_q4':20}

    def test_observation_time_is_not_backdated(self):
        row=normalize(self.game(),'2026-10-31T20:48:00Z','raw.json')
        self.assertEqual(row['result_available_at'],'2026-10-31T20:48:00+00:00')
        self.assertEqual(row['result_availability_precision'],'CAPTURED_NOW')

    def test_preseason_live_and_future_results_are_excluded(self):
        for changes in [{'datetime':'2026-10-10T23:00:00Z'},{'status_state':'in_progress'},
                        {'datetime':'2026-11-01T23:00:00Z'},{'postseason':True}]:
            game=deepcopy(self.game());game.update(changes)
            self.assertIsNone(normalize(game,'2026-10-31T20:48:00Z','raw.json'))

    def test_inconsistent_quarters_are_rejected(self):
        game=self.game();game['home_q4']=17
        with self.assertRaisesRegex(ValueError,'Quarter totals'):
            normalize(game,'2026-10-31T20:48:00Z','raw.json')
