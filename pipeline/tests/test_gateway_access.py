import os
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from api.access import private_gateway


class GatewayAccessTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.middleware("http")(private_gateway)

        @app.get("/api/v1/matches")
        def matches():
            return []

        self.client = TestClient(app)

    def test_production_requires_configured_strong_token(self):
        for token in ("", "short", "a" * 32):
            with self.subTest(token_length=len(token)), patch.dict(os.environ, {"APP_ENV": "production", "PIPELINE_INTERNAL_TOKEN": token}):
                response = self.client.get("/api/v1/matches", headers={"Origin": "https://allowed.example.test"})
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json()["error"]["code"], "PRIVATE_SERVICE")

    def test_gateway_token_allows_internal_request(self):
        token = "a" * 32
        with patch.dict(os.environ, {"APP_ENV": "production", "PIPELINE_INTERNAL_TOKEN": token}):
            self.assertEqual(self.client.get("/api/v1/matches", headers={"X-Internal-Token": token}).status_code, 200)
            self.assertEqual(self.client.get("/api/v1/matches", headers={"X-Internal-Token": "b" * 32}).status_code, 403)

    def test_development_compatibility(self):
        with patch.dict(os.environ, {"APP_ENV": "development", "PIPELINE_INTERNAL_TOKEN": ""}):
            self.assertEqual(self.client.get("/api/v1/matches").status_code, 200)


if __name__ == "__main__":
    unittest.main()
