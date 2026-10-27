"""Research-only manager features using observations from earlier completed days.

Match metadata identifies the coach who actually managed a fixture. It cannot
prove when an appointment was announced, so current-match coach IDs are used
only in state updates, never in that match's prediction vector.
"""
from collections import defaultdict, deque

import pandas as pd

from models.features import FEATURE_NAMES, FeatureState

SIDE_FEATURES = ['known', 'stint_games_observed', 'recent_change_observed',
                 'prior_games_observed', 'smoothed_ppg', 'elo_adjusted_result']
MANAGER_FEATURES = [f'{side}_manager_{name}' for side in ['home', 'away'] for name in SIDE_FEATURES]
MANAGER_FEATURES += ['manager_pair_games', 'manager_pair_home_score']


def coach_key(value) -> str | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        identifier = int(value)
        return str(identifier) if identifier > 0 and float(value) == identifier else None
    except (ValueError, TypeError, OverflowError):
        return None


class ManagerState:
    def __init__(self) -> None:
        self.teams = {}
        self.records = defaultdict(lambda: deque(maxlen=20))
        self.games = defaultdict(int)
        self.pairs = defaultdict(lambda: deque(maxlen=10))

    def vector(self, home: str, away: str) -> dict:
        features, coaches = {}, []
        for side, team in [('home', home), ('away', away)]:
            stint = self.teams.get(team)
            coach = stint['coach'] if stint else None
            coaches.append(coach)
            records = list(self.records[coach]) if coach else []
            values = [float(coach is not None), float(stint['games']) if stint else 0.,
                      float(stint['changed'] and stint['games'] <= 5) if stint else 0.,
                      float(self.games[coach]) if coach else 0.,
                      (sum(row[0] for row in records) + 5 * 1.3) / (len(records) + 5),
                      sum(row[1] for row in records) / (len(records) + 10)]
            features.update({f'{side}_manager_{key}': value for key, value in zip(SIDE_FEATURES, values)})
        pair = tuple(sorted(coaches)) if all(coaches) else None
        history = list(self.pairs[pair]) if pair else []
        oriented = history if pair and coaches[0] == pair[0] else [1-score for score in history]
        features['manager_pair_games'] = float(len(history))
        features['manager_pair_home_score'] = (sum(oriented) + 5) / (len(history) + 10)
        return features

    def update(self, row: dict, home_expected: float) -> None:
        hg, ag = row['home_score'], row['away_score']
        home_score = 1. if hg > ag else .5 if hg == ag else 0.
        coaches = [coach_key(row.get(side + '_coach_id')) for side in ['home', 'away']]
        for side, coach, result, expected in [('home', coaches[0], home_score, home_expected),
                                              ('away', coaches[1], 1-home_score, 1-home_expected)]:
            if coach is None:
                continue
            team = row[side + '_key']
            previous = self.teams.get(team)
            if previous and previous['coach'] == coach:
                previous['games'] += 1
            else:
                self.teams[team] = {'coach': coach, 'games': 1, 'changed': previous is not None}
            points = 3. if result == 1 else 1. if result == .5 else 0.
            self.records[coach].append((points, result-expected))
            self.games[coach] += 1
        if all(coaches) and coaches[0] != coaches[1]:
            pair = tuple(sorted(coaches))
            self.pairs[pair].append(home_score if coaches[0] == pair[0] else 1-home_score)


def build_manager_frame(fixtures: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Input is a validated, chronological canonical fixture table."""
    ordered = fixtures.sort_values(['date', 'home_key', 'away_key']).reset_index(drop=True)
    if not ordered.result.notna().all():
        raise ValueError('Manager research requires completed fixtures')
    history, managers = FeatureState(), ManagerState()
    baseline, extra = [], []
    for _, group in ordered.groupby(ordered.date.dt.normalize(), sort=True):
        pending = []
        for row in group.to_dict('records'):
            vector = history.vector(row['home_team'], row['away_team'])
            baseline.append(vector)
            extra.append(managers.vector(row['home_key'], row['away_key']))
            pending.append((row, vector['home_expected']))
        for row, expected in pending:
            managers.update(row, expected)
            history.update(row)
    return pd.DataFrame(baseline, columns=FEATURE_NAMES), pd.DataFrame(extra, columns=MANAGER_FEATURES), ordered
