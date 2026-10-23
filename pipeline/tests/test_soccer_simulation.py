"""Behavioral gates for event integrity, temporal isolation and simulated accounting."""
from copy import deepcopy
import io
from pathlib import Path
import tempfile
import unittest

import numpy as np

from etl.soccer_event_dataset import iter_array, normalize_match, substitutions
from models.run_soccer_simulation import (actual_stats, chronological_split, count_crps,
                                         read_model, save_model, validate_players)
from models.soccer_players import player_distributions, roster_scenario, sampled_intervals
from models.soccer_possessions import PossessionModel, event_stats, possessions


def fixture() -> tuple[dict, list[dict], dict]:
    teams = {}
    for team_id, first, side in [(10, 1, 'home'), (20, 101, 'away')]:
        teams[str(team_id)] = dict(teamId=team_id, side=side, score=int(side == 'home'),
            scoreHT=int(side == 'home'), formation=dict(
                lineup=[{'playerId': i} for i in range(first, first + 11)], bench=[], substitutions='null'))
    match = dict(wyId=1, dateutc='2018-01-01 12:00:00', status='Played', teamsData=teams)
    events = []
    for i, (half, sec, team, pid, kind, tags) in enumerate([
        ('1H', 100., 10, 2, 'Shot', [101, 1801]),
        ('1H', 2701., 20, 102, 'Pass', [1801]),
        ('2H', 0., 20, 102, 'Pass', [1801]),
        ('2H', 2701., 10, 2, 'Pass', [1802]),
    ]):
        events.append(dict(id=i, matchPeriod=half, eventSec=sec, teamId=team, playerId=pid,
            eventName=kind, subEventName=kind, tags=[{'id': t} for t in tags],
            positions=[{'x': 50, 'y': 50}], matchId=1))
    roles = {pid: 'GK' if pid in [1, 101] else 'FW' for pid in list(range(1, 12)) + list(range(101, 112))}
    return match, events, roles


class DatasetTests(unittest.TestCase):
    def test_stream_parser_and_truncation(self) -> None:
        class Tiny(io.StringIO):
            def read(self, size: int = -1) -> str:
                return super().read(min(size, 7) if size > 0 else size)
        self.assertEqual(list(iter_array(Tiny('[{"x":1234}, {"y":"football"}]'))), [{'x': 1234}, {'y': 'football'}])
        for invalid in ['[{"x": 2}', '[{},]', '[{} {}]', '[1]', '[] true']:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                list(iter_array(io.StringIO(invalid)))

    def test_null_substitutions(self) -> None:
        for value in [None, 'null', []]:
            self.assertEqual(substitutions({'substitutions': value}), [])
        with self.assertRaises(ValueError):
            substitutions({'substitutions': 'unexpected'})

    def test_score_reconstruction_and_prior_state(self) -> None:
        match, events, roles = fixture()
        raw = deepcopy(events)
        result = normalize_match(match, events, roles)
        self.assertEqual(result['quarantine'], [])
        self.assertEqual(result['regulation_score'], [1, 0])
        self.assertEqual(result['events'][0]['home_goals_before'], 0)
        self.assertEqual(result['events'][1]['home_goals_before'], 1)
        self.assertEqual(events, raw)

    def test_quarantines_corruption(self) -> None:
        for change, reason in [
            (lambda e: e[1].update(id=0), 'duplicate_event_id'),
            (lambda e: e[1].update(playerId=999), 'actor_not_in_team_roster'),
            (lambda e: e[1].update(positions=[{'x': 101, 'y': 50}]), 'invalid_coordinates'),
            (lambda e: e[0].update(tags=[]), 'home_regulation_score_mismatch'),
        ]:
            match, events, roles = fixture()
            change(events)
            self.assertIn(reason, normalize_match(match, events, roles)['quarantine'])

    def test_own_goal_and_shootout_are_separate(self) -> None:
        match, events, roles = fixture()
        events[0].update(teamId=20, playerId=102, tags=[{'id': 102}], eventName='Others on the ball')
        extra = deepcopy(events[0])
        extra.update(id=99, matchPeriod='P', eventName='Shot', subEventName='Penalty', tags=[{'id': 101}])
        result = normalize_match(match, events + [extra], roles)
        self.assertEqual(result['quarantine'], [])
        self.assertEqual(actual_stats(result)[0, 0], 1)
        self.assertEqual(actual_stats(result)[1, 0], 0)
        self.assertEqual(actual_stats(result)[1, 6], 1)

    def test_possessions_preserve_action_statistics(self) -> None:
        match, events, roles = fixture()
        record = normalize_match(match, events, roles)
        observed = np.sum([event_stats(e) for e in record['events']], axis=0)
        extracted = np.sum([p['stats'] for p in possessions(record)], axis=0)
        np.testing.assert_array_equal(observed, extracted)


