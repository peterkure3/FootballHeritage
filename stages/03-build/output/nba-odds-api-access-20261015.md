# NBA historical Odds API access — 2026-10-15

Attempted one authenticated historical NBA moneyline request using the existing `THE_ODDS_API_KEY`, without displaying the credential.

- Endpoint: `GET https://api.the-odds-api.com/v4/historical/sports/basketball_nba/odds`
- Snapshot requested: `2024-01-15T18:00:00Z`
- Parameters: `regions=us`, `markets=h2h`, `oddsFormat=decimal`.
- HTTP status: 401.
- Provider error: `HISTORICAL_UNAVAILABLE_ON_FREE_USAGE_PLAN`.
- Provider message: historical odds are only available on paid usage plans.
- Quota headers: `x-requests-used=500`, `x-requests-remaining=0`, `x-requests-last=0`.
- No historical odds returned; no credits consumed by this probe. No model retraining or activation performed.

The provider documents historical featured-market snapshots from June 2020 and a cost of 10 credits per region per market. Source: https://the-odds-api.com/historical-odds-data/ . One region and moneyline only minimizes each successful request to 10 credits. Historical collection must span the existing chronological train, tune, calibration and test periods; at least 30 covered observations and both outcome classes are required in each development/calibration partition by the current trainer.

The existing `pipeline/etl/fetch_historical_nba_odds.py` uses the live `/v4/sports/.../odds` route with date filters, so it cannot retrieve historical snapshots. Do not run it as a historical backfill. Correct collection must use `/v4/historical/sports/.../odds`, preserve the provider's returned snapshot timestamp as the historical observation time, and retain today's retrieval time separately. Many existing historical results have day precision; validate exact kickoff and opponent identity before joining odds rather than weakening the current strict matching requirement.

To resume: enable a paid Odds API plan with available credits, or configure an existing paid key as `THE_ODDS_API_KEY` in local `pipeline/.env`. Do not paste credentials into chat. Then verify access, collect a bounded NBA-only historical moneyline sample across chronological partitions, validate joins and coverage, and retrain/evaluate a new candidate. Current NBA candidate `20261015T163645187197Z` remains available.
