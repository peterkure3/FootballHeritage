"""Probability/quote behavior and real PostgreSQL queries in rollback-only temp tables."""
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
import unittest
import os
from unittest.mock import patch

from sqlalchemy import text

from api import prediction_dashboard as dashboard
from api.db import get_db_connection
from config import MODEL_VERSION


class QuoteTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.probs = dict(zip(dashboard.OUTCOMES, (.6, .25, .15)))

    def quote(self, name="A", prices=(2., 3., 5.), age=1):
        return dict(bookmaker=name, home_win=prices[0], draw=prices[1], away_win=prices[2],
                    updated_at=(self.now - timedelta(hours=age)).replace(tzinfo=None) if age is not None else None)

    def test_decimal_price_and_unit_ev_including_draw(self):
        result = dashboard.quote_comparison(self.probs, [self.quote()], self.now, True)
        self.assertEqual(len(result["comparisons"]), 3)
        home = result["comparisons"][0]
        self.assertAlmostEqual(home["break_even_prob"], .5)
        self.assertAlmostEqual(home["estimated_ev_units"], .2)
        self.assertAlmostEqual(sum(result["consensus"].values()), 1)
        self.assertAlmostEqual(result["quotes"][0]["fair_probabilities"]["home_win"], .5 / (.5 + 1/3 + .2))

    def test_consensus_and_best_price_are_separate(self):
        result = dashboard.quote_comparison(self.probs, [self.quote(), self.quote("B", (2.5, 3., 4.))], self.now, True)
        home = result["comparisons"][0]
        self.assertEqual(home["bookmaker"], "B")
        self.assertEqual(home["decimal_odds"], 2.5)
        self.assertAlmostEqual(home["consensus_prob"], (.5 / (.5 + 1/3 + .2) + .4 / (.4 + 1/3 + .25)) / 2)

    def test_stale_future_unknown_and_incomplete_quotes_cannot_create_value(self):
        for quote in [self.quote(age=25), self.quote(age=-1), self.quote(age=None), self.quote(prices=(2., None, 5.)), self.quote(prices=(float("nan"), 3., 5.))]:
            result = dashboard.quote_comparison(self.probs, [quote], self.now, True)
            self.assertEqual(result["comparisons"], [])
            self.assertIsNone(result["consensus"])
            self.assertNotIn("fair_probabilities", result["quotes"][0])

    def test_stale_prediction_and_missing_market_have_distinct_states(self):
        stale = dashboard.quote_comparison(self.probs, [self.quote()], self.now, False)
        self.assertEqual(stale["state"], "current")
        self.assertEqual(stale["comparisons"], [])
        self.assertEqual(dashboard.quote_comparison(self.probs, [], self.now, True)["state"], "missing")


