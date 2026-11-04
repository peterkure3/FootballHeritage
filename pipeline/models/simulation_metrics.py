"""Distribution scores for paired home/away final scores, shared across sports."""
import numpy as np


def empirical_crps(samples: np.ndarray, observed: float) -> float:
    values = np.sort(np.asarray(samples, dtype=float))
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all() or not np.isfinite(observed):
        raise ValueError("CRPS needs finite observations and a nonempty vector")
    n = len(values)
    return float(np.mean(abs(values - observed)) - np.dot(2 * np.arange(n) - n + 1, values) / n ** 2)


def paired_score_metrics(scores: np.ndarray, observed: np.ndarray) -> dict:
    scores, observed = np.asarray(scores, dtype=float), np.asarray(observed, dtype=float)
    if (scores.ndim != 2 or scores.shape[1] != 2 or len(scores) < 2 or observed.shape != (2,)
            or not np.isfinite(scores).all() or not np.isfinite(observed).all()
            or (scores < 0).any() or (observed < 0).any()
            or (scores != np.floor(scores)).any() or (observed != np.floor(observed)).any()):
        raise ValueError("Need at least two paired nonnegative integer final scores and one observed pair")
    result = {"runs": len(scores), "distributions": {},
              "sampling_error_note": "Monte Carlo standard errors assume independent runs conditional on the fitted model; they do not measure model uncertainty."}
    for name, draws, actual in [("margin", scores[:, 0] - scores[:, 1], observed[0] - observed[1]),
                                ("total", scores.sum(axis=1), observed.sum())]:
        intervals = {}
        for coverage in [.8, .9, .95]:
            low, high = np.quantile(draws, [(1 - coverage) / 2, (1 + coverage) / 2])
            intervals[str(coverage)] = {"bounds": [float(low), float(high)],
                                       "covered": bool(low <= actual <= high), "width": float(high - low)}
        result["distributions"][name] = {"observed": float(actual), "mean": float(draws.mean()),
            "crps": empirical_crps(draws, actual), "intervals": intervals,
            "quantiles": dict(zip(["p01", "p05", "p50", "p95", "p99"], np.quantile(draws, [.01, .05, .5, .95, .99]).tolist())),
            "mean_mc_standard_error": float(draws.std(ddof=1) / np.sqrt(len(draws)))}
    margin = scores[:, 0] - scores[:, 1]
    probabilities = np.array([(margin > 0).mean(), (margin == 0).mean(), (margin < 0).mean()])
    result["outcome_probabilities_home_draw_away"] = probabilities.tolist()
    result["outcome_mc_standard_errors"] = np.sqrt(probabilities * (1 - probabilities) / len(scores)).tolist()
    return result
