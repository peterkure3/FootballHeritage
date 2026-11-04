# Soccer event dataset and simulation baseline

## Outcome

Built an isolated, runnable soccer possession/event Monte Carlo baseline from the
original Wyscout public archive. It generates regulation-time action sequences,
scoreline/goal-difference distributions and correlated team/player event counts.
All production model selection, databases, APIs and schedules remain untouched.

This is a historical research baseline. Holdout results do not justify promotion:
outcome performance is mixed and pass-count intervals are substantially too narrow.
It does not reconstruct continuous movement of 22 players or reproduce the future
actual match. No current-season fixture forecasts are claimed.

## Dataset and provenance

- 3,251,294 events across all 1,941 published matches; seven competition files.
- 1,930 matches pass the implemented gates; 11 quarantined: seven score/halftime
  inconsistencies, three invalid-coordinate cases and one incomplete period.
- All four data assets pass the publisher's MD5 and size checks; SHA-256 captures
  identify all downloaded bytes. Normalized match files have separate checksums.
- Original ZIP/JSON files are preserved; per-match gzip JSON retains provider
  event/player/team IDs, source order, periods, clocks, tags and coordinates.
- Source: Wyscout, released by Pappalardo and Massucco; cite
  [Pappalardo et al. (2019)](https://doi.org/10.1038/s41597-019-0247-7) and the
  [Figshare collection](https://doi.org/10.6084/m9.figshare.c.4415000).
- Original dataset metadata explicitly specifies CC BY 4.0. Preserve attribution,
  license links and transformation notices. No StatsBomb data entered these models.

The verified Figshare article IDs are Players **7765196**, Teams **7765310**,
Events **7770599**, Matches **7770422**. The Events/Matches IDs were transposed in
one section of the earlier discovery report; the capture metadata and collector
use the correct titles and file URLs.

Coverage: 2017/18 England, France, Germany, Italy and Spain; Euro 2016 and World
Cup 2018. Data integrity checks establish provider consistency, not independent
video verification of every action. Period-end coverage uses the last observed
event and a completeness threshold, not an official whistle feed.

Data gaps remain explicit. There are 226,038 actor-less event records, mostly
interruptions/duels, including 12,102 free kicks, 260 other on-ball actions, 31
passes and three shots. Another 851 events across 184 matches fall outside the
substitution-time tolerance. Those interval diagnostics do not automatically
quarantine an otherwise score-consistent match. Unknown catalogue players retain
their native ID and an explicit unknown label/role.

## Implementation

| Module | Responsibility |
|---|---|
| `pipeline/etl/fetch_soccer_events.py` | Resumable Scrapling acquisition, robots-policy checks, license, size, MD5 and SHA-256 verification |
| `pipeline/etl/soccer_event_dataset.py` | Streaming ZIP/JSON normalisation, roster/coordinate/clock/score checks, quarantine and per-match checksums |
| `pipeline/models/soccer_possessions.py` | Fit empirical possession templates and smoothed team scoring effects; vectorized Monte Carlo rollouts |
| `pipeline/models/soccer_players.py` | Assign active actors using historical per-90 usage and role priors; sampled outfield substitutions; consistent player/team statistics |
| `pipeline/models/run_soccer_simulation.py` | Frozen chronological split, saved models, goal baseline, proper scores, replay checks and resume validation |
| `pipeline/models/evaluate_soccer_players.py` | Per-fixture test-set player distributions and explicit missing-actor exclusions |
| `pipeline/scripts/simulate_soccer_fixtures.py` | Batch inference from explicit native-ID fixture and optional lineup scenarios |

The model resamples sequences of passes, free kicks, shots and other on-ball
actions. Paired duels are excluded from control decisions but remain in the
dataset. Sampling conditions on half, score-margin sign, one of three longitudinal
field zones and nominal home/away side, with smoothed attacking/defending effects.
The final possession of each half is right-censored and excluded from the duration
template pool. This is a fitted possession bootstrap, not a neural next-event model.

Actor selection is conditional on supplied starting XI and bench, with smoothed
training-only player usage and role-compatible replacements. The baseline samples
up to three outfield substitutions at training-derived times. It does not model
red cards, injuries, tactical formations, individual finishing skill, assists,
extra time or shootouts. Donor coordinates use Wyscout's attacking-direction
0–100 grid; they do not constitute a continuous physical trajectory.

Team/player goals, shots, shots on target, passes, completed passes, corners and
own goals come from the same sampled actions. Keeper saves are defined as opposing
non-goal shots on target. Own goals credit the opponent once; the conceding side
restarts. Second-half kickoff switches sides. Actors must be active at their
sampled action time; player/team counts reconcile on every player trajectory.

Passing here includes non-shot free kicks/restarts, so these counts are explicitly
provider-derived definitions and need not match a bookmaker's box-score definition.

## Chronological evaluation

Each competition independently uses approximately 70% training, 15% validation
and 15% test, keeping identical kickoff timestamps together. The frozen baseline
was not tuned using validation/test results. Donor-match IDs are audited against
training IDs; forecast kickoff must follow training cutoff, including ISO timezone
inputs. Held-out substitutions, goals and observed action sequences are not inputs.
Archived starting XI/bench are treated as confirmed-at-kickoff scenarios; their
historical publication timestamps were not independently established.

Totals: **1,341 training, 295 validation, 294 test fixtures**. Every validation and
test fixture received **1,000 complete match simulations: 589,000 rollouts**.

The comparator is an independent Poisson goal model with smoothed team attack/
defense and training-derived nominal home/away rates. Outcome log loss is lower
when better; the table is descriptive and does not establish statistical superiority.

| Competition | Train / validation / test | Event model test log loss | Goal baseline | Event model pass-total 90% interval coverage |
|---|---|---:|---:|---:|
| England | 264 / 57 / 57 | 1.0668 | 1.0474 | 64.9% |
| Euro 2016 | 34 / 9 / 8 | 1.1522 | 1.0708 | 62.5% |
| France | 262 / 59 / 58 | 0.9948 | 1.0077 | 81.0% |
| Germany | 212 / 46 / 46 | 1.0036 | 0.9981 | 69.6% |
| Italy | 262 / 57 / 58 | 1.0302 | 1.0363 | 56.9% |
| Spain | 264 / 57 / 57 | 1.0633 | 1.0652 | 59.6% |
| World Cup 2018 | 43 / 10 / 10 | 1.2186 | 1.1374 | 80.0% |

Full outputs also include multiclass Brier score, accuracy, count CRPS, observed
and simulated means, and interval coverage for all supported team count variables.
England completed-pass coverage is only 52.6% at a nominal 90%. Sampling more runs
will not repair this underdispersion; the model needs between-match pace/style
variation and improved conditional action/actor models.

## Player evaluation and distribution example

The chronological test set has per-fixture player distributions from **100 complete
player trajectories per game: 29,400 trajectories across all 294 test fixtures,
with no fixture-level roster exclusions**, separate from the 1,000-run team outcome estimates.
Player statistics are evaluated using empirical-distribution CRPS and 90% interval
coverage. A fixture/stat is not scored when observed actor identities are incomplete;
unknown is never converted to an observed player zero. Averages include the bench's
zero-minute players, so high coverage for rare goals is not proof of strong props.
Goalkeeper-save attribution is accounting-checked, not independently calibrated
against a second provider's named goalkeeper statistics.

The historical example (Wyscout match 2500042) has 10,000 team simulations, 250
player trajectories and a 1,076-action trace with native donor-event provenance.
Its serialized model reproduces the seeded samples and trajectory references.
A separate 50,000-run check gives home/draw/away probabilities of
78.734% / 13.330% / 7.936%. Differences from the 10,000-run example are all below
0.13 percentage points and within approximate Monte Carlo sampling noise.
This checks numerical sampling stability, not forecast accuracy or parameter uncertainty.

## Reproduce

From `pipeline/`, using the existing Scrapling environment for acquisition and the
normal modeling environment (NumPy/SciPy) for simulation:

```powershell
.\.venv-scrapling\Scripts\python.exe -m etl.fetch_soccer_events
py -3 -m etl.soccer_event_dataset
py -3 -m models.run_soccer_simulation --runs 1000 --demo-runs 10000 --player-runs 250 --resume
py -3 -m models.evaluate_soccer_players --runs 100
py -3 -m scripts.simulate_soccer_fixtures --model data/raw/historical/soccer_events/20261022/simulation-baseline/England-model.json.gz --fixtures data/raw/historical/soccer_events/20261022/simulation-baseline/example-fixtures.json --output data/raw/historical/soccer_events/20261022/simulation-baseline/custom-forecast.json --runs 10000 --player-runs 250
```

Fixture JSON contains `fixture_id`, `kickoff`, `home_team_id`, `away_team_id` and
optional home/away `lineups` with `team_id`, eleven `starters`, `bench`, and player
ID-to-`roles` maps. IDs must be native Wyscout IDs; both teams need event history
in the selected competition model. Naive kickoff inputs are interpreted as UTC.
No automatic current-fixture resolution or live lineup ingestion is implemented.

Data/models/HTML remain local and ignored under
`pipeline/data/raw/historical/soccer_events/20261022/`. Key files:

- `manifest.json`: original captured assets and checksums.
- `normalized/index.json`: all match files, integrity results and quarantine.
- `simulation-baseline/report.json`: all seven team evaluation summaries.
- `simulation-baseline/player-report.json`: all seven player evaluation summaries.
- `simulation-baseline/player-evaluation/`: per-fixture player PMFs and validation.
- `simulation-baseline/demo.json`: example statistics, actor assignments and trace.
- `simulation-baseline/distributions.html`: standalone interactive distribution charts.
- `simulation-baseline/distributions.csv`: scoreline, goal-difference and total-goal PMFs.
- `simulation-baseline/convergence.json`: independent 50,000-run sampling comparison.
- `simulation-baseline/batch-verification.json`: actual batch-command output.

The source-evidence and completion-certification JSON files beside this report are
compact, reviewable records. The chart was exported successfully; browser visual
inspection could not run because the computer-use sandbox helper failed to start.

## Verification and limits

The targeted soccer and existing NFL play-by-play suites passed **26 tests and five
subtests**. Pyflakes reported zero errors. Saved-model replay, actual batch inference
and full source/dataset/split/artifact certification are recorded in the companion
evidence, along with final code hashes and runtime versions. Repository Fallow audit remains failing
with the same before/after summary: 374 dead-code issues, 59 complexity findings,
maximum cyclomatic 32 and three clone groups; missing JS dependencies degrade its
analysis. No clean repository-wide or full application CI result is claimed.

Before production use, add recent licensed event histories and timestamped roster
inputs, improve pace/count dispersion and player allocation, resolve interval/
identity gaps, support the required event/stat definitions and rules, and validate
on additional untouched seasons. Existing test results should remain a frozen
benchmark; do not tune on them and then call them unseen.
