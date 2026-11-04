# Betting intelligence implementation — 20 October 2026

## Plan and delivered scope

1. Inspect existing AI Picks, sport navigation, odds mathematics, source storage and candidate models. Baseline: large pre-existing dirty tree; Fallow summary fails on existing dead code, duplication and complexity, with incomplete root dependency resolution.
2. Add a shared Intelligence hub to AI Picks, with a summary per supported sport and dedicated sport tools. Delivered at `/ai-picks/intelligence`, `/ai-picks/intelligence/:sport`, and `/ai-picks/intelligence/:sport/:view`.
3. Publish a read-only intelligence contract from the pipeline; separate model estimates, de-vigged bookmaker probabilities, other-book consensus and theoretical arbitrage. Add a bounded snapshot refresh, integrate existing refresh entry points and repair player prop identity matching.
4. Verify calculations, source exclusions, API contracts, desktop/mobile navigation, errors and empty states. Record build, tests, live API evidence and remaining data limits below.

## Product behavior

AI Picks desktop/mobile menus now include Intelligence and NBA intelligence. The hub summarizes Football, NBA, NFL, WNBA, NCAAB and College Football. Each sport has AI picks, predictions, de-vigged odds, EV bets, player props and arbitrage views. Sport home pages and the existing Best Picks page link to their intelligence summary; sport Insights links preserve the selected sport.

NBA prediction models are explicitly experimental candidates, not promoted active models. Missing or stale prices do not become fabricated EV or arbitrage results. Prediction rows identify the model and timestamp. Market rows identify their probability basis, bookmaker, settlement contract and timestamp. Search, pagination, tool navigation, sport switching, retry and responsive tables are provided.

## Pipeline and API

- `api/betting_intel.py`: pure sport identity, complete-market de-vigging, EV and nominal arbitrage calculations. Reuses the shared implied probability and EV functions in `api/odds_math.py`.
- `etl/betting_intel.py`: reads active football predictions/quotes, explicitly linked backend events/offers/props and existing NBA/NCAAB/Odds API raw captures. Exact sport, home, away and kickoff duplicates are merged. Publishes `data/processed/betting_intel/snapshot.json` via atomic replacement. Database reads do not modify stored bets or active models. Up to 30 upcoming candidate previews per sport are generated offline, using checksum-validated existing candidate inference.
- `api/routers/betting_intel.py`: `GET /api/v1/betting-intel` and `GET /api/v1/betting-intel/{sport}`; optional exact competition filter. Unsupported sports return 404; missing/invalid snapshots return 503. Requests re-evaluate freshness and exclude games that have started. No mutation endpoint or model loading runs during a GET.
- Existing regional refresh and both daily batch entry points publish the snapshot. This adds refresh work to those entry points; it does not install another scheduler. The with-sync batch publishes again after backend synchronization so newly synced events can appear.
- `etl/ingest_player_props.py`: uses the provider's event-specific odds endpoint in decimal format, with bounded event collection. Matches both sides of the same player/market/line and provider timestamp. Writes only when league, home/away orientation and kickoff identify exactly one event; unmatched and ambiguous events are skipped. The previous arbitrary first-event association is removed. Repeated identical snapshots are not inserted again. Existing historical prop rows are not repaired or certified by this change.

Refresh from `pipeline/`:

```powershell
py -3 -m etl.betting_intel
```

Collect up to ten NBA event prop markets and then refresh, when the configured provider account has access and quota:

```powershell
py -3 -m etl.betting_intel --collect-props
```

