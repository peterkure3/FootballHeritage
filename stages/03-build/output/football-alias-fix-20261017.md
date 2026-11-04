# Football candidate name matching — 17 October 2026

Fixed reviewed provider variants for Brighton & Hove Albion, Sunderland and Hull City. New `models.football_identity` resolves them to the exact keys already stored in candidate history, while retaining an already-known original key. The global training normalizer and saved datasets/models were not changed. Existing Bournemouth settlement equivalence is preserved in the shared identity helper.

Candidate football inference now uses the resolved history keys for feature construction, preserves supplied names in responses, and rejects two aliases of the same club. Trial settlement and seen-fixture identity use the same reviewed aliases so provider and official result names match. Unknown teams and similar youth/women/other club names are still rejected; no fuzzy matching is used.

## Verification

- 36 focused Python tests passed; one opt-in database timezone test skipped. Covers aliases, real-history-key requirements, same-club rejection, exact-kickoff settlement, study integrity, manual-pick separation, regional collection and continuation.
- All eight formerly rejected fixture inputs forecast successfully and reproduce the canonical-name probabilities exactly.
- All 22 original successful forecasts reproduce their saved probabilities within 1e-12.
- Running :5555 API returned HTTP 200 for each repaired name through `/api/v1/sport-models/preview`.
- SHA-256 checks confirmed candidate artifacts and all original immutable trial files unchanged. No retrospective selections were imported.
- Python compilation passed. Fallow audit captured in `football-alias-fallow-20261017.json`; repository-wide findings remain and Fallow does not analyze Python.

Evidence: `football-alias-verification-20261017.json` and the read-only `verify-football-aliases-20261017.py` script.

## Remaining separate behavior

The study still has six settled and six pending selections. Existing excluded rows are immutable and the collector's first-observation lock still prevents their retry. This fix applies to new forecasts; changing retry/decision timing requires a separate change with explicit ledger handling. No EV thresholds, model artifacts or historical selection decisions changed.
