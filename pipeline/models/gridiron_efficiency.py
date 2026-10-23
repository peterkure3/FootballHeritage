"""Causal NFL efficiency features derived from completed nflfastR play-by-play."""
from collections import defaultdict, deque
import heapq

import numpy as np
import pandas as pd

from models.gridiron_sources import NFL_RENAMES
from models.sport_features import build_features, HISTORY_FEATURES

PBP_VALUES = ['offense_epa', 'defense_epa', 'offense_success', 'defense_success', 'pbp_games']
PBP_FEATURES = [f'{side}_{name}' for side in ['home', 'away'] for name in PBP_VALUES]
EFFICIENCY_FEATURES = HISTORY_FEATURES + PBP_FEATURES


def build_efficiency_features(games: pd.DataFrame, stats: pd.DataFrame) -> pd.DataFrame:
    """Never expose same-game, same-day, or unavailable result efficiency."""
    lookup = {}
    for row in stats.to_dict('records'):
        team = NFL_RENAMES.get(row['posteam'], row['posteam'])
        key = (str(row['game_id']), team)
        if key in lookup:
            raise ValueError('Duplicate nflfastR team/game aggregate')
        lookup[key] = row
    states = defaultdict(lambda: deque(maxlen=8))
    pending, sequence, vectors = [], 0, []
    for day, block in games.groupby(games.date.dt.normalize(), sort=True):
        while pending and pending[0][0] <= day:
            _, _, team, values = heapq.heappop(pending)
            states[team].append(values)
        for game in block.to_dict('records'):
            vector = {}
            for side, other in [('home', 'away'), ('away', 'home')]:
                team, opponent = str(game[f'provider_{side}_team_id']), str(game[f'provider_{other}_team_id'])
                history = list(states[team])
                means = np.mean(history, axis=0) if history else [0., 0., .45, .45]
                vector.update({f'{side}_{name}': float(value) for name,value in zip(PBP_VALUES[:-1], means)})
                vector[f'{side}_pbp_games'] = len(history)
                own = lookup.get((str(game['provider_event_id']), team))
                opp = lookup.get((str(game['provider_event_id']), opponent))
                if own is not None and opp is not None:
                    available = max(game['result_available_at'], day + pd.Timedelta(days=1))
                    values = [own['epa_per_play'], opp['epa_per_play'], own['success_rate'], opp['success_rate']]
                    heapq.heappush(pending, (available, sequence, team, values))
                    sequence += 1
            vectors.append(vector)
    base = build_features(games, 'nfl')[HISTORY_FEATURES]
    return pd.concat([base.reset_index(drop=True), pd.DataFrame(vectors, columns=PBP_FEATURES)], axis=1)
