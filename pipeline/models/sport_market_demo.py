"""Compare saved sport candidates with captured bookmaker offers at quote time."""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re

import joblib
import numpy as np
import pandas as pd
import requests
from threadpoolctl import threadpool_limits

from config import RAW_DATA_DIR
from models.market_demo import paired_comparison, paper_policy, paper_roi_interval, make_report
from models.sport_features import live_features
from models.sport_predict import candidate_directory
from models.validation import probability_metrics

RUNS = {"basketball": "20261009T100528981075Z", "wnba": "20261009T103733107847Z",
        "ncaab": "20261009T103733107847Z", "ncaabw": "20261009T103733107847Z",
        "nfl": "20261009T144354530070Z", "ncaaf": "20261009T144354530070Z"}
LEAGUES = {"basketball": "basketball_nba", "wnba": "basketball_wnba", "ncaab": "basketball_ncaab",
           "ncaabw": "basketball_wncaab", "nfl": "americanfootball_nfl", "ncaaf": "americanfootball_ncaaf"}
CLASSES = ["away_win", "home_win"]


def observation_bounds(value: str) -> tuple[pd.Timestamp, pd.Timestamp, str]:
    if re.fullmatch(r"\d{8}_\d{6}", value):
        nominal = pd.to_datetime(value, format="%Y%m%d_%H%M%S", utc=True)
        # The legacy writer recorded local wall time without its timezone.
        # Global UTC offsets bound capture time; history uses the earliest bound.
        return nominal - pd.Timedelta(hours=14), nominal + pd.Timedelta(hours=12), "UNKNOWN_TIMEZONE_BOUNDED"
    observed = pd.Timestamp(value)
    if observed.tzinfo is None:
        raise ValueError("Odds observation timestamp must include a timezone")
    return observed.tz_convert("UTC"), observed.tz_convert("UTC"), "EXPLICIT_TIMEZONE"


def team_aliases(games: pd.DataFrame, directory: dict | None = None) -> dict[str, str]:
    names = defaultdict(set)
    ids = defaultdict(set)
    for row in games.to_dict("records"):
        for side in ["home", "away"]:
            key = row[f"{side}_key"]
            names[key].add(key)
            if row.get(f"provider_{side}_team_id") is not None:
                ids[str(row[f"provider_{side}_team_id"])].add(key)
    if directory:
        for sport in directory.get("sports", []):
            for league in sport.get("leagues", []):
                for entry in league.get("teams", []):
                    team = entry["team"]
                    targets = ids.get(str(team["id"]), set())
                    for field in ["displayName", "location", "shortDisplayName"]:
                        if team.get(field):
                            names[team[field].casefold().strip()].update(targets)
    return {name: next(iter(keys)) for name, keys in names.items() if len(keys) == 1}


