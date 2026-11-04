# Live Premier League bookmaker check — 10 October 2026

Captured at 11:12:36 UTC / 14:12:36 Africa/Kampala. All six English Premier League fixtures were scheduled, prematch, and offered an open regulation-time three-way moneyline in Bovada's direct public feed. Decimal prices below are capture-time quotes, not guaranteed executable prices later.

| Fixture | Kickoff Kampala | Home | Draw | Away |
|---|---|---:|---:|---:|
| Arsenal — Leeds United | 14:30 | 1.458716 | 4.50 | 7.00 |
| Aston Villa — Brentford | 17:00 | 2.75 | 3.50 | 2.50 |
| Chelsea — Bournemouth | 17:00 | 1.819672 | 3.90 | 4.10 |
| Ipswich Town — Fulham | 17:00 | 2.75 | 3.45 | 2.50 |
| Sunderland — Brighton | 17:00 | 3.10 | 3.45 | 2.30 |
| Manchester United — Tottenham | 19:30 | 1.735294 | 4.10 | 4.30 |

Official fixture verification: https://www.premierleague.com/en/news/4688862/fixture-amendments-for-premier-league-matches-in-october-and-november

Collector: `py -3 etl/scrape_sportsbooks.py --provider-fallback --sports soccer_epl` from `pipeline/`. Capture directory: `pipeline/data/raw/sportsbooks/20261010T111221381609Z/`. Source report includes individual results for all 20 targets. Bovada yielded 1,872 football snapshots across competitions; six were selected using country England, competition Premier League, and UTC kickoff date 2026-10-10. Other direct requests yielded no normalized prices because of access restrictions, connection failure, or missing adapters. The configured multi-bookmaker provider rejected the EPL request with HTTP 401, `OUT_OF_USAGE_CREDITS`, quota remaining 0. This check establishes coverage for one bookmaker only.

Compact full-provenance six-fixture capture: `epl-bookmaker-quotes-20261010.json`. Full normalized capture: `pipeline/data/raw/sportsbooks/20261010T111221381609Z/odds_snapshots.jsonl`.

Prior dashboard verification stored today's fixture starts three hours later than these independently agreeing official and bookmaker UTC times. That discrepancy requires investigation before exact kickoff joins or betting-edge presentation. No fixture timestamps, application database odds, training artifacts, or active models were changed by this check. No model advantage was evaluated or established.
