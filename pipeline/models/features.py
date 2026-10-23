"""One causal feature contract for training, replay evaluation, and serving."""

from collections import defaultdict, deque
from typing import Optional

import numpy as np
import pandas as pd

from models.data import ODDS_COLUMNS, canonical_matches, team_key

FEATURE_SCHEMA_VERSION = "2.1.0"
FEATURE_NAMES = [
    "fair_home_prob", "fair_draw_prob", "fair_away_prob", "odds_ratio", "odds_spread",
    "log_home_odds", "log_away_odds", "log_draw_odds", "home_is_favorite",
    "favorite_odds", "underdog_odds", "home_elo", "away_elo", "elo_diff", "home_expected",
    "h2h_home_wins", "h2h_draws", "h2h_away_wins", "h2h_home_goals_avg", "h2h_away_goals_avg",
    "home_weighted_form", "away_weighted_form", "home_weighted_goals_for",
    "home_weighted_goals_against", "away_weighted_goals_for", "away_weighted_goals_against",
    "home_team_home_win_rate", "home_team_home_goals_avg", "away_team_away_win_rate",
    "away_team_away_goals_avg", "home_team_wins_last_n", "home_team_draws_last_n",
    "home_team_losses_last_n", "away_team_wins_last_n", "away_team_draws_last_n",
    "away_team_losses_last_n", "home_team_avg_gd_last_n", "away_team_avg_gd_last_n",
    "odds_missing",
]


class FeatureState:
    def __init__(self) -> None:
        self.elo = defaultdict(lambda: 1500.0)
        self.history = defaultdict(lambda: deque(maxlen=10))
        self.venues = defaultdict(lambda: deque(maxlen=20))
        self.h2h = defaultdict(lambda: deque(maxlen=10))

    def vector(self, home: str, away: str, odds: Optional[dict] = None) -> dict:
        home, away = team_key(home), team_key(away)
        odds = odds or {}
        prices = np.array([odds.get(col, np.nan) for col in ODDS_COLUMNS], dtype=float)
        missing = not (np.isfinite(prices).all() and (prices > 1).all())
        if missing:
            prices = np.array([2.5, 3.2, 2.8])
        fair = 1 / prices
        fair /= fair.sum()
        h, d, a = prices
        features = dict(zip(["fair_home_prob", "fair_draw_prob", "fair_away_prob"], fair))
        features.update({"odds_ratio": h / a, "odds_spread": h - a,
                         "log_home_odds": np.log(h), "log_draw_odds": np.log(d),
                         "log_away_odds": np.log(a), "home_is_favorite": float(h < a),
                         "favorite_odds": min(h, a), "underdog_odds": max(h, a),
                         "home_elo": self.elo[home], "away_elo": self.elo[away],
                         "elo_diff": self.elo[home] - self.elo[away] + 100,
                         "home_expected": 1 / (1 + 10 ** ((self.elo[away] - self.elo[home] - 100) / 400)),
                         "odds_missing": float(missing)})
        for side, team in [("home", home), ("away", away)]:
            history = list(self.history[team])
            if history:
                points, gf, ga = np.array(history).T
                weights = 0.9 ** np.arange(len(history) - 1, -1, -1)
                features[f"{side}_weighted_form"] = np.average(points, weights=weights)
                features[f"{side}_weighted_goals_for"] = np.average(gf, weights=weights)
                features[f"{side}_weighted_goals_against"] = np.average(ga, weights=weights)
            else:
                features.update({f"{side}_weighted_form": 1.0,
                                 f"{side}_weighted_goals_for": 1.5,
                                 f"{side}_weighted_goals_against": 1.5})
            recent = history[-5:]
            features[f"{side}_team_wins_last_n"] = sum(m[0] == 3 for m in recent)
            features[f"{side}_team_draws_last_n"] = sum(m[0] == 1 for m in recent)
            features[f"{side}_team_losses_last_n"] = sum(m[0] == 0 for m in recent)
            features[f"{side}_team_avg_gd_last_n"] = np.mean([m[1] - m[2] for m in recent]) if recent else 0.0
            venue = list(self.venues[(team, side)])
            features[f"{side}_team_{side}_win_rate"] = np.mean([m[0] == 3 for m in venue]) if len(venue) >= 5 else (0.5 if side == "home" else 0.33)
            features[f"{side}_team_{side}_goals_avg"] = np.mean([m[1] for m in venue]) if len(venue) >= 5 else (1.5 if side == "home" else 1.0)
        past = self.h2h[tuple(sorted([home, away]))]
        oriented = [(hg, ag) if ht == home else (ag, hg) for ht, hg, ag in past]
        features.update({"h2h_home_wins": sum(hg > ag for hg, ag in oriented),
                         "h2h_draws": sum(hg == ag for hg, ag in oriented),
                         "h2h_away_wins": sum(hg < ag for hg, ag in oriented),
                         "h2h_home_goals_avg": np.mean([m[0] for m in oriented]) if oriented else 0.0,
                         "h2h_away_goals_avg": np.mean([m[1] for m in oriented]) if oriented else 0.0})
        return features

    def update(self, match: dict) -> None:
        if pd.isna(match.get("result")):
            return
        home, away = match["home_key"], match["away_key"]
        hg, ag = match["home_score"], match["away_score"]
        hp = 3 if hg > ag else (1 if hg == ag else 0)
        ap = 3 if ag > hg else (1 if hg == ag else 0)
        expected = 1 / (1 + 10 ** ((self.elo[away] - self.elo[home] - 100) / 400))
        delta = 32 * ((1.0 if hg > ag else (0.5 if hg == ag else 0.0)) - expected)
        self.elo[home] += delta
        self.elo[away] -= delta
        self.history[home].append((hp, hg, ag))
        self.history[away].append((ap, ag, hg))
        self.venues[(home, "home")].append((hp, hg, ag))
        self.venues[(away, "away")].append((ap, ag, hg))
        self.h2h[tuple(sorted([home, away]))].append((home, hg, ag))


def build_feature_frame(matches: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    fixtures = canonical_matches([matches])
    state = FeatureState()
    records = []
    # Date-only historical sources have no finish timestamp. Wait until the next
    # UTC day before exposing results, including to other fixtures that day.
    for _, group in fixtures.groupby("fixture_day", sort=True):
        group_records = group.to_dict("records")
        records.extend(state.vector(m["home_team"], m["away_team"], m) for m in group_records)
        for match in group_records:
            state.update(match)
    return pd.DataFrame(records, columns=FEATURE_NAMES), fixtures


def build_live_features(history: pd.DataFrame, home: str, away: str,
                        cutoff: pd.Timestamp, odds: Optional[dict] = None) -> pd.DataFrame:
    cutoff = pd.to_datetime(cutoff, utc=True)
    fixtures = canonical_matches([history]) if not history.empty else pd.DataFrame()
    state = FeatureState()
    if not fixtures.empty:
        fixtures = fixtures[fixtures.date < cutoff.normalize()]
        for match in fixtures.to_dict("records"):
            state.update(match)
    return pd.DataFrame([state.vector(home, away, odds)], columns=FEATURE_NAMES)
