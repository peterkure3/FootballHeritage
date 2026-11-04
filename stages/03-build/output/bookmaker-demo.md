# Bookmaker comparison demo — 2026-10-08

Open `bookmaker-demo/demo.html`. Complete data exports: `fixtures.csv` and
`results.json` in the same directory. No model retraining or activation occurred.

## Finding

The model has not demonstrated a probability advantage over the bookmaker baseline.
All 108 odds-backed test fixtures were compared; 1,152 fixtures without odds were
excluded explicitly. Covered fixtures span 2024-05-12 through 2024-06-02 (14 UTC
fixture days). The model and proportional-margin-adjusted B365 probabilities use
the same fixtures, outcomes, and outcome order.

| Metric | Model | Bookmaker | Model advantage, 95% paired day-bootstrap interval |
|---|---:|---:|---:|
| Accuracy | 60.19% | 59.26% | +0.93 percentage points [-2.94, +4.05] |
| Log loss | 0.910246 | 0.910096 | -0.000150 [-0.041146, +0.028240] |
| Brier score | 0.537239 | 0.537079 | -0.000160 [-0.025383, +0.015721] |

Positive advantage means model minus market accuracy, or market minus model loss.
All intervals include zero. Lower log loss and Brier score indicate better forecast
quality; see the [scikit-learn scoring documentation](https://scikit-learn.org/stable/modules/model_evaluation.html).

## Fixed-rule paper simulation

Select at most one outcome per fixture by maximum `model_probability * raw_odds - 1`.
Bet one unit if expected return is at least 5%; no threshold optimization or filtering
by realized outcomes. Wins return decimal odds minus one, losses minus one.

- Model: 80 bets, 24 wins, +10.62 units, ROI +13.28%.
- Model ROI day-bootstrap 95% interval: -38.83% to +72.24%.
- Always backing the bookmaker favorite: 108 bets, +3.44 units, ROI +3.19%.
  This benchmark has different exposure and is not a matched strategy advantage test.
- Applying the same 5% EV rule to the margin-adjusted bookmaker probabilities places
  zero bets; removing margin does not create profitable offers at the same prices.

The positive realized paper return does not establish a repeatable profitable edge.
Historical odds lack a verified observation timestamp and executable prediction
horizon. Costs, slippage and limits are excluded. Previously inspected retrospective
test data is not fresh final acceptance data. Day blocks address within-day dependence
only. No real bets or external data calls were made.

## Reproduction and verification

From `pipeline/`, with a new destination directory:

```powershell
py -3 -m models.market_demo --bundle models/model_store/candidates/20261008T170059291611Z --output-dir ../stages/03-build/output/bookmaker-demo
py -3 -m unittest discover -s tests -v
py -3 -m compileall -q models tests
```

Shared bundle loading validates the frozen dataset SHA-256, feature schema, feature
order and encoder classes before evaluation. Report exports retain all matches and
both winning and losing bets. Uncertainty uses 4,000 paired day-block resamples with
seed 42. All 33 behavioral tests passed. Fallow root audit passed with no new
dead-code, complexity or duplication findings; its JS dependency warning and Python
coverage limitations remain. `pyarrow` was added to the small CI test dependency
list because artifact verification uses Parquet. Remote CI was not run.

Next acceptance experiment: freeze model and decision policy, record prediction
probabilities and available timestamped bookmaker offers before kickoff, retain
every predeclared fixture, then compare outcomes in a newly reserved future period.
No stage gate is advanced by this report.
