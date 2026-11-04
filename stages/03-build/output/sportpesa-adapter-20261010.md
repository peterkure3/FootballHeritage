# SportPesa retry: public global EPL odds verified

The user-provided football page loads successfully. Its HTML renders fixtures, while its published JavaScript requests anonymous JSON from `/api/upcoming/games`. The global page identifies country `global`, currency EUR and GMT. This is retained as **SportPesa Global**, not relabeled as Uganda.

The collector now requests `sportId=1`, `leagueId=70`, `markets_layout=single`, `page=1`. The live response returned HTTP 206 with `Content-Range: 0-18/19`: all 19 events in this filtered EPL response were captured. Range metadata is retained; future first-page responses must not be assumed to cover an entire larger schedule.

The public default-market definitions identify standard football market 10 as 1X2 with home/draw/away ordering. Published market help defines full time including injury/stoppage time; game rules distinguish standard 1X2 from early-payout markets. The parser excludes those early-payout variants, inconsistent kickoff encodings, mismatched team selections, suspended selections, non-EPL/non-football records and games already started. It retains provider event/team/selection IDs and UTC observation/kickoff timestamps. Execution availability remains unknown because the anonymous feed does not explicitly confirm it.

Live capture: `pipeline/data/raw/sportsbooks/20261010T135039623278Z/`. SportPesa contributed 19 valid EPL snapshots, of which 12 matched database fixtures by reviewed club identities and exact UTC kickoff. All 19 entered checksum-protected odds storage; pending games cannot receive fabricated training labels. This combined cycle captured 76 EPL snapshots across five books, matched 46 and refreshed five existing active-model predictions. AbaBet supplied only one fresh quote in this cycle; its other displayed quotes retain their earlier observation times.

The real API check confirms all five upcoming EPL fixtures have Bovada, betPawa UG, Fortebet UG, AbaBet UG and SportPesa Global quotes. Evidence: `regional-pipeline-live-verification-20261010.json`. Daily runners already use the updated collector. Inventories preserve the Uganda landing-page reference separately from the newly verified global feed.

During this refresh, the unchanged Bovada trial received its first verified final result: one losing paper selection, four forecasts still pending. This is one result, not evidence of model profitability; no model or trial policy changed.

All 105 Python regression tests passed with database checks enabled, including the two new SportPesa parser tests. No frontend code changes were needed for the additional bookmaker.

Primary operator references: [football page](https://www.sportpesa.com/en/sports-betting/football-1/), [public prematch API](https://www.sportpesa.com/api/upcoming/games?sportId=1&leagueId=70&markets_layout=single&page=1), [market definitions](https://www.sportpesa.com/api/default/markets), [standard 1X2 help](https://www.sportpesa.com/api/markets/help?sportId=1&marketId=10), [game rules](https://www.sportpesa.com/game_rules). Published client code, definitions, help and discovery responses are saved under `pipeline/data/raw/sportsbooks/sportpesa_retry/`.
