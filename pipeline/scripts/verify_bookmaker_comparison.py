"""Audit exported bookmaker ledgers against the actual captured book prices."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from models.validation import probability_metrics


def verify(root: Path) -> dict:
    reports = json.loads((root / "results.json").read_text(encoding="utf-8"))["sports"]
    checked = {}
    for sport, report in reports.items():
        if report["matched_fixtures"] == 0:
            checked[sport] = {"status": "no_matched_odds"}
            continue
        ledger = pd.read_csv(root / sport / "fixtures.csv")
        assert len(ledger) == report["matched_fixtures"]
        assert not ledger.duplicated(["date", "home_team", "away_team"]).any()
        classes = ["away_win", "draw", "home_win"] if sport == "football" else ["away_win", "home_win"]
        decisive = ledger.result.isin(classes)
        y = np.array([classes.index(value) for value in ledger.loc[decisive, "result"]])
        for prefix, name in [("model", "model"), ("bookmaker", "bookmaker")]:
            probabilities = ledger.loc[decisive, [f"{prefix}_{value}" for value in classes]].to_numpy(float)
            scored = probability_metrics(y, probabilities, classes)
            for key in ["accuracy", "log_loss", "brier_score"]:
                np.testing.assert_allclose(scored[key], report[name][key], atol=1e-12, rtol=0)
        if sport != "football":
            offers = pd.read_csv(root / sport / "offers.csv")
            history = pd.read_parquet(Path(report["candidate"]) / "dataset.parquet")
            keys = ["date", "home_key", "away_key"]
            history["date"] = pd.to_datetime(history.date, utc=True)
            lookup = {tuple(row[key] for key in keys): i for i, row in history.iterrows()}
            captures = {}
            for row in ledger.to_dict("records"):
                index = lookup[(pd.Timestamp(row["date"]), row["home_key"], row["away_key"])]
                quote = offers[(offers.fixture_index == index) & (offers.bookmaker == row["selected_bookmaker"])]
                assert len(quote) == 1
                price = float(quote.iloc[0][row["ev_selection"]])
                source = quote.iloc[0].source_file
                if source not in captures:
                    captures[source] = json.loads(Path(source).read_text(encoding="utf-8"))
                event = next(event for event in captures[source]["events"] if event["id"] == quote.iloc[0].provider_event_id)
                book = next(book for book in event["bookmakers"] if book["key"] == row["selected_bookmaker"])
                market = next(market for market in book["markets"] if market["key"] == "h2h")
                team = event["away_team"] if row["ev_selection"] == "away_win" else event["home_team"]
                raw_price = next(outcome["price"] for outcome in market["outcomes"] if outcome["name"] == team)
                np.testing.assert_allclose(price, raw_price, atol=0, rtol=0)
                np.testing.assert_allclose(price, row[f"best_odds_{row['ev_selection']}"])
                probability = row[f"model_{row['ev_selection']}"]
                assert bool(row["bet"]) == (probability * price - 1 >= .05)
                expected = 0 if not row["bet"] or row["void"] else price - 1 if row["result"] == row["ev_selection"] else -1
                np.testing.assert_allclose(row["profit_units"], expected, atol=1e-12, rtol=0)
                assert pd.Timestamp(row["observation_upper_bound"]) < pd.Timestamp(row["captured_kickoff"])
            for path, sha256 in report["audit"]["source_checksums"].items():
                assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == sha256
        np.testing.assert_allclose(ledger.profit_units.sum(), report["model_ev_policy"]["profit_units"], atol=1e-12, rtol=0)
        checked[sport] = {"status": "verified", "ledger_rows": len(ledger), "metrics_reproduced": True,
                          "actual_book_prices_checked": sport != "football"}
        print(json.dumps({"sport": sport, **checked[sport]}), flush=True)
    (root / "verification.json").write_text(json.dumps(checked, indent=2), encoding="utf-8")
    return checked


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-dir", type=Path, required=True)
    args = parser.parse_args()
    verify(args.report_dir)


if __name__ == "__main__":
    main()
