"""Advisor draft validation uses the existing optimizer's constraints."""
import unittest
from dataclasses import replace
from etl.fpl_optimizer import Player, evaluate_custom_team


class CustomTeamTests(unittest.TestCase):
    def setUp(self):
        positions = ["GKP"] * 2 + ["DEF"] * 5 + ["MID"] * 5 + ["FWD"] * 3
        self.players = [Player(i + 1, f"Player {i + 1}", i % 5, f"Club {i % 5}", pos, 5.0, 40, 3.0, 4.0, 5.0, expected_points=4.0) for i, pos in enumerate(positions)]
        self.squad = list(range(1, 16))
        self.starters = [1, 3, 4, 5, 8, 9, 10, 11, 13, 14, 15]

    def evaluate(self, **overrides):
        values = dict(players=self.players, squad_ids=self.squad, starter_ids=self.starters, captain_id=13, vice_captain_id=14)
        values.update(overrides)
        return evaluate_custom_team(**values)

    def test_valid_team_recalculates_captain_bonus_cost_and_bench(self):
        team = self.evaluate()
        self.assertEqual(team["expected_points"], 48.0)
        self.assertEqual(team["total_cost"], 75.0)
        self.assertEqual(team["budget_remaining"], 25.0)
        self.assertEqual(team["formation"], {"DEF": 3, "MID": 4, "FWD": 3})
        self.assertEqual([p["id"] for p in team["bench"]], [2, 6, 7, 12])

    def test_invalid_drafts_are_rejected(self):
        cases = [
            {"squad_ids": self.squad[:-1]},
            {"squad_ids": self.squad[:-1] + [1]},
            {"squad_ids": self.squad[:-1] + [999]},
            {"starter_ids": self.starters[:-1]},
            {"starter_ids": self.starters[:-1] + [999]},
            {"starter_ids": self.starters[:-1] + [1]},
            {"starter_ids": [2] + self.starters[1:-1] + [1]},
            {"captain_id": 2}, {"vice_captain_id": 2}, {"vice_captain_id": 13},
            {"players": [replace(p, price=8) for p in self.players]},
            {"players": [replace(p, team_id=1) for p in self.players]},
            {"players": [replace(p, position="DEF") if p.id == 15 else p for p in self.players]},
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                self.evaluate(**case)

    def test_exact_budget_and_alternative_formation(self):
        players = [replace(p, price=30 if p.id == 1 else 5) for p in self.players]
        team = self.evaluate(players=players, starter_ids=[1, 3, 4, 5, 6, 8, 9, 10, 11, 13, 14])
        self.assertEqual(team["budget_remaining"], 0)
        self.assertEqual(team["formation"], {"DEF": 4, "MID": 4, "FWD": 2})


if __name__ == "__main__":
    unittest.main()
