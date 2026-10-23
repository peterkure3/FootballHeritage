"""Rank real fixture predictions, optionally comparing available bookmaker quotes."""

import math


def build_picks(rows, limit=10, min_edge=0.05):
    picks = []
    for row in rows:
        probabilities = [float(row[key]) for key in ("home_prob", "draw_prob", "away_prob")]
        if not all(math.isfinite(p) and 0 <= p <= 1 for p in probabilities):
            continue
        if abs(sum(probabilities) - 1) > 0.01:
            continue
        names = [f"{row['home_team']} (Home Win)", "Draw", f"{row['away_team']} (Away Win)"]
        quotes = row.get("quotes") or []
        candidates = []
        for quote in quotes:
            for index, key in enumerate(("home_win", "draw", "away_win")):
                odds = quote.get(key)
                if odds is None or not math.isfinite(float(odds)) or float(odds) <= 1:
                    continue
                odds = float(odds)
                edge = probabilities[index] - 1 / odds
                candidates.append((edge, probabilities[index] * odds - 1, index, odds, quote))
        value = max(candidates, key=lambda c: c[:3], default=None)
        is_value = value is not None and value[0] >= min_edge
        index = value[2] if is_value else max(range(3), key=probabilities.__getitem__)
        if not is_value:
            value = max((c for c in candidates if c[2] == index), key=lambda c: c[:3], default=None)
        p = probabilities[index]
        odds = value[3] if value else None
        quote = value[4] if value else None
        # A fixed one-unit reference, never the user's wallet or a bet instruction.
        pick = {key: row[key] for key in (
            "match_id", "home_team", "away_team", "competition", "match_date", "model_version", "prediction_created_at"
        )}
        pick.update(
            selection=names[index], pick_type="value" if is_value else "prediction",
            model_prob=p, home_prob=probabilities[0], draw_prob=probabilities[1], away_prob=probabilities[2],
            implied_prob=1 / odds if odds else None, decimal_odds=odds,
            edge=value[0] if value else None, edge_pct=value[0] * 100 if value else None,
            expected_value=p * odds - 1 if odds else None, recommended_stake=1.0 if odds else None,
            bookmaker=quote["bookmaker"] if quote else None,
            odds_updated_at=quote["updated_at"] if quote else None,
            explanation=(
                "Model probability exceeds the quoted odds-implied probability by at least five percentage points."
                if is_value else
                "The model's most likely result. No qualifying value edge is available from current bookmaker quotes."
                if quote else
                "The model's most likely result. No recent bookmaker quote is available, so odds and value cannot be calculated."
            ),
        )
        picks.append(pick)
    picks.sort(key=lambda p: (p["pick_type"] == "value", p["edge"] if p["pick_type"] == "value" else p["model_prob"], p["model_prob"]), reverse=True)
    return picks[:limit]
