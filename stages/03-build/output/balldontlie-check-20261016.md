# BALLDONTLIE access and NFL collection — 2026-10-16

Tested the user-supplied API key using the documented raw `Authorization` header. The key is configured as `BALLDONTLIE_API_KEY` in ignored local `pipeline/.env`; no credential is included in reports or source captures. The public environment template contains a placeholder only.

| Endpoint | Result |
|---|---|
| NFL historical games | HTTP 200 |
| NFL odds | HTTP 401 Unauthorized |
| NFL historical opening odds | HTTP 401 Unauthorized |
| NCAAF games | HTTP 401 Unauthorized |
| NCAAF odds | HTTP 401 Unauthorized |
| NCAAF historical opening odds | HTTP 401 Unauthorized |

All probe queries used the 2025 season, week 10, a documented period after the start of football odds coverage. Requests were spaced at 13-second intervals to remain below five per minute. The successful NFL request confirms that the key/header work; the denied endpoints are consistent with missing account-tier entitlements. The exact account subscription was not inspected.

## Successful NFL collection

Downloaded the complete accessible 2025 regular/postseason NFL schedule: **285 unique games**, across three cursor-paginated pages (100, 100, 85). The season parameter and unique provider IDs were validated. Every result matched the existing nflverse corpus by UTC game date and ordered franchise identities: **285 matches, zero score conflicts, zero unmatched games**. No duplicate observations were appended to the training dataset and no model was retrained.

Capture: `pipeline/data/raw/balldontlie/20261016T085856238161Z/`.

- `nfl-2025-games.csv`: normalized games, scores, team identities, status and timestamps.
- `nfl-2025-games.json`: complete game objects.
- `nfl-2025-page-{1,2,3}.json`: original paginated responses.
- `manifest.json`: pagination, source URLs, checksums and independent comparison.

Access evidence: `stages/03-build/output/balldontlie-access-20261016.json` and its raw capture directory. Collection evidence: `balldontlie-nfl-20261016.json`.

## What BALLDONTLIE could add with access

The [NFL documentation](https://nfl.balldontlie.io/) lists games on the free tier and betting odds on GOAT. The [NCAAF documentation](https://ncaaf.balldontlie.io/) lists games on ALL-STAR/GOAT and betting odds on GOAT. Paid subscriptions are scoped by sport unless using ALL-ACCESS.

Both sports document historical opening odds with an `opened_at` timestamp, limited to the most recently completed and ongoing seasons where available. General odds coverage is documented from NFL 2025 week 8 and NCAAF 2025 week 9. These are provider documentation claims, not successful paid-endpoint observations with this key. Opening timestamps would need validation against exact kickoff and native game identity before use in a point-in-time training dataset. The existing models and unverified archive-odds status are unchanged.

Reproduce the bounded checks and NFL season collection from workspace root:

```powershell
py -3 stages/03-build/output/probe-balldontlie-20261016.py
py -3 stages/03-build/output/collect-balldontlie-nfl-20261016.py
```

Both scripts create fresh capture directories; they do not purchase a subscription or start a paid trial.

## Follow-up: sportsbook-comparison article

Read the user-provided December 7, 2025 [sportsbook-comparison guide](https://www.balldontlie.io/blog/compare-sportsbook-odds/). It uses the NBA `/nba/v2/odds` endpoint and raw Authorization header. Direct tests with the configured key returned HTTP 401 Unauthorized for that exact path, the `/v2/odds` alias shown in the NBA reference, and `/nba/v2/odds/opening` with a historical date. Evidence: `balldontlie-nba-blog-check-20261016.json`.

The blog describes current odds and says historical odds are not stored. The newer [NBA API reference](https://docs.balldontlie.io/#get-opening-betting-odds) now documents limited historical opening snapshots and `opened_at`; it explicitly requires GOAT. Thus the article's older limitation is not a complete description of the newer API, while account-tier access still prevents retrieving either current NBA odds or historical opening snapshots with this key. No model data changed.
