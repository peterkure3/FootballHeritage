"""Provider aliases use existing candidate history and exact settlement identity."""

import unittest
from unittest.mock import patch

from models.data import team_key
from models.football_identity import football_history_key, football_identity_key
from models.paper_trial import result_key, settle
from models.sport_predict import predict_candidate
from scripts.record_edge_trial import price_analysis


class FootballIdentityTests(unittest.TestCase):
    def test_reviewed_names_match_official_names_and_history_keys(self):
        for provider, official, expected in [
            ("Brighton & Hove Albion", "Brighton & Hove Albion FC", "brighton"),
            ("Sunderland", "Sunderland AFC", "sunderland afc"),
            ("Hull City", "Hull City AFC", "hull city afc"),
            ("Bournemouth", "AFC Bournemouth", "afc bournemouth"),
        ]:
            with self.subTest(provider=provider):
                self.assertEqual(football_history_key(provider, {expected}), expected)
                self.assertEqual(football_identity_key(official), expected)
                self.assertEqual(result_key(provider, "Arsenal", "2026-10-01T12:00:00Z"),
                                 result_key(official, "Arsenal FC", "2026-10-01T15:00:00+03:00"))

    def test_existing_feature_keys_and_global_normalization_are_preserved(self):
        for name in ["Bournemouth", "Sunderland", "Hull City", "Brighton & Hove Albion"]:
            original = team_key(name)
            self.assertEqual(football_history_key(name, {original, football_identity_key(name)}), original)
        self.assertEqual(team_key("Sunderland"), "sunderland")
        self.assertEqual(team_key("Hull City"), "hull city")

    def test_unknown_or_similar_clubs_are_not_fuzzy_matched(self):
        for name in ["Hull", "Hull United", "Sunderland U21", "Brighton Women"]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                football_history_key(name, {"hull city afc", "sunderland afc", "brighton"})

    def test_alias_resolution_requires_existing_history(self):
        with self.assertRaises(ValueError):
            football_history_key("Hull City", {"arsenal"})

    def test_same_club_aliases_are_rejected_before_feature_generation(self):
        import pandas as pd
        history = pd.DataFrame({"home_key": ["brighton"], "away_key": ["arsenal"]})
        with patch("models.sport_predict.pd.read_parquet", return_value=history), \
                patch("pathlib.Path.read_text", return_value="{}"), \
                patch("models.features.build_live_features") as features:
            with self.assertRaisesRegex(ValueError, "Competitors must differ"):
                predict_candidate("20261009T100528981075Z", "football", "Brighton", "Brighton & Hove Albion", "2027-01-01T12:00:00Z")
            features.assert_not_called()

    def test_provider_names_settle_against_official_names(self):
        for provider, official in [("Brighton & Hove Albion", "Brighton & Hove Albion FC"),
                                   ("Sunderland", "Sunderland AFC"), ("Hull City", "Hull City AFC")]:
            with self.subTest(provider=provider):
                trial = {"candidate_id": "test", "policy": {"payout_haircut": .02}, "limits": [],
                         "fixtures": [{"home": provider, "away": "Arsenal", "kickoff": "2026-10-01T12:00:00Z",
                             "bookmaker": "bovada", "status": "recorded_pregame", "selected_outcome": "home_win",
                             "outcomes": price_analysis({"home_win": .6, "draw": .2, "away_win": .2},
                                                        {"home_win": 2., "draw": 3., "away_win": 4.})}]}
                result = {"home_team": official, "away_team": "Arsenal FC", "commence_time": "2026-10-01T12:00:00Z",
                          "home_score": 2, "away_score": 1, "status": "FINISHED", "settlement_rule": "REGULATION_TIME",
                          "observed_at": "2026-10-01T15:00:00Z", "source_url": "https://example.com/results"}
                self.assertEqual(settle(trial, [result])["settled_selections"], 1)
                result["commence_time"] = "2026-10-01T13:00:00Z"
                self.assertEqual(settle(trial, [result])["settled_selections"], 0)
