# Additional bookmaker inventory and public-source check

All 34 brands requested on 10 October 2026 were added to the master inventory, which now contains 54 unique bookmaker IDs. Previous provider mappings are preserved. The additions are retained separately in `sportsbook-sources-africa-20261010.json`. No aggregator mappings were guessed for the additional brands.

Public-page research established 27 candidate collection URLs. A source URL identifies an operator-facing page, not a verified odds feed, current licensing, account availability, or regional football coverage. Where verified, regional variants are explicit: UG, KE, NG or ZA. Unknown regions remain null; international root sites must not be treated as Uganda offers. Notably, Mozzart's checked operator page is Nigeria's offering and SportyBet's root redirects to Nigeria. BetVita and Goalkings remain unresolved; similarly named prediction applications were not treated as bookmakers.

Primary examples supporting Uganda-facing source selection: [betPawa operator information](https://www.betpawa.ug/about), [SportPesa Uganda](https://ug.sportpesa.com/), [Betika Uganda](https://www.betika.com/en-ug/s/home.bet), [GSB operator help](https://help.gsb.ug/) and [AbaBet](https://ababet.ug/). Other checked operator URLs and verification references are retained in the machine-readable addition inventory.

The bounded anonymous collector run completed at 11:46:08 UTC. Capture: `pipeline/data/raw/sportsbooks/20261010T114545794136Z/`. It made one request per resolved source, using existing timeout and challenge handling, and skipped unresolved sources.

| Result | Brands |
|---|---|
| Public response; parser required (21) | betPawa, SportPesa, Mozzart Bet, Betway, 1xBet, 22Bet, Premier Bet, BetKing, NairaBET, Bangbet, Odibets, Supabets, World Sports Betting, SunBet, Bet.co.za, SportyBet, MegaPari, Paripesa, Fortebet, TopBet, AbaBet |
| Access denied (3) | Playabets (403), BetWinner (401), GSB (403) |
| Connection failed (3) | Betika (ConnectTimeout), Bet9ja (see raw report), AdmiralBet (SSLError) |
| Source verification pending; no collection request (7) | Hollywoodbets, Merrybet, BetLion, Easybet, Gbets, BetVita, Goalkings |

The seven unresolved rows are retained rather than silently dropped. Five have candidate domains which could not be verified using the web tool; those domains are not automatically used by the collector. Easybet search surfaced an explicitly unofficial affiliate site, which was not used. A successful HTML response may be a landing page rather than an odds offer.

**Zero normalized odds snapshots were produced by this new-source run.** The new pages require source-specific validated parsers before their prices can enter training, the dashboard, or model-versus-bookmaker comparisons. Raw HTML is not training evidence. No provider credits were consumed and no application database, active model, prospective trial policy, or training dataset was changed.

The collector now resolves researched inventory `source_url` fields in addition to its original built-in mappings. It preserves the selected region in its source report and returns `source_verification_pending` for unresolved brands instead of crashing with a missing mapping. Tests cover regional routing, unresolved-source network avoidance, safe IDs and source URLs, and existing snapshot normalization.

Verification: all seven sportsbook collector behavioral tests passed. Master inventory IDs are unique (54). Fallow 3.32.0 before/after audits passed without introduced findings; Python is outside its analysis coverage and missing root node_modules limits dependency classification. Syntax compilation passed. The previous 34-brand probe and source report are preserved for adapter work; direct source adapters and broader region discovery remain outstanding.

Repeat from `pipeline/`:

```powershell
py -3 etl/scrape_sportsbooks.py --targets ../stages/03-build/output/sportsbook-sources-africa-20261010.json --sports soccer_epl
py -3 -m unittest discover -s tests -p test_sportsbook_scraping.py -v
```
