# ADR-004: Expected Goals (xG) Data Integration

## Status
Proposed

## Context
Discovery found that xG (Expected Goals) data improves soccer prediction accuracy (~1% gain per benchmark). Currently, the model uses form stats, ELO, H2H, and odds-derived features but lacks advanced metrics.

## Decision
Add Understat as a data source for soccer xG data. Integration approach:
1. **Understat scraper** — fetch per-match xG, xGA, xG per shot via Playwright XHR interception (same approach as EPL-betting benchmark project)
2. **Transform** — calculate rolling xG averages (last 5 matches) as new features
3. **Model update** — add rolling xG features to the existing 38-feature set (v2.1)
4. **Coverage** — Premier League primary, extend to La Liga/Serie A/Bundesliga as Understat data allows

## Consequences
- (+) Proven accuracy improvement in benchmarks
- (+) Rolling xG features are straightforward to add to existing feature engineering
- (-) Understat has no official API — scraping is fragile and may break
- (-) Only covers top European soccer leagues, not US sports
- (-) Playwright dependency for scraping adds deployment complexity
