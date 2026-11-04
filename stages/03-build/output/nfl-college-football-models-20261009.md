# NFL and college football candidates — 2026-10-09

Two independently fitted, calibrated winner models are saved under candidate
`20261009T144354530070Z`. They are available through the existing candidate preview
API. They have not been promoted to the active production model.

| Model | Completed history | Held-out scored games | Accuracy | Fixed development-prior accuracy | Log loss | Prior log loss |
|---|---:|---:|---:|---:|---:|---:|
| NFL | 2,852 | 406 | 63.30% | 55.91% | 0.63906 | 0.68623 |
| College football, FBS participant | 9,026 | 1,357 | 75.68% | 66.84% | 0.49247 | 0.64005 |

NFL history contains ten final ties. These update team history and Elo but are
excluded from supervised winner fitting and winner accuracy. One tie falls in the
test period and is excluded from its 406 scored games. NFL previews explicitly
return `probability_basis: CONDITIONAL_ON_NO_FINAL_TIE` and
`settlement_rule: INCLUDING_OVERTIME_TIES_VOID`. These probabilities apply to a
two-way market only when a final tie voids the bet; they are not unconditional win
probabilities or a draw prediction. College finals include overtime and have two
decisive outcomes.

## Data and provenance

`pipeline/etl/fetch_americanfootball_history.py` collects regular/postseason NFL
results from public ESPN calendar-year scoreboards and college results from
SportsDataverse seasonal ESPN schedule releases, covering 2016–2026. Preseason,
All-Star, unfinished and future games are excluded. College scope requires at
least one FBS participant, retaining FBS versus FCS games for team history; it is
not a standalone FCS or lower-division model.

Capture directory:
`pipeline/data/raw/historical/americanfootball_leagues/20261009T143446697752Z/`.
Raw responses, normalized JSONL and a manifest retain source URLs, IDs, retrieval
times and SHA-256 checksums. All 22 seasonal source captures plus an independent
nflverse reference file were verified. The NFL cross-check found all 2,852
expected completed games through local game date 2026-10-06, with zero missing
ESPN IDs. The reference's untimestamped betting lines are not model inputs.

Historical result availability is conservatively estimated as UTC game day plus
two days, explicitly marked `CONSERVATIVE_TWO_DAYS`; it is not an observed historical
timestamp. Recent results whose estimated availability is still in the future are
excluded from the training corpus. NFL history ends 2026-10-06 UTC; college history
ends 2026-10-07 UTC. Franchise relocations and school renames follow stable ESPN
team IDs, retaining original source names alongside canonical current names.
Neither corpus had conflicting final scores requiring quarantine.

Primary source documentation:

- [SportsDataverse college schedule loader and schema](https://js.sportsdataverse.org/docs/cfb/reference/loaders#loadcfbschedule)
- [nflverse schedule data](https://nflreadr.nflverse.com/reference/load_schedules.html)
- [nflverse source schedule](https://github.com/nflverse/nfldata/blob/master/data/games.csv)

## Training and evaluation

Each model uses its own weights, score prior, rolling history and league-specific
Elo. The existing 20-column sport feature contract covers past scores, margins,
win rates, rest, recent schedule load and optional timestamped two-way moneylines.
Neutral-site games remove the Elo home-field adjustment during training and
prediction. No quarterback, injury, roster, recruiting, weather, spread or total
model is claimed.

Logistic regression regularization is selected on chronological tuning data,
refitted on train plus tune, then sigmoid-calibrated on a separate later partition.
Labels unavailable before the next partition are purged. Test data selects
neither hyperparameters nor calibration. Earlier held-out results can update team
history for later games once available, matching chronological inference.

| Model | Train | Tune | Calibration | Test period |
|---|---:|---:|---:|---|
| NFL | 1,735 | 413 | 283 | 2024-12-22 through 2026-10-06 |
| College | 5,514 | 1,257 | 888 | 2024-12-27 through 2026-10-07 |

NFL uses `C=0.01`; college uses `C=1.0`. NFL purged five boundary labels and college
purged ten. The full checksummed history stays in each saved dataset for causal
feature reconstruction; tied and purged games do not enter model fitting.

There is **no demonstrated bookmaker advantage**. All 63 matched NFL odds games
are in the test period, so a market expert could not be trained. On this subset,
model accuracy is 55.56% versus market 60.32%, and log loss is 0.67289 versus market
0.64631. College has zero exact, timestamped odds joins. Its short school names
also require an explicit provider/team-ID crosswalk before joining bookmaker
names such as school-plus-mascot names; fuzzy matches are not used. Both models
currently serve the calibrated history expert even when preview odds are supplied.
Prospective timestamped price capture and settled paper evaluation remain needed.

## Usage

Run from `pipeline/`:

```powershell
py -3 -m etl.fetch_americanfootball_history
py -3 -m models.train_sports --sports nfl ncaaf
py -3 -m models.sport_predict --candidate-id 20261009T144354530070Z --sport nfl --league americanfootball_nfl --home "Kansas City Chiefs" --away "Buffalo Bills" --kickoff 2026-10-20T00:00:00Z
py -3 -m models.sport_predict --candidate-id 20261009T144354530070Z --sport ncaaf --league americanfootball_ncaaf --home "Alabama" --away "Georgia" --kickoff 2026-10-20T00:00:00Z --neutral-site
```

Preview requests use `POST /api/v1/sport-models/preview`:

```json
{
  "candidate_id": "20261009T144354530070Z",
  "sport": "nfl",
  "league": "americanfootball_nfl",
  "home_team": "Kansas City Chiefs",
  "away_team": "Buffalo Bills",
  "kickoff": "2026-10-20T00:00:00Z",
  "neutral_site": false
}
```

For college, use `sport: ncaaf`, `league: americanfootball_ncaaf` and the source's
school names, such as `Alabama` and `Georgia`. Examples are hypothetical matchup
previews, not claims of scheduled fixtures. Kickoff must be timezone-aware and
later than model training. Unknown teams and mismatched leagues return HTTP 422.
`GET /api/v1/sport-models` lists these candidates.

## Verification

- All **68** pipeline behavioral tests passed, including actual fit/calibration/
  persistence with NFL ties, league isolation, neutral-site input parsing, causal
  history replay, label purging, coverage checks and checksum enforcement.
- Saved artifact checksums passed; recomputed held-out accuracy, log loss and Brier
  scores reproduced both stored reports to numerical precision. Evidence is in
  the candidate's `verification.json`; seasonal test metrics are also recorded.
- Isolated live API: NFL and college previews HTTP 200 with probabilities summing
  to one; cross-league and unknown-team requests HTTP 422. Test server stopped.
- Python compilation and `git diff --check` passed.
- Fallow 3.32.0 before/after audits passed their new-findings gate: one inherited
  dead-code finding, ten inherited complexity findings and one inherited clone
  group, with no newly introduced findings. An unpinned post-check fetched 3.33.0
  and failed on two frontend complexity attributions; rerunning the baseline
  version passed. No frontend files changed in this task. Missing dependency/
  boundary configuration limits remain. Fallow does not analyze Python; training,
  behavior tests and live checks provide that evidence.
- Generated raw data and candidate binaries remain ignored by Git; pre-existing
  workspace edits were preserved.

Repeat saved-model verification:

```powershell
py -3 -m scripts.verify_sport_models --candidate-id 20261009T144354530070Z --sports nfl ncaaf --capture-dir data/raw/historical/americanfootball_leagues/20261009T143446697752Z
py -3 -m scripts.smoke_sport_models --candidate-id 20261009T144354530070Z --americanfootball-leagues
py -3 -m unittest discover -s tests -v
```
