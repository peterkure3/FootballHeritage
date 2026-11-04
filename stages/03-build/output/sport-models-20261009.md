# Separate sport prediction models

Built and trained isolated **football and basketball winner candidates**. Added
sport data adapters, causal feature profiles and readiness gates for American
football, baseball and hockey. Existing active prediction models remain unchanged.

Candidate run: `20261009T100528981075Z`, stored under
`pipeline/models/model_store/candidates/sports/`. Each trained sport has its own
frozen dataset, model artifact, schema, calibration and evaluation report.

| Sport | Completed games available | Outcome | Result |
|---|---:|---|---|
| Football | 10,107 | Home/draw/away, regulation time | Trained; 50.08% accuracy, log loss 1.0086 on 1,260 retrospective test fixtures |
| Basketball | 8,586 | Home/away, final score including overtime | Trained; NBA previews available |
| American football | 163 | Final score including ties | Adapter implemented; below 500-game minimum |
| Baseball | 265 | Home/away, final score including extra innings | Adapter implemented; below 500-game minimum |
| Ice hockey | 26 | Home/away, final score including overtime/shootout | Adapter implemented; below 500-game minimum |

The minimum is an engineering readiness gate, not evidence of predictive quality.
All chronological partitions must also have at least 30 games and every target
class. American football's three-way target requires tie observations in each
partition; its two-way bookmaker prices are not treated as equivalent markets.
Additional historical results and timestamped odds are needed for those sports.

## Basketball evidence

Sources: six existing historical NBA season exports, explicitly completed NBA
score captures and NCAA men's score captures. After deduplication, there are
8,114 NBA and 472 NCAA games. One contradictory NBA fixture (Miami Heat–Chicago
Bulls on 2026-02-01 UTC) was quarantined entirely. Table-header records such as
`Playoffs` are excluded from historical exports. Baseball provider event IDs
preserve separate games in doubleheaders rather than conflating their scores.

- Development: 6,322 games; independent calibration: 710 games.
- Full test: 1,554 games, 2025-01-15 through 2026-06-09.
- Model: **61.52% accuracy**, **0.6468 log loss**, **0.4556 multiclass Brier score**.
- Fixed development-period class-frequency baseline: **54.25% accuracy**,
  **0.6904 log loss**, **0.4972 Brier score** on the same full test.
- NBA subset: **64.42% accuracy**, **0.6325 log loss**, 1,082 test games.
- NCAA subset: 54.87% accuracy, 0.6796 log loss, 472 games. NCAA exists only in the
  test period and is explicitly a transfer evaluation. It is **not a trained NCAA
  model** and NCAA previews are rejected until development data exists.
- No usable complete prematch moneyline joins. The market expert remains absent;
  this candidate uses history features. **No basketball advantage over bookmaker
  probabilities or profitable betting strategy has been established.**

These are retrospective evaluation results, not guaranteed future accuracy. NBA
history ends in June 2026 and lacks the current season's roster/injury information.
Future previews disclose the history cutoff. The candidate needs current data and
prospective validation before becoming an active prediction source.

## Feature and training design

- Football reuses its established calibrated odds-aware/history experts with its
  own 39-feature contract and three outcome classes.
- Other sports use separate sport-specific state, score scale, recent-game window
  and home advantage, with league-isolated team Elo, recent wins, scoring and
  conceded averages, margins, rest and recent game load. These first versions
  use final-score history; possession efficiency, player injuries, pitchers,
  quarterbacks and lineup features are not present in the local training data.
- Logistic regularization is selected on tuning games only. Development refitting
  uses train+tune; sigmoid calibration uses its separate period. Test results
  do not select parameters. An optional independent market expert requires
  sufficient observed-odds coverage in development and calibration.
- Results update history only when available and never within the same UTC game
  day. Day-only NBA historical results and legacy capture timestamps with unknown
  timezone use a conservative two-day availability delay. Explicit timezone
  captures preserve their time. Odds must be available before exact kickoff.
- Candidate previews use the same causal state logic as evaluation. Feature
  schemas, dataset checksums and basketball model checksums are checked on load.
  Unknown teams, untrained leagues, historical kickoff previews and invalid
  candidate identities are rejected. Missing odds route to the history expert.

## Commands and API

From `pipeline/`, rebuild all supported sport candidates without activation:

```powershell
py -3 -m models.train_sports
```

Select sports with `--sports basketball football`, or use `--output-dir` for a
new isolated run directory. Reports retain insufficient-data statuses for sports
that cannot train. Generated data and models are ignored by Git.

Preview the saved NBA candidate:

```powershell
py -3 -m models.sport_predict --candidate-id 20261009T100528981075Z --sport basketball --league basketball_nba --home "Boston Celtics" --away "Los Angeles Lakers" --kickoff 2026-10-15T00:00:00Z
```

API endpoints under `/api/v1`:

- `GET /sport-models`: candidate runs and readiness per sport.
- `POST /sport-models/preview`: explicit candidate preview. Request fields:
  `candidate_id`, `sport`, `league` (required for non-football), `home_team`,
  `away_team`, timezone-bearing `kickoff`, and optional decimal `home_odds`,
  `away_odds`, `draw_odds`. Returns named probabilities, winner, history cutoff,
  model version and `active: false`.

Live preview smoke check:

```powershell
py -3 scripts/smoke_sport_models.py --candidate-id 20261009T100528981075Z
```

This starts and stops an isolated API on localhost:5562. Verified NBA and football
HTTP 200 predictions with probabilities summing to one, American football HTTP
503 (insufficient data), and NCAA HTTP 422 (untrained league).

## Verification

51 behavioral tests passed, including future-score invariance, delayed and same-day
result isolation, league separation, doubleheader identities, conflicting scores,
timestamp uncertainty, persisted model reload and missing-market routing. Saved
NBA and football candidates were reloaded in fresh processes and previewed. Live
API checks passed. Python compilation and patch whitespace checks passed.
Fallow's repository audit is also checked; it does not analyze Python model
behavior, which is covered by the tests and actual training/prediction runs.
The root audit passed with no new findings; it retains a missing root
`node_modules` warning and inherited JavaScript findings.