class SimulationTests(unittest.TestCase):
    def setUp(self) -> None:
        match, events, roles = fixture()
        self.record = normalize_match(match, events, roles)
        self.model = PossessionModel.fit([self.record])
        self.players = {str(k): {'role': v} for k, v in roles.items()}

    def test_rejects_future_training_and_bad_counts(self) -> None:
        with self.assertRaises(ValueError):
            self.model.simulate(10, 20, '2017-01-01', 10)
        with self.assertRaises(ValueError):
            self.model.simulate(10, 20, '2018-01-01T13:00:00+03:00', 10)
        with self.assertRaises(ValueError):
            self.model.simulate(10, 20, '2019-01-01', 10, player_runs=11)
        corrupted = deepcopy(self.record)
        corrupted['quarantine'] = ['bad']
        with self.assertRaises(ValueError):
            PossessionModel.fit([corrupted])

    def test_reproducibility_and_player_accounting(self) -> None:
        a = self.model.simulate(10, 20, '2019-01-01', 40, 9, 40)
        b = self.model.simulate(10, 20, '2019-01-01', 40, 9, 40)
        np.testing.assert_array_equal(a['samples'], b['samples'])
        self.assertEqual(a['histories'], b['histories'])
        scenarios = roster_scenario(self.record['match'], self.players)
        result = player_distributions(self.model, a['histories'], scenarios, a['samples'], 10)
        self.assertEqual(result['runs'], 40)
        for event in result['trace']:
            side = 0 if event['team_id'] == 10 else 1
            self.assertIn(event['player_id'], scenarios[side]['starters'])

    def test_partial_possession_does_not_score_after_whistle(self) -> None:
        templates = []
        for half in [1, 2]:
            templates.append(dict(match_id=1, team_id=10, opponent_id=20,
                half=half, margin=0, zone=1, duration=4000, next_zone=1, switch=True,
                stats=[1, 1, 1, 0, 0, 0, 0], actions=[dict(offset=3000,
                    stats=[1, 1, 1, 0, 0, 0, 0])]))
        model = PossessionModel(templates, ['2018-01-01'], [[2700], [2700]], {}, [])
        self.assertEqual(model.simulate(10, 20, '2019-01-01', 40)['samples'].sum(), 0)

    def test_own_goal_restart_and_second_half_kickoff(self) -> None:
        templates = [dict(match_id=1, team_id=10, opponent_id=20,
            half=half, margin=0, zone=1, duration=1400, next_zone=1, switch=True,
            stats=[0, 0, 0, 0, 0, 0, 1], actions=[dict(offset=0,
                stats=[0, 0, 0, 0, 0, 0, 1])]) for half in [1, 2]]
        model = PossessionModel(templates, ['2018-01-01'], [[2800], [2800]], {}, [])
        result = model.simulate(10, 20, '2019-01-01', 10, player_runs=10)
        for history in result['histories']:
            first = [p for p in history if p[1] == 1]
            second = [p for p in history if p[1] == 2]
            self.assertEqual(first[0][4], first[1][4])
            self.assertEqual(first[0][4], 1 - second[0][4])

    def test_temporal_split_keeps_equal_kickoffs_together(self) -> None:
        items = [dict(match_id=i, date=f'2018-01-{i // 2 + 1:02d}') for i in range(40)]
        split = chronological_split(items)
        self.assertLess(max(m['date'] for m in split['train']), min(m['date'] for m in split['validation']))
        self.assertLess(max(m['date'] for m in split['validation']), min(m['date'] for m in split['test']))

    def test_crps_known_values(self) -> None:
        self.assertEqual(count_crps(np.array([0, 0, 0]), 1), 1.)
        self.assertEqual(count_crps(np.array([0, 2]), 1), .5)

    def test_persisted_model_reproduces_rollout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'model.json.gz'
            save_model(self.model, path, {'scope': 'test'})
            restored, metadata = read_model(path)
            self.assertEqual(metadata, {'scope': 'test'})
            first = self.model.simulate(10, 20, '2019-01-01', 20, 17)['samples']
            second = restored.simulate(10, 20, '2019-01-01', 20, 17)['samples']
            np.testing.assert_array_equal(first, second)

    def test_missing_observed_actor_does_not_become_a_zero(self) -> None:
        simulation = self.model.simulate(10, 20, '2019-01-01', 20, 2, 20)
        scenarios = roster_scenario(self.record['match'], self.players)
        prediction = player_distributions(self.model, simulation['histories'], scenarios,
                                           simulation['samples'], 3)
        incomplete = deepcopy(self.record)
        incomplete['events'][1]['player_id'] = 0
        result = validate_players(incomplete, prediction, scenarios)
        self.assertFalse(result['metrics']['passes']['scored'])
        self.assertTrue(result['metrics']['goals']['scored'])

    def test_roster_scenario_ignores_observed_future_outcomes(self) -> None:
        before = roster_scenario(self.record['match'], self.players)
        altered = deepcopy(self.record['match'])
        for team in altered['teamsData'].values():
            team['score'] = 999
            team['formation']['substitutions'] = [{'playerOut': 1, 'playerIn': 2, 'minute': 3}]
            for player in team['formation']['lineup']:
                player['goals'] = 999
        self.assertEqual(before, roster_scenario(altered, self.players))

    def test_sampled_substitutions_keep_eleven_active_and_no_reentry(self) -> None:
        scenario = roster_scenario(self.record['match'], self.players)[0]
        scenario['bench'] = [12, 13, 14]
        scenario['roles'].update({12: 'FW', 13: 'FW', 14: 'FW'})
        intervals = sampled_intervals(scenario, [60., 70., 80.], np.random.default_rng(4))
        for minute in [0, 59, 60, 70, 80, 96]:
            self.assertEqual(sum(start <= minute < end for start, end in intervals.values()), 11)
        self.assertEqual(sum(start > 0 for start, _ in intervals.values()), 3)


if __name__ == '__main__':
    unittest.main()
