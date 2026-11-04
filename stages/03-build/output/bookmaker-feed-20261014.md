# BookMaker Champions League feed — 2026-10-14

BookMaker's supplied page returned HTTP 200 HTML without browser cookies:
`https://lines.bookmaker.eu/en/sports/soccer/uefa-champions-league/`.
The page includes 18 fixture groups: nine past, suspended games and nine upcoming
games with open three-way moneylines. Only the nine upcoming complete markets
are collected. The canonical source inventory remains at 45; BookMaker was
already a member and is now a verified collector in the regional refresh.

The adapter verifies the canonical route, league heading, table caption and
Moneyline column. It rejects live/started fixtures, suspended/missing prices,
unverified links, missing draws and changed schemas. American odds are converted
to decimal prices; movement arrows and opening prices are ignored. The provider's
JSON-LD dateModified is preserved separately from request observation time.
The grid stores the published update time for BookMaker, so polling a cached
page cannot repeatedly make unchanged prices appear newly updated.

BookMaker's official [three-way soccer moneyline rules](https://get.bookmaker.help/hc/en-us/articles/360032287791-Soccer-3-way-moneyline-betting)
confirm regulation time plus injury time. The page's team order may be opposite
the fixture order; BookMaker and BetOnline alone allow reversed-pair matching
with exact UTC kickoff, unique fixture identity and prices swapped with the named
teams. Other sources retain their original orientation requirements.

Capture: `pipeline/data/raw/sportsbooks/20261014T045414934872Z`.
All nine quotes matched and imported. Repeating the import inserted zero.
The live API verified nine fresh BookMaker quotes and correct LASK/Liverpool
price alignment: LASK 9.09, draw 6.34, Liverpool approximately 1.295.
Nine sources now supply nine fresh Champions League quotes each (81 total).

Verification: 25 focused Python checks passed (BookMaker HTML 4, supplied feeds 9,
scraping 10, catalog/matching 2), Python compilation passed, and the real-pipeline
Chromium check passed. API quote and import evidence is in `bookmaker-feed-20261014.json`.
