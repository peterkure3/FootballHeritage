"""Candidate team discovery uses the selected model's league history."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from models.sport_predict import candidate_teams


class CandidateTeamTests(unittest.TestCase):
    def test_names_are_sorted_deduplicated_and_scoped_to_league(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            pd.DataFrame({
                "home_team": ["Chiefs", "Bills", "Other"],
                "away_team": ["Bills", "Chiefs", "College"],
                "league": ["americanfootball_nfl", "americanfootball_nfl", "americanfootball_ncaaf"],
            }).to_parquet(directory / "dataset.parquet")
            (directory / "metrics.json").write_text(json.dumps({
                "training_leagues": ["americanfootball_nfl"],
            }))
            with patch("models.sport_predict.candidate_directory", return_value=directory):
                self.assertEqual(candidate_teams("candidate", "nfl", "americanfootball_nfl"), ["Bills", "Chiefs"])
                with self.assertRaises(ValueError):
                    candidate_teams("candidate", "nfl", "americanfootball_ncaaf")
                self.assertEqual(candidate_teams("candidate", "football"), ["Bills", "Chiefs", "College", "Other"])

    def test_invalid_paths_are_rejected(self):
        with self.assertRaises(ValueError):
            candidate_teams("../../outside", "nfl", "americanfootball_nfl")