Prop collection is explicit; routine snapshot publication does not spend new prop API quota. The provider contract was checked against its [official v4 documentation](https://the-odds-api.com/liveapi/guides/v4/#get-event-odds).

## Calculation and evidence policies

Only complete bookmaker markets with finite decimal odds above one are eligible. Quote timestamps must include a timezone, precede kickoff, be no more than 30 minutes old and not lie in the future. Opposing legs must be within two minutes; conflicting same-time prices invalidate a selection. Latest invalid prices never revive an older convenient quote.

Football uses all three regulation outcomes; two-way moneylines cannot be mistaken for complete football markets. NBA, WNBA and college leagues remain separate. Prop grouping includes event, market, participant and line. Integer prop lines and NFL tie-push markets have unmodeled push probability, so they do not produce EV or arbitrage claims. Their de-vig output is labeled conditional on no push. Zero/one probabilities, incompatible settlement, invalid probability sums and stale predictions are rejected.

EV uses an eligible model probability when available. Otherwise at least two other complete books form an equal-book de-vigged consensus, excluding the target bookmaker. These are gross estimates, not established profitability. Arbitrage uses the best complete-market legs, requires multiple books and bounded quote skew, and displays actual gross return `1 / reciprocal_sum - 1` with equal-payout allocations per 100 reference units. Acceptance, market terms, taxes, fees, limits and simultaneous execution remain unverified.

## Live coverage and limits

The live smoke snapshot included 37 upcoming NBA fixtures, 30 labeled candidate forecasts, and 17 eligible active football forecasts. NBA moneyline and prop prices were not fresh enough to populate price-based views. Other sport summaries were empty in the current seven-day source window. These counts describe available source coverage, not the complete real-world schedule. Source errors and stale snapshot status are surfaced separately from empty results.

No new player performance model was trained. Props display bookmaker quotes/probabilities and, where eligible, market consensus comparisons. No active model was promoted, no bets were placed and no production deployment was performed.

## Verification evidence

See `betting-intel-live-20261020.json` for live overview/six-sport endpoint, OpenAPI, unsupported-sport, probability and allocation checks. Unit tests cover de-vig/EV/ROI arithmetic, stale/future/incomplete/conflicting evidence, quote skew, sport scope, player/line matching, push markets, atomic publication and prop fixture association. Browser tests cover all NBA tools, sport switching, six summaries, search, failure/retry, mobile layout and invalid routes.

Final outcomes:

- `npm run build`: passed, including TypeScript and the production Vite build.
- Targeted ESLint: passed for the changed JavaScript integration and browser tests. TypeScript components are checked by the build; this repository's ESLint configuration does not lint TSX.
- `py -3 -m unittest discover -s tests -p test_betting_intel.py`: 24 passed.
- Existing `test_ai_picks.py`: five passed. Existing `test_regional_pipeline.py`: 16 passed, one database-gated test skipped.
- Targeted Python `compileall`: passed.
- Chromium `tests/betting-intel.spec.js`: seven passed, including all tools, six summaries, desktop/mobile navigation, filtering, sport isolation, recoverable errors and unsupported routes.
- Live API smoke: overview, all six sport endpoints, probability sums, arbitrage allocation checks, 404 behavior and OpenAPI passed after correcting a candidate's internal `basketball` identity to the outward-facing `nba` contract.
- A standalone browser check rendered the actual 30-forecast NBA snapshot on desktop and mobile. Screenshots: `betting-intel-desktop-20261020.png` and `betting-intel-mobile-20261020.png`; both were visually inspected. Run `npm run verify:intel:live` from `frontend/` with the isolated pipeline API listening on port 5567. It starts and closes its own Vite server on 5189 and does not belong to the automatic mock-based browser suite.
- Final Fallow audit remains failing in the broader pre-existing dirty tree, with incomplete root dependency resolution. After refactoring, no complexity finding points at the new intelligence TSX files; the audit is not a clean repository gate. New CSS uses the existing Heritage palette and responsive layout; the generic raw-value inventory is not itself evidence of a broken page.

The normal local pipeline endpoint at `http://127.0.0.1:5555/api/v1/betting-intel/nba` also returned HTTP 200 after implementation. Temporary verification services are stopped at handoff. Existing unrelated working-tree changes are preserved; no commit or deployment was made.
