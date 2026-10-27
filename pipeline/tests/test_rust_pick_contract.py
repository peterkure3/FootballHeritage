"""The frozen Rust contract must remain the actual Python selection behavior."""

import hashlib
import json
import unittest
from pathlib import Path

from api.ai_picks import build_picks

ROOT = Path(__file__).resolve().parents[2]


class RankingContractTests(unittest.TestCase):
    def test_frozen_examples_match_current_python(self):
        contract = json.loads(
            (ROOT / "backend/tests/fixtures/ai_pick_selection_contract.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(contract["synthetic_test_data_only"])
        self.assertEqual(
            contract["python_source_sha256"],
            hashlib.sha256(
                (ROOT / "pipeline/api/ai_picks.py").read_bytes()
            ).hexdigest(),
        )
        for case in contract["cases"]:
            with self.subTest(case=case["name"]):
                self.assertEqual(
                    build_picks(case["rows"], case["limit"]), case["expected"]
                )
