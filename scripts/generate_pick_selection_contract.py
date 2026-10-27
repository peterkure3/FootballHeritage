"""Freeze synthetic cross-language examples from the existing Python ranking code."""

import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from api.ai_picks import build_picks


def row(identifier, probabilities, quotes):
    return {
        "match_id": identifier,
        "home_team": f"Test home {identifier}",
        "away_team": f"Test away {identifier}",
        "competition": "Synthetic contract league",
        "match_date": "2030-01-02T12:00:00+00:00",
        "model_version": "test-only-model",
        "prediction_created_at": "2030-01-01T12:00:00+00:00",
        **dict(
            zip(("home_prob", "draw_prob", "away_prob"), probabilities, strict=True)
        ),
        "quotes": quotes,
    }


def quote(bookmaker, prices):
    return {
        "bookmaker": bookmaker,
        "updated_at": "2030-01-01T12:01:00+00:00",
        **dict(zip(("home_win", "draw", "away_win"), prices, strict=True)),
    }


def main():
    rng = random.Random(20261026)
    cases = [
        {"name": "empty", "rows": [], "limit": 10},
        {
            "name": "missing_quotes_and_probability_tie",
            "rows": [row(1, [0.4, 0.4, 0.2], [])],
            "limit": 10,
        },
        {
            "name": "value_index_tie_and_first_bookmaker_tie",
            "rows": [
                row(
                    2,
                    [1 / 3, 1 / 3, 1 / 3],
                    [quote("first", [4.0, 4.0, 4.0]), quote("second", [4.0, 4.0, 4.0])],
                )
            ],
            "limit": 10,
        },
        {
            "name": "invalid_probabilities_and_prices",
            "rows": [
                row(3, [0.8, 0.8, 0.2], []),
                row(4, [-0.1, 0.6, 0.5], []),
                row(5, [0.5, 0.3, 0.2], [quote("invalid", [None, 1.0, "NaN"])]),
                row(
                    6, [0.6, 0.2, 0.2], [quote("string-prices", ["2.0", "3.0", "4.0"])]
                ),
            ],
            "limit": 20,
        },
    ]
    for scenario in range(8):
        rows = []
        for identifier in range(1, 31):
            weights = [rng.random() for _ in range(3)]
            probabilities = [value / sum(weights) for value in weights]
            quotes = [
                quote(
                    f"test-book-{book}",
                    [round(rng.uniform(1.05, 8), 4) for _ in range(3)],
                )
                for book in range(rng.randrange(4))
            ]
            rows.append(row(scenario * 100 + identifier, probabilities, quotes))
        cases.append(
            {
                "name": f"seeded-ranking-{scenario}",
                "rows": rows,
                "limit": 1 + scenario * 2,
            }
        )
    for case in cases:
        case["expected"] = build_picks(case["rows"], case["limit"])
    result = {
        "synthetic_test_data_only": True,
        "python_source_sha256": hashlib.sha256(
            (ROOT / "pipeline/api/ai_picks.py").read_bytes()
        ).hexdigest(),
        "cases": cases,
    }
    target = ROOT / "backend/tests/fixtures/ai_pick_selection_contract.json"
    rendered = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if target.exists():
        if target.read_text(encoding="utf-8") != rendered:
            raise SystemExit("Existing contract differs; review before regenerating it")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
    print(f"Validated {len(cases)} synthetic Python ranking contract cases")


if __name__ == "__main__":
    main()
