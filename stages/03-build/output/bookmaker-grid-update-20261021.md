# Bookmaker grid data repair — 21 October 2026

The grid now links collected Champions League prices for the previously empty Inter, Bayern and Club Brugge fixtures, and restores missing Sporting/Viking offers. The live verification found stored quotes from 6–10 bookmakers for each of tonight's seven fixtures. The remaining upcoming feed returned 20 fixtures, 18 with linked prices, and all 46 requested source columns.

## Changes

- Added explicit UCL ingestion aliases for Inter/Inter Milano, Bayern Munich, Club Brugge, Lens, Sporting and Viking. Competition, unique team pair and exact UTC kickoff matching remain mandatory; frozen model feature keys and source names are unchanged.
- Grid synchronization now reads the dataset declared by a normalization manifest. Expanded captures previously stored usable observations in `odds_snapshots_complete.jsonl` while synchronization read the empty/original `odds_snapshots.jsonl`.
- Captures with HTTP cache evidence reject unavailable sources, upstream cache age over 120 seconds, and Bookmaker pages older than the conservative 300-second Last-Modified rule. The latter is a page timestamp, not proof of individual quote age.
- Added a decimal-odds comparison view alongside probabilities and gross EV. Populated requested sources appear first, and each source reports fresh fixture coverage. All requested columns and the existing stale/missing states remain; deliberately removed sources are not reintroduced through old quotes. EV copy explicitly states that tax and fees are excluded.

## Live data

Scrapling capture `pipeline/data/raw/ucl_revision_20261021T184219Z` supplied 29 new rows: 22 betPawa and seven Cloudbet, covering 16 Premier League and 13 UCL source/fixture pairs at the time of import. One additional betPawa spelling (`Inter Milano`) was discovered and repaired afterwards. An archived exact-match replay of that capture now links all seven UCL fixtures for both sources. The subsequent periodic collector also used the repaired matching; all seven fixtures have newly refreshed quotes in the DB.

Ababet refresh attempts failed, so no new Ababet observations were invented. Bovada and Bookmaker observations rejected by cache checks were not imported from this audited capture. Other existing stored quotes retain their recorded times and the dashboard's existing 24-hour display policy; stored source counts are not claims of simultaneous executable offers.

Repeated application inserted zero duplicates. When the final repeat ran after the 19:00 UTC kickoff, UCL fixtures were correctly excluded from new pre-match ingestion. The read-only API/DB verification at 19:09 UTC confirmed all seven fixtures had stored bookmaker prices and that the upcoming API excluded started fixtures. No in-play prices were substituted into pre-match markets.

## Verification

- Five Python catalog, identity, normalization-file and HTTP-cache tests passed.
- Nine supplied bookmaker adapter tests passed, including reversed home/away matching.
- Four Chromium tests passed covering decimal prices, market probabilities, EV, stale quote/model suppression, source coverage ordering, all requested columns, paging and mobile overflow. The first expanded catalog check caught a removed-source regression during development; the final implementation preserves the requested inventory and all four checks pass together.
- Targeted ESLint and the production TypeScript/Vite build passed.
- Fallow repository summary and post-change audit ran. Repository-wide checks remain failing with existing unresolved imports, duplicate groups and complexity issues; root dependency resolution is degraded because no root node_modules exists. New small grid helpers were simplified after the audit flagged estimated coverage/complexity risk.

Live evidence: `bookmaker-grid-update-live-20261021.json`. Source responses, normalization reports and individual sync reports remain in the capture directory. No model was retrained or promoted, no predictions were overwritten, and no bets were placed.
