"""Export an auditable historical candidate-versus-bookmaker comparison."""

import argparse
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

sys.path.append(str(Path(__file__).parent.parent))
from models.evaluate import load_evaluation_bundle
from models.validation import probability_metrics


def paired_comparison(y: np.ndarray, model: np.ndarray, market: np.ndarray,
                      dates: pd.Series, samples: int = 4000, seed: int = 42,
                      classes: list[str] | None = None) -> dict:
    """Resample paired fixture days; positive differences favor the model."""
    if len(y) == 0 or samples < 100:
        raise ValueError("Need matched fixtures and at least 100 bootstrap samples")
    classes = classes or ["away_win", "draw", "home_win"]
    for probabilities in [model, market]:
        probability_metrics(y, probabilities, classes)
    actual = np.eye(len(classes))[y]
    index = np.arange(len(y))
    differences = np.column_stack([
        -np.log(np.clip(market[index, y], 1e-15, 1)) + np.log(np.clip(model[index, y], 1e-15, 1)),
        np.sum((market - actual) ** 2, axis=1) - np.sum((model - actual) ** 2, axis=1),
        (model.argmax(axis=1) == y).astype(float) - (market.argmax(axis=1) == y),
    ])
    days = pd.to_datetime(dates, utc=True).dt.normalize().to_numpy()
    if len(days) != len(y) or pd.isna(days).any():
        raise ValueError("Need one valid fixture day per prediction")
    blocks = [differences[days == day] for day in np.unique(days)]
    totals = np.array([block.sum(axis=0) for block in blocks])
    counts = np.array([len(block) for block in blocks])
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(blocks), size=(samples, len(blocks)))
    bootstrap = totals[draws].sum(axis=1) / counts[draws].sum(axis=1)[:, None]
    bounds = np.quantile(bootstrap, [0.025, 0.975], axis=0)
    return {name: {"advantage": float(differences[:, i].mean()),
                   "ci95": bounds[:, i].tolist(),
                   "positive_ci": bool(len(blocks) > 1 and bounds[0, i] > 0)}
            for i, name in enumerate(["log_loss", "brier_score", "accuracy"])} | {
                "fixture_days": len(blocks), "bootstrap_samples": samples, "seed": seed,
                "method": "paired fixture-day cluster bootstrap; positive favors model"}


def paper_policy(y: np.ndarray, probabilities: np.ndarray, odds: np.ndarray,
                 minimum_ev: float = 0.05, classes: list[str] | None = None) -> tuple[dict, dict]:
    """One flat-unit bet at most per fixture, selected without outcome information."""
    if not np.isfinite(odds).all() or (odds <= 1).any() or not np.isfinite(minimum_ev) or minimum_ev < 0:
        raise ValueError("Need observed decimal odds >1 and nonnegative EV threshold")
    if probabilities.shape != odds.shape or len(y) != len(odds):
        raise ValueError("Prediction, outcome and price dimensions differ")
    probability_metrics(y, probabilities, classes or ["away_win", "draw", "home_win"])
    ev = probabilities * odds - 1
    picks = ev.argmax(axis=1)
    rows = np.arange(len(y))
    chosen_ev = ev[rows, picks]
    bet = chosen_ev >= minimum_ev
    profit = np.where(bet, np.where(picks == y, odds[rows, picks] - 1, -1), 0)
    stakes = int(bet.sum())
    summary = {"bets": stakes, "stake_units": stakes,
               "profit_units": float(profit.sum()),
               "roi": float(profit.sum() / stakes) if stakes else None,
               "wins": int((bet & (picks == y)).sum()), "minimum_ev": minimum_ev}
    return summary, {"picks": picks, "bet": bet, "ev": chosen_ev, "profit": profit}


def paper_roi_interval(policy: dict, dates: pd.Series, samples: int = 4000) -> list[float] | None:
    """Resample entire fixture days, retaining both bets and non-bets."""
    days = pd.to_datetime(dates, utc=True).dt.normalize().to_numpy()
    blocks = np.unique(days)
    profit = np.array([policy["profit"][days == day].sum() for day in blocks])
    stakes = np.array([policy["bet"][days == day].sum() for day in blocks])
    if not stakes.sum() or len(blocks) < 2:
        return None
    draws = np.random.default_rng(42).integers(0, len(blocks), size=(samples, len(blocks)))
    sampled_stakes = stakes[draws].sum(axis=1)
    valid = sampled_stakes > 0
    returns = profit[draws].sum(axis=1)[valid] / sampled_stakes[valid]
    return np.quantile(returns, [0.025, 0.975]).tolist()


