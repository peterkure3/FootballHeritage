# Bookmaker network inspection — 14 October 2026

Inspecting the browser's public network requests found working feeds that the earlier landing-page collector missed. Betika Uganda and Fortebet Uganda are now integrated into the bookmaker grid. The live API returned 36 fresh Champions League quotes: four bookmakers across nine fixtures, up from two bookmakers before this run.

## Inspection scope and evidence

All 47 resolved URLs in the 54-bookmaker inventory were loaded in isolated anonymous Chromium contexts. Seven entries still have no verified operator URL. This was a default-page inspection, not a claim that every site's Champions League page was fully explored. Absence of a captured price response does not establish absence of fixtures on the site.

| Browser result | Count |
| --- | ---: |
| Page inspected | 37 |
| Access challenge | 8 |
| Region restricted | 1 |
| Navigation failed | 1 |
| Operator source verification pending | 7 |

The initial discovery curl pass selected 35 public requests across 18 source IDs; 26 returned JSON. Some responses are configuration, translations or casino metadata rather than usable football prices. Those were not ingested. Useful candidate endpoints were observed for Mozzart, Odibets, Bangbet and World Sports Betting, among others; they require market/schema verification and, where necessary, targeted football navigation before integration. The Premier Bet landing URL loaded an SBA Uganda feed, so that operator identity needs review before attributing its prices to Premier Bet.

The complete source URLs, final destinations, response schemas and curl results are in [the JSON audit](bookmaker-network-discovery-20261014.json). Browser captures are in:

- `pipeline/data/raw/sportsbooks/network_20261013_browser/`
- `pipeline/data/raw/sportsbooks/network_20261013_remaining/`

The browser-control tool failed during sandbox startup. An isolated Playwright capture helper provided request/response inspection instead. The first helper stalled on an unbounded browser wait; completed captures were preserved, and the remaining batch ran with bounded screenshot and response waits. Both browser helpers have exited.

## Implemented feeds

| Source | Verified public request | Validated snapshots | Linked quotes |
| --- | --- | ---: | ---: |
| Betika Uganda | GET `https://api-ug.betika.com/v1/uo/matches` | 1,375 | 18: nine EPL and nine CL |
| Fortebet Uganda | GET `https://www.fortebet.ug/api/web/v1/offer/full-prematch-en` | 624 | 18: nine EPL and nine CL |

Betika's homepage requests today's highlights. The observed response metadata publishes an All-date filter (`period_id=9`) and start-time sort (`sort_id=2`). The collector uses those filters, soccer ID 3, standard 1X2 subtype 1, and validated pagination. Original page responses are retained alongside the combined dataset. Its published client configuration declares `dbTimezone: Africa/Accra`; naive fixture timestamps are therefore UTC, while the user interface uses Africa/Kampala. Exact canonical kickoff matching confirmed that interpretation.

Fortebet's current browser request is a GET prematch feed, rather than the older POST `full_offer` route. Its published market definition identifies Full Time Result, 3WAY, with ordered 1/X/2 outcomes. The UEFA tournament mapping additionally checks tournament ID TO7 and category International Clubs; other similarly named Champions League tournaments are not relabeled as UEFA. Source URL provenance is passed explicitly, preserving normalization of older captures.

Betika rejects simulated and other sports, started/live games, nonstandard markets, incomplete or duplicate selections, mismatched participant identities and prices, and suspended offers. Since its feed lacks an explicit execution-availability flag, normalized offers remain UNKNOWN rather than claiming they are open for execution. The grid's existing freshness and complete-market rules still apply.

The verified collector capture is `pipeline/data/raw/sportsbooks/20261013T202937840101Z/`. Thirty-six exact competition/team/kickoff matches were inserted; a second import inserted zero rows. Reviewed Champions League name mappings handle the abbreviations in these feeds without changing captured source names, model features, or the exact-kickoff requirement. The existing periodic regional target list now includes Betika and the corrected Fortebet route.

## Reproducible curl examples

Run these from PowerShell. The Betika example fetches page one; the production collector follows the reported total through all pages, with a five-page cap and duplicate/completeness checks.

```powershell
curl.exe --get 'https://api-ug.betika.com/v1/uo/matches' `
  --data-urlencode 'page=1' --data-urlencode 'limit=1000' `
  --data-urlencode 'sport_id=3' --data-urlencode 'sub_type_id=1' `
  --data-urlencode 'period_id=9' --data-urlencode 'sort_id=2' `
  --data-urlencode 'esports=false' `
  --header 'Accept: application/json' `
  --header 'Origin: https://www.betika.com' `
  --max-time 20

curl.exe --ssl-revoke-best-effort `
  'https://www.fortebet.ug/api/web/v1/offer/full-prematch-en' `
  --header 'Accept: application/json' `
  --header 'Referer: https://www.fortebet.ug/' `
  --max-time 20
```

The Fortebet flag addresses this machine's observed Schannel `CRYPT_E_REVOCATION_OFFLINE` error. Certificate and hostname verification remain enabled. The replay helper retries once with that flag only for this specific offline-revocation error; it does not retry denied access. The final immutable replay returned four successful JSON responses across Betika and Fortebet with no browser cookies or authorization headers.

Reusable tools:

- `frontend/scripts/capture-bookmaker-network.mjs`: bounded anonymous browser request capture with private fields redacted.
- `pipeline/scripts/replay_bookmaker_network.py`: credential-free curl replay of selected public requests, skipping account/order/authentication routes. New replay outputs have separate run directories. Earlier diagnostic response filenames were reused; the audit uses the latest diagnostic results, and original browser and production collector captures remain intact.
- `pipeline/scripts/audit_bookmaker_network.py`: combine disjoint inspection batches into a reviewable per-source audit.

## Verification

- 44 focused Python checks passed, including adapter rejection behavior, UTC timestamps, complete pagination, replay eligibility and rollback-only database checks.
- Four Chromium grid checks passed, including real API data, all 54 inventory columns, paging/filtering, missing/stale prices and mobile overflow.
- Capture helper ESLint passed; changed Python modules compiled successfully.
- Live API: 54 catalog entries; nine CL fixtures have 36 fresh quotes from `betika:UG`, `betpawa:UG`, `bovada`, and `fortebet:UG`.
- Models, prospective trial policy, and bet placement were not changed. No provider credits were needed for these new feeds. Remaining sources need further operator/market verification, parsers, or accessible integrations; full price coverage for all 54 bookmakers is still incomplete.
