# League models and bookmaker grid — 25 October 2026

La Liga is displayed by name while preserving the official `Primera Division` database key. The menu currently exposes ten competitions. Upcoming leagues remain selectable; competitions with at least 100 stored completed results also remain selectable between fixture refreshes. This menu threshold is not a model-quality certification.

## Training and predictions

Eight additional domestic models were trained independently on **20,211 completed matches**. Premier League and Champions League retain their existing shared-model path. The new models use 27 history features, with no historical bookmaker prices: archive prices lack verified observation timestamps.

Each league has separate chronological training, tuning, calibration and test periods, blocked by match day. Three logistic candidates and a histogram gradient model compete on tuning log loss; the winner is refitted on train+tune and sigmoid-calibrated on a separate period. Test labels are reserved for final evaluation. Saved model replay reproduced the held-out probabilities. Model, dataset and identity dictionary checksums accompany the artifacts.

| League | History matches | Test matches | Test accuracy | Model log loss | Prior baseline log loss | Upcoming forecasts at HTTP verification |
|---|---:|---:|---:|---:|---:|---:|
| La Liga | 2,754 | 379 | 52.77% | 0.9813 | 1.0522 | 23 |
| Bundesliga | 2,203 | 331 | 49.85% | 1.0085 | 1.0658 | 18 |
| Serie A | 2,735 | 380 | 55.53% | 0.9836 | 1.0740 | 31 |
| Ligue 1 | 2,421 | 346 | 49.71% | 1.0702 | 1.0758 | 19 |
| Primeira Liga | 1,305 | 212 | 51.42% | 1.0084 | 1.0884 | 22 |
| Eredivisie | 1,317 | 200 | 53.50% | 0.9981 | 1.0893 | 19 |
| Championship | 1,813 | 267 | 40.45% | 1.1148 | 1.0933 | 36 |
| Brazilian Série A | 5,663 | 753 | 50.86% | 1.0130 | 1.0468 | 22 |

The baseline uses outcome frequencies from train+tune, with Laplace smoothing. **Championship underperformed this baseline on held-out log loss.** These are evaluated candidates, not evidence of a bookmaker advantage. Their API records have `active: false`, distinct league model versions and `model_kind: evaluated_league_candidate`; the UI identifies them accordingly and exposes the evaluation sample and feature cutoff. No global active model artifact was replaced by this implementation.

The published snapshot contains **191 pre-match forecasts**, with no missing-team exclusions. At 17:04 UTC, HTTP verification returned **190 still-upcoming fixtures**, all with their league forecasts; one Serie A fixture had started since generation and was correctly excluded. Probabilities and the grid's gross EV arithmetic were independently checked through the authenticated API. La Liga returned 23 forecasts, with fresh linked prices for 13 fixtures.

The serving registry advanced to run `20261025T165351114106Z` during verification. The HTTP audit follows that registered run and checks snapshot consistency. Earlier isolated runs remain available for audit. Forecasts are atomically published to `pipeline/data/processed/league_predictions.json`; model artifacts are under `pipeline/models/model_store/league_models/`.

## Data refresh and source limits

- Refreshed ten official competitions: 1,183 eligible completed results imported into a dated history CSV, and 239 official upcoming fixtures upserted into the serving database. Started fixtures subsequently age out of the upcoming feed.
- Collected all 46 configured sportsbook targets. The audited full run captured 745 normalized snapshots: seven source parsers produced records; 20 responses still need adapters, six brands lack a verified source URL, five were blocked by robots policy, four failed to connect, two denied access and two supplied no complete upcoming 1X2 markets.
- The paid odds fallback returned HTTP 401, `OUT_OF_USAGE_CREDITS`, with zero remaining quota. No replacement prices were invented.
- Imported 146 audited source observations and 134 expanded betPawa observations; an identical repeat inserted zero. The final working-source refresh captured 216 snapshots and imported 179 more observations from betPawa, SportPesa, Cloudbet, 1xBet and 22Bet. Its earlier preview matched 180; one fixture started before application and was correctly excluded.
- HTTP Date/Age/Last-Modified evidence is retained. Stale cached Bovada and Bookmaker responses from the full run were excluded. The same exclusions now protect the secondary EPL import and frozen-trial continuation paths.
- Competition matching is country-scoped, with reviewed domestic team aliases, unique team-pair identity and exact UTC kickoff requirements. The source's original team names remain in the raw capture.
- Added Championship and Brazilian archives and an older Dutch season. Portugal's older archive requests repeatedly timed out and the official account denied the older season. Its extra 306-game season came from [OpenFootball's published 2022/23 Portuguese dataset](https://github.com/openfootball/football.json/blob/master/2022-23/pt.1.json), with explicit source-name mapping, regulation-score validation and a retained checksum. The 1,000-game model minimum was preserved.

Raw captures and manifests are retained under `pipeline/data/raw/sportsbooks/`, `team_form/leagues_20261025` and `league_training/`. Repeated snapshots from different observation times are retained as separate observations. This is not complete extraction from every sportsbook: blocked sources, unverified brands and missing adapters remain explicit limitations.

## Pipeline and verification

Daily collection now tracks the additional leagues with provider request spacing. The regional refresh uses the complete configured sportsbook inventory through Scrapling, then refreshes forecasts from the registered league artifacts. Weekly retraining now trains the additional domestic models and publishes their forecasts. No scheduler registrations were changed.

From `pipeline/`, retrain with `py -3 -u -m models.train_football_leagues --publish --threads 2`, or refresh forecasts with `py -3 -m models.predict_football_leagues --publish`. Model preparation requires the existing historical captures; missing history or incomplete forecast coverage fails publication rather than substituting invented inputs.

Verification includes 67 targeted Python tests, rollback-only PostgreSQL integration, artifact replay, seven Chromium checks including the authenticated live La Liga feed, ESLint, TypeScript/Vite production build, Python compilation and whitespace checks. The live browser proxy explicitly emits UTF-8 and rejects replacement characters. Pyflakes was unavailable in both installed Python environments. Final Fallow reports no dead-code or duplicate-group findings for the audited changes and two remaining complexity findings: the pre-existing prediction-test API mock and an unrelated preflight helper already present in the workspace. Introduced provenance-component findings were resolved.

Evidence: `league-models-verification-20261025.json`, `league-grid-api-final-20261025.json`, `league-predictions-20261025.csv`, `league-grid-live-20261025.png`, `league-grid-probabilities-20261025.png`, and `league-models-fallow-20261025.json`.

Application changes and model artifacts were verified locally. No hosted deployment was performed.
