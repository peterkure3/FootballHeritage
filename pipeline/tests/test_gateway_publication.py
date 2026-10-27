"""Boundary checks for response snapshots; no service/database dependency."""

import unittest
from datetime import UTC, datetime, timedelta

from sync.gateway import contract, fresh_until


class GatewayPublicationTests(unittest.TestCase):
    def test_packaged_route_manifests_are_identical(self):
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]
        self.assertEqual(
            (root / "pipeline/sync/gateway_routes.json").read_bytes(),
            (root / "backend/contracts/gateway_routes.json").read_bytes(),
        )

    def test_static_routes_are_not_mistaken_for_parameter_routes(self):
        self.assertTrue(contract("GET", "predictions/validate-data")["admin"])
        self.assertFalse(contract("GET", "predictions/42")["admin"])
        self.assertIsNone(contract("POST", "unknown/action"))

    def test_market_snapshot_expires_at_kickoff(self):
        now = datetime(2026, 10, 27, 12, tzinfo=UTC)
        value = {"predictions": [{"kickoff": (now + timedelta(seconds=9)).isoformat()}]}
        self.assertEqual(
            fresh_until("betting-intel/nba", value, now, 300),
            now + timedelta(seconds=9),
        )

    def test_quote_and_prediction_expiry_bound_the_cache(self):
        now = datetime(2026, 10, 27, 12, tzinfo=UTC)
        value = {
            "quotes": [{"observed_at": (now - timedelta(seconds=1795)).isoformat()}]
        }
        self.assertEqual(
            fresh_until("betting-intel/nfl", value, now, 300),
            now + timedelta(seconds=5),
        )
        value = {
            "prediction_created_at": (
                now - timedelta(hours=24) + timedelta(seconds=2)
            ).isoformat()
        }
        self.assertEqual(
            fresh_until("prediction-dashboard/fixtures", value, now, 300),
            now + timedelta(seconds=2),
        )

    def test_history_and_already_labelled_old_evidence_do_not_expire_new_views(self):
        now = datetime(2026, 10, 27, 12, tzinfo=UTC)
        old = {"date": (now - timedelta(days=2)).isoformat()}
        self.assertEqual(
            fresh_until("predictions/history-data", old, now, 300),
            now + timedelta(seconds=300),
        )

    def test_native_intelligence_preserves_rust_wire_types(self):
        from decimal import Decimal

        from sync.intelligence_views import wire

        self.assertEqual(wire(Decimal("1.00"), "stake"), "1.00")
        self.assertEqual(wire(Decimal("0.55"), "true_probability"), 0.55)
        self.assertEqual(
            wire(datetime(2026, 10, 27, 12, microsecond=120000, tzinfo=UTC)),
            "2026-10-27T12:00:00.120Z",
        )


if __name__ == "__main__":
    unittest.main()
