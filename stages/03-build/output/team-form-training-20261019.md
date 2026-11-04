# Football form collection and candidate — 19 October 2026

## Delivered

- Added `pipeline/etl/fetch_football_form.py`: configured football-data.org collection across PL, CL, PPL, DED, BL1, PD, SA, FL1, ELC and BSA; raw captures, checksums, dated results and oldest-to-newest last-five sequences. Rejects unfinished/future results and extra-time/penalty scores without regulation-time scores. Same-day results are conservatively excluded from form, matching the existing model contract.
- Collected 1,204 completed results. Imported validated history into `pipeline/data/raw/historical/team_form_20261019.csv`; existing training and serving history loaders consume it. Existing form features already include last-five W/D/L and weighted recent points/goals; no incompatible feature schema was introduced.
- Exported all 106 upcoming fixtures returned by the ten competitions for the seven days following collection (19–26 October). 96 have five provider-covered results for each team. These are not claimed to be all fixtures offered globally by betPawa, nor complete all-competition histories.
- Created `pipeline/models/model_store/candidates/team_form_20261019/` with 11,235 deduplicated completed fixtures (previously 10,144). New results influence current history and chronological evaluation; recent held-out labels are deliberately not fitted as training labels. Model selection, development fitting and calibration remain chronologically separated from testing.
- Test: 1,847 matches, accuracy 0.4899837574, log loss 1.0217290041. These metrics are not evidence of improvement over another model on a different test set. Active model was not replaced.
- `upcoming-team-form-20261019.md` lists every collected upcoming fixture. Companion JSON contains dated contributing matches and 96 history-only candidate previews; ten incomplete-form previews are withheld. Odds are not supplied to these previews.

## Coverage limitations and source checks

PSV matches the supplied W–L–W–L–L. Porto's collected sequence is L–W–W–W–L: Manchester City (8 September, 0–2), Casa Pia (12 September, 4–1), Benfica (20 September, 3–1), Marítimo (10 October, 2–1), Real Betis (14 October, 2–3). The user-reported W–W–W–W–L remains an unverified observation and was not forced into training data. Cup/other-league omissions remain possible.

Incomplete teams: Sabah, Fenerbahçe, Slavia Praha, AEK, Slovan Bratislava, Bodø/Glimt, Galatasaray, Shakhtar Donetsk, Club Brugge, Viking and LASK. Ten affected fixtures because Fenerbahçe–Slavia includes two incomplete teams. Team-specific provider requests returned only two CL games for each; Porto returned ten matches from CL/PPL. Evidence: `pipeline/data/raw/team_form/20261019/team_probe.json` and `team_*.json`.

Scrapling verified betPawa senior event 37637794, Sportradar event 74165946, kickoff 20 October 19:00 UTC. Widget scripts and licensing loaded in hidden Chromium but no result/form feed was returned. Youth fixture 38212826 was kept separate. Public ESPN fallback collection stopped at a 403 robots-policy response; no denied endpoints were scraped. Raw betPawa fixture and widget-request evidence is retained with the provider captures. Temporary downloaded JS was removed.

## Verification

- 3 new form tests and 17 existing model-pipeline tests passed. Covers W/D/L order, away orientation, missing history, future/same-day exclusion, final regulation scores, and existing leakage/identity gates.
- Saved model reloaded; accuracy/log loss/Brier reproduced from its dataset and chronological test partition. All 96 preview form win/loss counts matched actual model vectors; probabilities finite and sum to one.
- `pyflakes` unavailable in the installed Python environment. Compilation check used instead.
- Fallow baseline: 20 unused files, 41 unused exports, one unresolved import, one duplicate export; 44 clone groups / 5.7% duplication; 173 complexity findings. Missing root node_modules limits JS dependency conclusions; Fallow does not validate this Python data path.
- Final Fallow audit completed with a failing repository gate: three dead-code issues, 52 complexity findings and three clone groups across the existing changed-file scope. These repository findings were not repaired as part of the form-data task. Artifact: `team-form-fallow-after-20261019.json`. Python compilation passed.

## Reuse

From `pipeline/`:

```powershell
py -3 -m etl.fetch_football_form --import-history
py -3 -m models.train_model_v2
```

Use a new capture directory for a fresh collection. Default output directory is timestamped. Explicit existing directories resume cached responses; source capture timestamps/checksums reveal their age. Current capture and candidate are local ignored data/model artifacts. No automatic schedule or active-model promotion was added.

Remaining work for complete overall form: obtain permitted domestic/cup result coverage for the missing competitions and resolve Porto's differing sequence before claiming full betPawa parity.
