import unittest

from api.ai_picks import build_picks


def fixture(match_id=1, quotes=None, probabilities=(0.6, 0.25, 0.15)):
    return dict(match_id=match_id, home_team="Arsenal", away_team="Chelsea",
                competition="Premier League", match_date="2026-10-10T14:30:00Z",
                model_version="test-model", prediction_created_at="2026-10-08T12:00:00Z",
                home_prob=probabilities[0], draw_prob=probabilities[1], away_prob=probabilities[2],
                quotes=quotes or [])


def quote(bookmaker="Test book", odds=(2.0, 3.0, 5.0)):
    return dict(bookmaker=bookmaker, updated_at="2026-10-08T12:00:00Z",
                home_win=odds[0], draw=odds[1], away_win=odds[2])


class AiPicksTests(unittest.TestCase):
    def test_missing_odds_returns_prediction_without_invented_value(self):
        pick = build_picks([fixture()])[0]
        self.assertEqual(pick["selection"], "Arsenal (Home Win)")
        self.assertEqual(pick["pick_type"], "prediction")
        for field in ("decimal_odds", "edge_pct", "expected_value", "bookmaker", "recommended_stake"):
            self.assertIsNone(pick[field])

    def test_value_uses_real_quote_and_one_unit_profit(self):
        pick = build_picks([fixture(quotes=[quote()])])[0]
        self.assertEqual(pick["pick_type"], "value")
        self.assertAlmostEqual(pick["edge_pct"], 10)
        self.assertAlmostEqual(pick["expected_value"], 0.2)
        self.assertEqual(pick["recommended_stake"], 1)
        self.assertEqual(pick["bookmaker"], "Test book")

    def test_ranking_and_limit_prioritize_value_then_probability(self):
        rows = [fixture(1, probabilities=(0.8, 0.1, 0.1)), fixture(2, quotes=[quote()])]
        self.assertEqual([p["match_id"] for p in build_picks(rows, 1)], [2])

    def test_invalid_probability_rows_are_excluded(self):
        for probabilities in [(0.8, 0.8, 0.8), (float("nan"), 0.3, 0.2), (-0.1, 0.6, 0.5)]:
            self.assertEqual(build_picks([fixture(probabilities=probabilities)]), [])

    def test_bad_quotes_and_tied_bookmakers_are_safe(self):
        pick = build_picks([fixture(quotes=[quote(odds=(float("nan"), 1, None))])])[0]
        self.assertIsNone(pick["decimal_odds"])
        picks = build_picks([fixture(quotes=[quote("A"), quote("B")])])
        self.assertEqual(len(picks), 1)


if __name__ == "__main__":
    unittest.main()
