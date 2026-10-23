"""League-isolated, causal score and schedule features for non-football sports."""

from collections import defaultdict, deque
import heapq

import numpy as np
import pandas as pd

from models.sport_data import SPORTS

SCHEMA_VERSION = "sport-winner-1.0"
HISTORY_FEATURES = ["elo_diff", "home_expected", "home_games", "away_games", "home_win_rate", "away_win_rate",
    "home_scored", "away_scored", "home_allowed", "away_allowed", "home_margin", "away_margin",
    "home_rest", "away_rest", "home_recent_load", "away_recent_load"]
MARKET_FEATURES = ["fair_home_prob", "fair_away_prob", "overround"]
FEATURES = HISTORY_FEATURES + MARKET_FEATURES + ["odds_missing"]


class SportState:
    def __init__(self, sport):
        self.spec = SPORTS[sport]
        self.elo = defaultdict(lambda: 1500.)
        self.games = defaultdict(lambda: deque(maxlen=self.spec["window"]))

    def vector(self, game):
        league = game["league"]
        h, a = (league, str(game["home_team"]).casefold().strip()), (league, str(game["away_team"]).casefold().strip())
        date = pd.to_datetime(game["date"], utc=True)
        advantage = 0. if game.get("neutral_site") is True else self.spec["home_advantage"]
        difference = self.elo[h] - self.elo[a] + advantage
        result = {"elo_diff": difference, "home_expected": 1 / (1 + 10 ** (-difference / 400))}
        prior = 70. if league == "basketball_ncaab" else self.spec["score_prior"]
        for side, key in [("home", h), ("away", a)]:
            games = list(self.games[key])
            scored = np.mean([g[1] for g in games]) if games else prior
            allowed = np.mean([g[2] for g in games]) if games else prior
            result.update({f"{side}_games": len(games), f"{side}_win_rate": np.mean([g[1] > g[2] for g in games]) if games else .5,
                f"{side}_scored": scored / prior, f"{side}_allowed": allowed / prior, f"{side}_margin": (scored - allowed) / prior,
                f"{side}_rest": min(30., max(0., (date - games[-1][0]).total_seconds() / 86400)) if games else 30.,
                f"{side}_recent_load": sum((date - g[0]).total_seconds() < 7 * 86400 for g in games)})
        prices = np.array([game.get("home_win", np.nan), game.get("away_win", np.nan)], dtype=float)
        missing = not (np.isfinite(prices).all() and (prices > 1).all())
        implied = 1 / prices if not missing else np.array([.5, .5])
        result.update(fair_home_prob=implied[0] / implied.sum(), fair_away_prob=implied[1] / implied.sum(),
                      overround=implied.sum() - 1, odds_missing=float(missing))
        return result

    def update(self, game):
        h, a = (game["league"], game["home_key"]), (game["league"], game["away_key"])
        advantage = 0. if game.get("neutral_site") is True else self.spec["home_advantage"]
        expected = 1 / (1 + 10 ** ((self.elo[a] - self.elo[h] - advantage) / 400))
        hs, aws = game["home_score"], game["away_score"]
        delta = 24 * ((1. if hs > aws else .5 if hs == aws else 0.) - expected)
        self.elo[h] += delta
        self.elo[a] -= delta
        self.games[h].append((game["date"], hs, aws))
        self.games[a].append((game["date"], aws, hs))


def build_features(games: pd.DataFrame, sport: str) -> pd.DataFrame:
    state, pending, vectors, sequence = SportState(sport), [], [], 0
    for day, block in games.groupby(games.date.dt.normalize(), sort=True):
        while pending and pending[0][0] <= day:
            _, _, game = heapq.heappop(pending)
            state.update(game)
        for game in block.to_dict("records"):
            vectors.append(state.vector(game))
            available = max(game["result_available_at"], day + pd.Timedelta(days=1))
            heapq.heappush(pending, (available, sequence, game))
            sequence += 1
    return pd.DataFrame(vectors, columns=FEATURES)


def live_features(history: pd.DataFrame, sport: str, game: dict, as_of=None) -> pd.DataFrame:
    cutoff = pd.to_datetime(as_of if as_of is not None else game["date"], utc=True).normalize()
    state = SportState(sport)
    eligible = history[(history.date < cutoff) & (history.result_available_at <= cutoff)]
    for row in eligible.sort_values(["result_available_at", "date"]).to_dict("records"):
        state.update(row)
    return pd.DataFrame([state.vector(game)], columns=FEATURES)