@unittest.skipUnless(os.environ.get('RUN_PREDICTION_DB_TESTS') == '1', 'Opt-in local PostgreSQL integration; uses rollback-only temp tables')
class PostgreSQLDashboardTests(unittest.TestCase):
    def setUp(self):
        self.connection = get_db_connection().connect()
        self.transaction = self.connection.begin()
        # PostgreSQL resolves session-local temp tables before public tables.
        # No production rows are changed; everything is rolled back in tearDown.
        for query in [
            "CREATE TEMP TABLE matches (match_id INTEGER PRIMARY KEY, competition TEXT, date TIMESTAMP, home_team TEXT, away_team TEXT, home_score INT, away_score INT, status TEXT, result TEXT) ON COMMIT DROP",
            "CREATE TEMP TABLE predictions (id SERIAL PRIMARY KEY, match_id INT, model_version TEXT, winner TEXT, home_prob FLOAT, draw_prob FLOAT, away_prob FLOAT, created_at TIMESTAMP) ON COMMIT DROP",
            "CREATE TEMP TABLE odds (id SERIAL PRIMARY KEY, match_id INT, bookmaker TEXT, home_win FLOAT, draw FLOAT, away_win FLOAT, updated_at TIMESTAMP) ON COMMIT DROP",
        ]:
            self.connection.execute(text(query))
        self.engine_patch = patch.object(dashboard, "get_db_connection", return_value=self)
        self.engine_patch.start()
        self.now = datetime.now(timezone.utc).replace(tzinfo=None)

    def connect(self):
        return nullcontext(self.connection)

    def tearDown(self):
        self.engine_patch.stop()
        self.transaction.rollback()
        self.connection.close()

    def fixture(self, identifier, when, result=None, status="TIMED", league="Test League"):
        self.connection.execute(text("INSERT INTO matches VALUES (:id,:league,:date,'Home','Away',NULL,NULL,:status,:result)"), {"id": identifier, "league": league, "date": when, "status": status, "result": result})

    def prediction(self, identifier, when, winner="home_win", version=MODEL_VERSION, probs=(.6, .25, .15)):
        self.connection.execute(text("INSERT INTO predictions (match_id,model_version,winner,home_prob,draw_prob,away_prob,created_at) VALUES (:id,:version,:winner,:home,:draw,:away,:date)"), dict(id=identifier, version=version, winner=winner, home=probs[0], draw=probs[1], away=probs[2], date=when))

    def test_nearest_fixture_pagination_filters_before_limit_and_active_prediction(self):
        self.fixture(1, self.now + timedelta(days=1))
        self.fixture(2, self.now + timedelta(days=2))
        self.fixture(3, self.now - timedelta(days=1), "home_win", "FINISHED")
        self.fixture(4, self.now + timedelta(days=1), status="LIVE")
        self.prediction(1, self.now - timedelta(hours=1))
        self.prediction(1, self.now - timedelta(minutes=1), version="inactive-candidate")
        first = dashboard.fixtures(1, 1)
        self.assertEqual(first["total_count"], 2)
        self.assertEqual(first["items"][0]["match_id"], 1)
        self.assertEqual(first["items"][0]["prediction"]["model_version"], MODEL_VERSION)
        self.assertEqual(dashboard.fixtures(2, 1)["items"][0]["match_id"], 2)
        self.assertEqual(dashboard.fixtures(1, 5, "Unknown")["total_count"], 0)

    def test_latest_per_book_unknown_timestamp_cannot_be_value(self):
        self.fixture(1, self.now + timedelta(days=1))
        self.prediction(1, self.now - timedelta(hours=1))
        for price, observed in [(10., self.now - timedelta(hours=2)), (2., self.now - timedelta(hours=1))]:
            self.connection.execute(text("INSERT INTO odds (match_id,bookmaker,home_win,draw,away_win,updated_at) VALUES (1,'A',:price,3,5,:observed)"), dict(price=price, observed=observed))
        self.connection.execute(text("INSERT INTO odds (match_id,bookmaker,home_win,draw,away_win) VALUES (1,'Unknown',10,3,5)"))
        market = dashboard.fixtures(1, 5)["items"][0]["market"]
        self.assertEqual(market["comparisons"][0]["decimal_odds"], 2.)
        self.assertEqual(len(market["quotes"]), 2)

    def test_evaluation_excludes_post_kickoff_unknown_invalid_and_deduplicates(self):
        yesterday = self.now - timedelta(days=1)
        for identifier in [1, 2, 4]:
            self.fixture(identifier, yesterday, "home_win", "FINISHED")
        self.fixture(3, None, "home_win", "FINISHED")
        self.prediction(1, yesterday - timedelta(hours=2), winner="away_win")
        self.prediction(1, yesterday - timedelta(hours=1))
        self.prediction(1, yesterday - timedelta(minutes=30), winner='unknown')
        self.prediction(1, yesterday + timedelta(hours=1), winner="away_win")
        self.prediction(2, yesterday + timedelta(hours=1))
        self.prediction(3, yesterday - timedelta(hours=1))
        self.prediction(4, yesterday - timedelta(hours=1), probs=(.8, .8, .8))
        summary = dashboard.accuracy(days=30)
        self.assertEqual(summary["total_predictions"], 1)
        self.assertEqual(summary["overall_accuracy"], 100)
        self.assertEqual(summary["excluded"]["unknown_kickoff_outside_date_window"], 1)
        self.assertEqual(summary["excluded"]["no_valid_pre_kickoff"], 2)
        self.assertAlmostEqual(summary["log_loss"], -__import__('math').log(.6))
        from api.routers import predictions as router
        with patch.object(router, 'get_db_connection', return_value=self):
            versions = router.get_prediction_versions()
        self.assertEqual(versions.current_version, MODEL_VERSION)
        self.assertEqual(versions.versions[0].settled_count, 1)
        self.assertEqual(versions.versions[0].accuracy_pct, 100)

    def test_correctness_counts_and_end_date_include_entire_day(self):
        kickoff = (self.now - timedelta(days=1)).replace(hour=23, minute=59)
        for identifier in range(1, 8):
            self.fixture(identifier, kickoff, "home_win", "FINISHED")
            self.prediction(identifier, kickoff - timedelta(hours=1), winner="home_win" if identifier <= 6 else "away_win")
        first = dashboard.history(1, 5, result_filter="correct", start_date=kickoff.date(), end_date=kickoff.date())
        second = dashboard.history(2, 5, result_filter="correct", start_date=kickoff.date(), end_date=kickoff.date())
        self.assertEqual(first["total_count"], 6)
        self.assertEqual(first["correct_count"], 6)
        self.assertEqual(len(first["predictions"]), 5)
        self.assertEqual(len(second["predictions"]), 1)
        self.assertEqual(dashboard.accuracy(start_date=kickoff.date(), end_date=kickoff.date())["total_predictions"], 7)

    def test_empty_sample_is_unavailable_not_zero_accuracy(self):
        summary = dashboard.accuracy(days=7)
        self.assertEqual(summary["total_predictions"], 0)
        self.assertIsNone(summary["overall_accuracy"])
        self.assertIsNone(summary["log_loss"])


if __name__ == '__main__':
    unittest.main()