def make_report(bundle: Path, output: Path, minimum_ev: float = 0.05,
                samples: int = 4000) -> dict:
    data = load_evaluation_bundle(bundle)
    test_X = data.features.iloc[data.test_indices]
    covered = test_X.odds_missing.eq(0).to_numpy()
    if not covered.any():
        raise ValueError("No held-out fixtures have observed bookmaker odds")
    fixtures = data.fixtures.iloc[data.test_indices].iloc[np.flatnonzero(covered)].reset_index(drop=True)
    X = test_X.iloc[np.flatnonzero(covered)]
    classes = list(data.encoder.classes_)
    with threadpool_limits(limits=2):
        probabilities = data.model.predict_proba(X)
    market = X[[f"fair_{name.removesuffix('_win')}_prob" for name in classes]].to_numpy()
    odds = fixtures[classes].to_numpy(dtype=float)
    y = data.encoder.transform(fixtures.result)
    comparison = paired_comparison(y, probabilities, market, fixtures.date, samples)
    model_policy, policy = paper_policy(y, probabilities, odds, minimum_ev)
    model_policy["roi_ci95"] = paper_roi_interval(policy, fixtures.date, samples)
    market_policy, _ = paper_policy(y, market, odds, minimum_ev)
    # Fixed favorite benchmark has a different bet count; it is not an EV strategy.
    favorites = market.argmax(axis=1)
    favorite_profit = np.where(favorites == y, odds[np.arange(len(y)), favorites] - 1, -1)
    verdict = "Probability advantage supported on this historical sample" if (
        comparison["log_loss"]["positive_ci"] and comparison["brier_score"]["positive_ci"]
    ) else "Model advantage over bookmaker probabilities is not established"
    result = {"verdict": verdict, "generated_at": datetime.now(timezone.utc).isoformat(),
              "candidate": str(bundle), "dataset_sha256": data.manifest["dataset_sha256"],
              "model_version": data.manifest["model_version"], "classes": classes,
              "test_fixtures": len(test_X), "matched_fixtures": len(y),
              "excluded_without_odds": int((~covered).sum()),
              "start": fixtures.date.min().isoformat(), "end": fixtures.date.max().isoformat(),
              "model": probability_metrics(y, probabilities, classes),
              "bookmaker": probability_metrics(y, market, classes),
              "paired_comparison": comparison, "model_ev_policy": model_policy,
              "bookmaker_ev_policy": market_policy,
              "always_favorite_benchmark": {"bets": len(y), "profit_units": float(favorite_profit.sum()),
                                            "roi": float(favorite_profit.mean())},
              "limits": ["Retrospective development sample already inspected; not fresh final validation.",
                         "Bookmaker probabilities normalize inverse B365 decimal odds to remove proportional margin.",
                         "Historical odds have no precise observation timestamp or verified executable prediction horizon.",
                         "Paper returns exclude commission, slippage, stake limits and execution availability.",
                         f"The {minimum_ev:.0%} EV policy is fixed before this run; no threshold search or winning-fixture filter.",
                         "Fixture-day bootstrap handles within-day dependence, not all season/team dependence.",
                         "No real bets, new training, external data downloads or production activation."]}
    ledger = fixtures.reindex(columns=["date", "competition", "home_team", "away_team", "result"]).copy()
    for i, name in enumerate(classes):
        ledger[f"odds_{name}"] = odds[:, i]
        ledger[f"model_{name}"] = probabilities[:, i]
        ledger[f"bookmaker_{name}"] = market[:, i]
    ledger["model_pick"] = np.array(classes)[probabilities.argmax(axis=1)]
    ledger["bookmaker_pick"] = np.array(classes)[favorites]
    ledger["ev_selection"] = np.array(classes)[policy["picks"]]
    ledger["predicted_ev"] = policy["ev"]
    ledger["bet"] = policy["bet"]
    ledger["profit_units"] = policy["profit"]
    output.mkdir(parents=True, exist_ok=False)
    ledger.to_csv(output / "fixtures.csv", index=False)
    (output / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (output / "demo.html").write_text(render_report(result, ledger), encoding="utf-8")
    return result


def render_report(result: dict, ledger: pd.DataFrame) -> str:
    metric_rows = ""
    for name, label in [("accuracy", "Accuracy ↑"), ("log_loss", "Log loss ↓"), ("brier_score", "Brier score ↓")]:
        evidence = result["paired_comparison"][name]
        low, high = evidence["ci95"]
        metric_rows += f"<tr><td>{label}</td><td>{result['model'][name]:.6f}</td><td>{result['bookmaker'][name]:.6f}</td><td>{evidence['advantage']:+.6f}</td><td>[{low:+.6f}, {high:+.6f}]</td></tr>"
    policies = ""
    for key, label in [("model_ev_policy", "Model: ≥5% expected return"),
                       ("bookmaker_ev_policy", "Bookmaker: same EV rule"),
                       ("always_favorite_benchmark", "Always bookmaker favorite")]:
        policy = result[key]
        roi = f"{policy['roi']:.1%}" if policy['roi'] is not None else "No bets"
        policies += f"<tr><td>{label}</td><td>{policy['bets']}</td><td>{policy['profit_units']:+.2f}</td><td>{roi}</td></tr>"
    threshold = result["model_ev_policy"]["minimum_ev"]
    policies = policies.replace("≥5%", f"≥{threshold:.0%}")
    limits = "".join(f"<li>{html.escape(limit)}</li>" for limit in result["limits"])
    table = ledger[["date", "home_team", "away_team", "result", "model_pick", "bookmaker_pick", "ev_selection", "predicted_ev", "bet", "profit_units"]].to_html(index=False, escape=True, float_format=lambda v: f"{v:.4f}", border=0)
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>FootballHeritage — bookmaker comparison</title>
<style>body{{font:16px/1.55 system-ui,sans-serif;background:#f6f8f6;color:#182c25;margin:0}}main{{max-width:1150px;margin:auto;padding:32px}}h1{{font-size:32px}}section{{background:white;padding:24px;margin:20px 0;border:1px solid #d6dfd9}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{text-align:left;padding:10px;border-bottom:1px solid #dde4df}}th{{background:#edf3ef}}.scroll{{overflow:auto}}.verdict{{border-left:6px solid #b37a19}}a{{color:#176f51}}small{{color:#53685d}}@media print{{main{{padding:0}}section{{break-inside:avoid}}}}</style>
<main><small>FOOTBALLHERITAGE · HISTORICAL EVIDENCE DEMO</small><h1>Does our model beat bookmaker probabilities?</h1>
<section class="verdict"><h2>{html.escape(result['verdict'])}</h2><p>{result['matched_fixtures']} matched fixtures from {result['start'][:10]} to {result['end'][:10]}. {result['excluded_without_odds']} test fixtures excluded because no observed odds exist.</p><p>Candidate {html.escape(Path(result['candidate']).name)}. Every comparison uses the same fixtures and outcomes. Model selection and calibration used earlier date periods.</p></section>
<section><h2>Probability quality</h2><p>Positive paired advantage favors the model. Accuracy uses model minus bookmaker; loss metrics use bookmaker minus model. A confidence interval spanning zero does not establish a difference. Higher accuracy alone does not establish better probabilities.</p><div class="scroll"><table><tr><th>Metric</th><th>Model</th><th>Bookmaker</th><th>Paired advantage</th><th>95% day-bootstrap interval</th></tr>{metric_rows}</table></div><p>{result['paired_comparison']['bootstrap_samples']} paired resamples across {result['paired_comparison']['fixture_days']} UTC fixture days, seed 42. Lower log loss and Brier score reward better probability forecasts.</p></section>
<section><h2>Paper betting demonstration</h2><p>Choose the largest model probability × observed decimal odds − 1. Bet one unit only if expected return is at least {threshold:.0%}; maximum one bet per fixture. A win returns odds − 1 profit, a loss −1. Outcomes never select the bets.</p><table><tr><th>Fixed policy</th><th>Bets</th><th>Profit (units)</th><th>Return on stake</th></tr>{policies}</table><p>Model ROI 95% day-bootstrap interval: {html.escape(str(result['model_ev_policy']['roi_ci95']))}. Bounds are return fractions (0.10 = 10%). The favorite benchmark bets on every fixture and has different exposure. Observed paper profit is descriptive and is not proof of a repeatable edge.</p></section>
<section><h2>Limits and next validation</h2><ul>{limits}</ul><p>Next acceptance run: freeze the model and policy, archive predictions and timestamped available odds before kickoff, settle results, and compare all predeclared fixtures in a new future period.</p><p><a href="fixtures.csv">Download every matched fixture and probability</a> · <a href="results.json">Download metrics and provenance</a> · <a href="https://scikit-learn.org/stable/modules/calibration.html">Probability scoring reference</a></p><small>Dataset SHA-256: {result['dataset_sha256']}</small></section>
<section><h2>Complete fixture ledger</h2><p>All {len(ledger)} matched fixtures, chronologically ordered; winning and losing bets are retained. Full probability vectors and raw odds are in the CSV.</p><div class="scroll">{table}</div></section></main></html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--minimum-ev", type=float, default=0.05)
    parser.add_argument("--bootstrap-samples", type=int, default=4000)
    args = parser.parse_args()
    result = make_report(args.bundle, args.output_dir, args.minimum_ev, args.bootstrap_samples)
    print(json.dumps({key: result[key] for key in ["verdict", "matched_fixtures", "paired_comparison", "model_ev_policy", "bookmaker_ev_policy"]}, indent=2))


if __name__ == "__main__":
    main()
