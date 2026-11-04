# Supplied bookmaker feeds — 2026-10-14

Cloudbet, 1xBet, 22Bet Uganda and BetOnline public requests return HTTP 200 JSON
without browser cookies or session headers. Collectors are integrated into the
regional refresh and bookmaker grid. Cloudbet adds one source to the canonical
inventory, bringing it to 55. 22Bet now uses the verified Uganda offering.

Cloudbet and 1xBet each supplied nine valid upcoming UEFA Champions League
full-match 1X2 snapshots in capture `20261014T032835754917Z`. All 18 matched existing
fixtures by reviewed names and exact UTC kickoff. Import inserted 18; repeat
inserted zero. The live API initially showed six sources with nine fresh quotes
each: these two plus Betika, betPawa, Bovada and Fortebet.

The additional capture `20261014T035154613528Z` contains nine valid quotes each
from 22Bet and BetOnline. All 18 matched and imported; the repeat inserted zero.
Final live verification showed 55 catalog entries and eight sources supplying
nine fresh Champions League quotes each (72 quotes across nine fixtures).

Cloudbet requires enabled BACK selections in `soccer.match_odds`, `period=ft` and
not-started trading events. 1xBet and 22Bet require Champions League ID 118587,
main games and standard group 1, types 1/home, 2/draw, 3/away. Three Home/Away and
Special bets placeholders are excluded. 22Bet's supplied `topGamesByStat` route
returns five promoted games; the verified `games1x2` league route returns all
nine actual fixtures. Operator and regional identities remain separate.

BetOnline's public fixture POST requires the supplied soccer/uefa-cl/schedule body.
Using `utc-offset: 0` was verified to return UTC kickoff (16:45 and 19:00), whereas
the pasted `-180` header returned 19:45 and 22:00. Only parent Game-period
three-way moneylines with complete decimal prices are accepted; alternate child
markets are rejected. The adapter preserves the source's team names and prices.
Grid matching checks both orientations for BetOnline alone, requires a unique
exact team pair and UTC kickoff, and swaps team prices with the names. Regression
tests verify this alignment and reject ambiguity or a changed kickoff.

1xBet, 22Bet and BetOnline execution availability is UNKNOWN because their public
responses lack a positive execution flag. These are quoted prices, not a promise
that a wager is available. Coverage is restricted to these verified Champions
League routes and bounded request limits; later fixtures without prices remain
visible as missing.

Caesars returned HTTP 403 HTML anonymously and HTTP 202 AWS WAF challenge HTML
with the supplied token. No odds JSON was obtained. It remains in the grid with
no linked prices. Session headers were ephemeral and not stored in code.

Verification: nine supplied-feed adapter checks, six network adapter checks,
17 regional checks including PostgreSQL timezone regression, ten scraping checks,
two catalog/matching checks and nine dashboard checks. Four Chromium grid/live
pipeline checks and targeted ESLint passed after correcting test-file encoding.
Live counts and import evidence are saved in the adjacent JSON report.
