# Verified regional odds and prospective trial integration

Implemented and exercised on 10 October 2026. Three new Uganda adapters produce complete prematch football home/draw/away decimal prices. A subsequent user-requested retry located SportPesa's anonymous global EPL odds API in its published JavaScript and added that adapter. Its global page identifies `en-GLOBAL`, country `global`, EUR and GMT. The original server-rendered rows lacked prices; the verified JSON feed now supplies them. No Uganda SportPesa prices were invented or imported. Follow-up evidence: `sportpesa-adapter-20261010.md`.

| Source | Verified coverage | Latest EPL snapshots |
|---|---|---:|
| Bovada | Existing public soccer feed, regulation 1X2 | 18 |
| betPawa UG | Directory-resolved upcoming EPL, explicit `1X2 - FT` regular playing time | 19 |
| Fortebet UG | Public prematch full offer, football Full Time Result, documented 1/X/2 ordering | 19 |
| AbaBet UG | Selected-day EPL Match Result, local Africa/Kampala kickoff converted to UTC | 5 |

These counts describe the first four-book capture. The subsequent 13:50 UTC capture adds 19 SportPesa Global snapshots and contains 76 EPL snapshots overall (AbaBet then supplied only one fresh quote), with 46 exact database joins. The five upcoming EPL API fixtures now each have five bookmaker sources; quote timestamps remain visible.

The latest exercised capture is `pipeline/data/raw/sportsbooks/20261010T125646932268Z/`. Its 61 EPL snapshots were imported into checksum-protected Parquet storage. Of these, 38 matched database fixtures using reviewed club identities and exact UTC kickoffs within an eight-day window. Unmatched fixtures retain their original capture without guessed joins. Five upcoming EPL fixtures each have all four books in the real dashboard API. Raw football captures also contain other leagues; this integration deliberately imports only verified EPL records. Results are still required before new quotes can become labeled training examples. No candidate was retrained or promoted during this integration.

## Kickoff correction

The pipeline database session used Africa/Nairobi while destination columns were TIMESTAMP WITHOUT TIME ZONE. Loading timezone-aware pandas values through a temporary table cast UTC instants into local clock values, adding three hours. The loader now converts values to UTC before removing timezone information and both loader/API engines explicitly set their sessions to UTC.

Fifteen source-verified EPL fixtures between 10 and 17 October were repaired by exact source ID, teams and original three-hour discrepancy. The applied repair receipt is `regional-odds-sync-applied-20261010.json`. Subsequent reviewed aliases added 11 missing exact matches, documented in `regional-odds-sync-aliases-20261010.json`. The global team-feature mapping and frozen candidate feature keys were preserved. A replay of the 12:42 capture inserted zero quotes and repaired zero fixtures; see `regional-odds-idempotency-20261010.json`.

## Refresh and immutable trial

`scripts.refresh_regional_pipeline` collects public sources concurrently, saves raw captures, ingests exact-matched EPL quotes, imports training-ready snapshots and appends fresh pregame predictions from the existing active v2.0.0 model. Inputs require complete prices observed within 15 minutes before kickoff. Cycle receipts include prediction IDs, quote times/prices, feature cutoffs and active artifact SHA-256 checksums. Existing prediction records are retained by this refresh.

The original Bovada candidate trial is copied byte-for-byte into SHA-addressed storage. Its five pregame forecasts, four paper selections and one missing-history exclusion remain fixed. New fixture recordings require the same candidate artifact checksums and declared policy: one unit, one selection per fixture, at least 5% estimated EV after a 2% payout reduction. Already captured fixtures cannot be reselected. Regional prices remain separate from this primary trial.

Official football-data.org FINISHED/REGULAR results are matched by reviewed team identity and exact UTC kickoff. Completed trial reports retain result source captures and checksums separately from immutable forecasts. Pending trials from earlier dates are refreshed on subsequent runs, allowing the next day's daily job to settle yesterday's games. Provider errors preserve existing evidence. Duplicate/ambiguous results, wrong kickoffs and in-play scores cannot settle a selection.

At the initial live cycle, all five forecasts remained pending, with zero settled selections and null paper/stressed ROI. The subsequent SportPesa refresh obtained the first verified result: one losing paper selection (-1 unit), four forecasts still pending. Estimated EV is not demonstrated profit. The declared prospective cohort and independent profitability assessment still need to be completed; this implementation never marks an edge established automatically.

The Predictions page now includes **Paper trials**, served by `/api/v1/prediction-dashboard/paper-trials`, with selections, exclusions, quotes, estimated EV, settlement states and paper/stressed ROI. It displays Pending rather than zero ROI before results arrive.

## Running and verification

Both existing daily batch runners call the regional cycle after active prediction generation; the sync runner then copies data to the backend. This updates the existing workflow. No new Windows scheduled task was registered.

From `pipeline/`:

```powershell
py -3 -m scripts.refresh_regional_pipeline
py -3 -m scripts.refresh_paper_trial --match-date 2026-10-10
py -3 -m scripts.verify_regional_pipeline
$env:RUN_PREDICTION_DB_TESTS='1'
py -3 -m unittest discover -s tests -v
```

Live evidence: `regional-pipeline-live-verification-20261010.json`. Ignored detailed cycle receipts: `pipeline/data/processed/regional_audits/`. Visual evidence: `predictions-ui-paper-trial-20261010.png`.

All 103 Python regression tests passed with opt-in PostgreSQL checks enabled, including a real Africa/Nairobi-session loader regression using rollback-only temporary tables, quote/parser/settlement safeguards and past-date result recovery. Seven Chromium feature checks passed, including real API rendering. Frontend lint/typecheck/build passed; lint retains an existing AdminEvents hook warning. Fallow 3.32 passed with zero introduced findings after simplifying rendering; Python is outside its coverage and missing root node_modules limits dependency classification.

Operator/account execution prices, taxes, limits and payout costs are not verified by public quote collection. The fixed 2% reduction is a sensitivity scenario, not a verified Uganda tax assumption. Additional bookmaker adapters, league-specific historical prices and new untouched model validation remain further work.