def matched_offers(games: pd.DataFrame, league: str, aliases: dict, root: Path = RAW_DATA_DIR) -> tuple[pd.DataFrame, dict]:
    keys = ["date", "home_key", "away_key"]
    lookup = {tuple(row[key] for key in keys): i for i, row in games.iterrows()
              if row.get("date_precision") == "TIMESTAMP"}
    provider_ids = defaultdict(list)
    for i, row in games.iterrows():
        provider_id = str(row.get("provider_event_id", ""))
        if row.get("date_precision") == "TIMESTAMP" and re.fullmatch(r"[a-f0-9]{32}", provider_id):
            provider_ids[provider_id].append(i)
    offers, counts = [], Counter()
    sources = {}
    for path in sorted((root / "the_odds_api").glob(f"odds_{league}_*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        counts["capture_files"] += 1
        if not isinstance(data, dict) or not data.get("fetched_at"):
            counts["missing_observation_timestamp"] += 1
            continue
        earliest, latest, precision = observation_bounds(data["fetched_at"])
        source = str(path.resolve())
        sources[source] = hashlib.sha256(path.read_bytes()).hexdigest()
        for event in data.get("events", []):
            counts["events"] += 1
            kickoff = pd.to_datetime(event["commence_time"], utc=True)
            if event.get("sport_key") != league or latest >= kickoff:
                counts["not_certainly_pregame"] += 1
                continue
            hk, ak = aliases.get(event["home_team"].casefold().strip()), aliases.get(event["away_team"].casefold().strip())
            index = lookup.get((kickoff, hk, ak))
            identity_method = "EXACT_TEAMS_AND_KICKOFF"
            if index is None and len(provider_ids.get(event["id"], [])) == 1:
                candidate = provider_ids[event["id"]][0]
                game = games.loc[candidate]
                if game.home_key == hk and game.away_key == ak and abs(game.date - kickoff) <= pd.Timedelta(hours=6) and latest < game.date:
                    index = candidate
                    identity_method = "EXACT_PROVIDER_EVENT_ID_AND_TEAMS"
                    counts["provider_id_start_time_adjustments"] += 1
            if index is None:
                counts["outside_test_or_unmatched_identity_time"] += 1
                continue
            for bookmaker in event.get("bookmakers", []):
                for market in bookmaker.get("markets", []):
                    if market.get("key") != "h2h":
                        continue
                    outcomes = market.get("outcomes", [])
                    prices = {item["name"]: item["price"] for item in outcomes}
                    if len(outcomes) != 2 or set(prices) != {event["home_team"], event["away_team"]}:
                        continue
                    h, a = float(prices[event["home_team"]]), float(prices[event["away_team"]])
                    if not np.isfinite([h, a]).all() or min(h, a) <= 1:
                        continue
                    updated = market.get("last_update") or bookmaker.get("last_update")
                    if not updated or pd.to_datetime(updated, utc=True) >= kickoff or pd.to_datetime(updated, utc=True) > latest:
                        continue
                    offers.append({"fixture_index": index, "bookmaker": bookmaker["key"], "bookmaker_title": bookmaker.get("title"),
                        "away_win": a, "home_win": h, "quote_as_of": earliest, "observation_upper_bound": latest,
                        "observation_precision": precision, "provider_updated_at": updated,
                        "source_file": source, "source_sha256": sources[source], "provider_event_id": event["id"]})
                    offers[-1].update(identity_method=identity_method, captured_kickoff=kickoff)
    frame = pd.DataFrame(offers)
    if not frame.empty:
        # Every book for a fixture comes from the same selected capture file.
        selected = frame.sort_values(["observation_upper_bound", "source_file"]).drop_duplicates("fixture_index", keep="last")
        frame = frame.merge(selected[["fixture_index", "source_file"]], on=["fixture_index", "source_file"], validate="many_to_one")
        frame = frame.sort_values("bookmaker").drop_duplicates(["fixture_index", "bookmaker"])
    return frame, {"counts": dict(counts), "source_checksums": sources}


def evaluate_sport(sport: str, output: Path, team_directory: dict | None = None, samples: int = 4000) -> dict:
    directory = candidate_directory(RUNS[sport], sport)
    metrics = json.loads((directory / "metrics.json").read_text(encoding="utf-8"))
    for filename, key in [("dataset.parquet", "dataset_sha256"), ("model.pkl", "model_sha256")]:
        if hashlib.sha256((directory / filename).read_bytes()).hexdigest() != metrics[key]:
            raise ValueError("Candidate checksum mismatch")
    history = pd.read_parquet(directory / "dataset.parquet")
    boundary = pd.Timestamp(metrics["splits"]["test"]["start"])
    # Preserve ties in the evaluation ledger: two-way NFL bets void on a tie.
    test = history[history.date.ge(boundary) & history.league.eq(LEAGUES[sport])]
    offers, audit = matched_offers(test, LEAGUES[sport], team_aliases(history, team_directory))
    result = {"sport": sport, "candidate_id": RUNS[sport], "candidate": str(directory),
        "dataset_sha256": metrics["dataset_sha256"], "model_sha256": metrics["model_sha256"],
        "test_fixtures": len(test), "matched_fixtures": int(offers.fixture_index.nunique()) if not offers.empty else 0,
        "status": "no_matched_odds", "audit": audit}
    output.mkdir(parents=True, exist_ok=False)
    if offers.empty:
        (output / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result
    model = joblib.load(directory / "model.pkl")
    if model.market_model is not None:
        raise ValueError("Quote-time evaluation requires a history-only saved candidate")
    fixtures, vectors, markets, best_prices, best_books = [], [], [], [], []
    for index, group in offers.groupby("fixture_index", sort=True):
        game = history.loc[index].to_dict()
        as_of = group.quote_as_of.iloc[0]
        if as_of.normalize() <= pd.Timestamp(metrics["splits"]["calibration"]["end"]).normalize():
            raise ValueError("Quote predates completed calibration period")
        vectors.append(live_features(history, sport, game | {"date": group.captured_kickoff.iloc[0]}, as_of=as_of))
        prices = group[CLASSES].to_numpy(float)
        implied = 1 / prices
        markets.append((implied / implied.sum(axis=1)[:, None]).mean(axis=0))
        winners = prices.argmax(axis=0)
        best_prices.append(prices[winners, np.arange(2)])
        best_books.append(group.bookmaker.to_numpy()[winners])
        fixtures.append(game | {"quote_as_of": as_of, "observation_upper_bound": group.observation_upper_bound.iloc[0],
                               "observation_precision": group.observation_precision.iloc[0], "source_file": group.source_file.iloc[0],
                               "captured_kickoff": group.captured_kickoff.iloc[0], "identity_method": group.identity_method.iloc[0]})
    ledger = pd.DataFrame(fixtures)
    with threadpool_limits(limits=2):
        probabilities = model.predict_proba(pd.concat(vectors, ignore_index=True))
    market, prices, books = np.array(markets), np.array(best_prices), np.array(best_books)
    decisive = ledger.result.ne("draw").to_numpy()
    y = np.array([CLASSES.index(value) if value in CLASSES else 0 for value in ledger.result])
    comparison = paired_comparison(y[decisive], probabilities[decisive], market[decisive], ledger.loc[decisive, "date"], samples, classes=CLASSES)
    policy_summary, policy = paper_policy(y, probabilities, prices, classes=CLASSES)
    voids = policy["bet"] & ~decisive
    placed_bets = policy["bet"].copy()
    policy["profit"][~decisive] = 0
    policy["bet"][~decisive] = False
    stakes = int(policy["bet"].sum())
    policy_summary.update(bets=int(placed_bets.sum()), void_bets=int(voids.sum()), stake_units=stakes,
        wins=int((policy["bet"] & (policy["picks"] == y)).sum()), profit_units=float(policy["profit"].sum()),
        roi=float(policy["profit"].sum() / stakes) if stakes else None,
        roi_ci95=paper_roi_interval(policy, ledger.date, samples))
    for i, name in enumerate(CLASSES):
        ledger[f"model_{name}"] = probabilities[:, i]
        ledger[f"bookmaker_{name}"] = market[:, i]
        ledger[f"best_odds_{name}"] = prices[:, i]
        ledger[f"best_book_{name}"] = books[:, i]
    ledger["model_pick"], ledger["bookmaker_pick"] = np.array(CLASSES)[probabilities.argmax(axis=1)], np.array(CLASSES)[market.argmax(axis=1)]
    ledger["ev_selection"] = np.array(CLASSES)[policy["picks"]]
    ledger["selected_bookmaker"] = books[np.arange(len(y)), policy["picks"]]
    ledger["predicted_ev"], ledger["bet"], ledger["void"], ledger["profit_units"] = policy["ev"], placed_bets, voids, policy["profit"]
    per_book = {}
    indexed = {index: i for i, index in enumerate(sorted(offers.fixture_index.unique()))}
    for bookmaker, group in offers.groupby("bookmaker"):
        selected = np.array([indexed[i] for i in group.fixture_index])
        selected = selected[decisive[selected]]
        book_prices = group.set_index("fixture_index").loc[[sorted(indexed)[i] for i in selected], CLASSES].to_numpy(float)
        if not len(selected):
            continue
        implied = 1 / book_prices
        fair = implied / implied.sum(axis=1)[:, None]
        per_book[bookmaker] = {"model": probability_metrics(y[selected], probabilities[selected], CLASSES),
                              "bookmaker": probability_metrics(y[selected], fair, CLASSES)}
    result.update(status="compared", scored_fixtures=int(decisive.sum()), ties=int((~decisive).sum()),
        start=ledger.date.min().isoformat(), end=ledger.date.max().isoformat(),
        model=probability_metrics(y[decisive], probabilities[decisive], CLASSES),
        bookmaker=probability_metrics(y[decisive], market[decisive], CLASSES), paired_comparison=comparison,
        model_ev_policy=policy_summary, per_bookmaker=per_book,
        verdict="No bookmaker advantage established" if not (comparison["log_loss"]["positive_ci"] and comparison["brier_score"]["positive_ci"]) else "Historical probability advantage; prospective validation required",
        limits=["Retrospective inspected candidates; not a prospective final test.",
                "One synchronized capture per fixture; bookmaker baseline averages separately margin-normalized two-way probabilities.",
                "Legacy capture timezones are unknown: UTC+14/-12 bounds require the latest possible capture before kickoff and history before the earliest capture's UTC day.",
                "Paper policy: fixed 5% EV, one flat-unit bet per fixture at the best actual quoted book price; no threshold tuning.",
                "Quote availability, limits, fees and slippage are unverified; returns are indicative paper results.",
                "NFL final ties void paper stakes and are excluded from conditional probability scoring.",
                "Confidence intervals resample UTC fixture days; residual team/season dependence remains."])
    ledger.to_csv(output / "fixtures.csv", index=False)
    offers.to_csv(output / "offers.csv", index=False)
    (output / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def render_overview(result: dict) -> str:
    rows = []
    for sport, report in result["sports"].items():
        if "model" not in report:
            rows.append({"Sport": sport, "Games": 0, "Model accuracy": "Unavailable", "Bookmaker accuracy": "Unavailable",
                         "Model log loss": "—", "Bookmaker log loss": "—", "Paper ROI": "—", "ROI 95% interval": "—"})
        else:
            policy = report["model_ev_policy"]
            bounds = policy.get("roi_ci95")
            rows.append({"Sport": "NBA" if sport == "basketball" else "Soccer" if sport == "football" else sport,
                "Games": report["matched_fixtures"], "Model accuracy": f"{report['model']['accuracy']:.2%}",
                "Bookmaker accuracy": f"{report['bookmaker']['accuracy']:.2%}",
                "Model log loss": f"{report['model']['log_loss']:.4f}", "Bookmaker log loss": f"{report['bookmaker']['log_loss']:.4f}",
                "Paper ROI": f"{policy['roi']:.2%}" if policy["roi"] is not None else "No bets",
                "ROI 95% interval": f"[{bounds[0]:.1%}, {bounds[1]:.1%}]" if bounds else "Unavailable"})
    links = "".join(f'<li><a href="{sport}/results.json">{html.escape(sport)} full results</a></li>' for sport in result["sports"])
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bookmaker comparisons</title><style>body{font:16px/1.6 system-ui;background:#f6f8f6;color:#182c25;margin:0}main{max-width:1200px;margin:auto;padding:32px}section{background:white;border:1px solid #d6dfd9;padding:24px;margin:20px 0}.scroll{overflow:auto}table{border-collapse:collapse;font-size:14px;width:100%}td,th{padding:10px;border-bottom:1px solid #dde4df;text-align:left}th{background:#edf3ef}a{color:#176f51}</style><main><h1>Basketball and football bookmaker comparisons</h1><section><h2>No established bookmaker advantage</h2><p>Matched historical games, fixed models and a fixed 5% EV paper policy. Small basketball samples and wide uncertainty prevent reliable conclusions. Actual quote availability, limits and costs have not been verified.</p></section><section class="scroll">' + pd.DataFrame(rows).to_html(index=False, escape=True) + '</section><section><h2>Method and limits</h2><p>Lower log loss is better. Bookmaker probabilities remove proportional margin. NBA, NCAA men, NFL and college football predictions use only history available before the earliest possible snapshot time; one synchronized capture supplies each fixture’s prices. Confidence intervals resample fixture days. Soccer uses historical odds without exact observation times and is a separate, weaker evidence track.</p><p>WNBA and NCAA women have no matched stored quotes. Most NBA historical rows lack exact kickoff times; stable event IDs resolve verified tip-off differences without fuzzy matching.</p><h2>Evidence</h2><ul>' + links + '</ul><p><a href="results.json">Combined machine-readable results</a> · <a href="verification.json">Independent ledger audit</a></p></section></main></html>'


def run(output: Path, samples: int = 4000) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    url = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/teams"
    response = requests.get(url, params={"limit": 1000}, timeout=(10, 60))
    response.raise_for_status()
    path = output / "college_team_directory.json"
    path.write_bytes(response.content)
    directory = response.json()
    result = {"generated_at": datetime.now(timezone.utc).isoformat(),
              "team_directory": {"source_url": response.url, "sha256": hashlib.sha256(response.content).hexdigest()}, "sports": {}}
    for sport in RUNS:
        print(f"Comparing {sport}...", flush=True)
        result["sports"][sport] = evaluate_sport(sport, output / sport, directory if sport == "ncaaf" else None, samples)
        print(json.dumps({"sport": sport, "matched_fixtures": result["sports"][sport]["matched_fixtures"]}), flush=True)
    soccer = candidate_directory("20261009T100528981075Z", "football")
    result["sports"]["football"] = make_report(soccer, output / "football", samples=samples)
    # Soccer's historical B365 odds lack quote timestamps, so its evidence is
    # reported separately from the quote-time sport comparisons above.
    result["sports"]["football"]["status"] = "historical_odds_without_observation_times"
    (output / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (output / "index.html").write_text(render_overview(result), encoding="utf-8")
    print(f"Comparison report: {output / 'index.html'}", flush=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--bootstrap-samples", type=int, default=4000)
    args = parser.parse_args()
    if args.bootstrap_samples < 100:
        parser.error("Need at least 100 bootstrap samples")
    run(args.output_dir, args.bootstrap_samples)


if __name__ == "__main__":
    main()
