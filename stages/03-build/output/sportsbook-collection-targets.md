# User-selected sportsbook collection targets

Original collection plan recorded 2026-10-08. Machine-readable inventory: `sportsbook-sources.json`.
On 2026-10-10, 34 additional brands expanded the inventory to 54 unique bookmaker
IDs. The new-source live check and current adapter coverage are documented in
`african-bookmaker-check-20261010.md`; the notes below describe the original plan.
All 20 requested books are retained. This is a collection plan, not verified live
scraper coverage or an enabled database registry migration.

Each scraper emits the JSONL contract in `bookmaker-data-format.md`. Use the stable
`bookmaker` ID in this inventory and `provider: scraper_<bookmaker>` for direct
collection. For aggregator collection use its real provider ID and provider-specific
bookmaker key, retaining the same internal bookmaker identity and regional variant.

## Existing-provider mappings

The current [Odds API bookmaker list](https://the-odds-api.com/sports-odds-data/bookmaker-apis.html)
documents mappings for 15 requested brands, with bet365's documented variant limited
to AFL/NRL. Listings do not guarantee current football fixtures, a particular market,
account-plan access, historical archives, or local availability. Validate these
before reporting a collector as working. The remaining five require a verified site
adapter or another feed; absence from this list is not evidence that they cannot
be collected elsewhere.

Two existing registry seeds need review before provider integration:

- Caesars internal ID `caesars` currently seeds provider key `caesars`, while the
  provider documents `williamhill_us`.
- bet365 currently seeds `bet365` in region `eu`; the current provider list documents
  `bet365_au` for limited non-football markets. Do not claim football support from it.

TheScore Bet retains provider key `espnbet`. The
[operator's rebrand notice](https://espnbet.zendesk.com/hc/en-us/articles/40921200115725-ESPN-BET-Rebrand-to-theScore-Bet)
dates the ESPN BET transition to December 1, 2025. Store historical branding as an
alias; do not merge US and Canadian offerings solely because the brand matches.

## What to collect first

Start with all three regulation-time football h2h outcomes. Preserve precise kickoff,
scraper observation timestamp, market status, source event/team IDs, source URL and
state/country variant. Store snapshots for the same fixture across books at the same
chosen prediction horizon, then add timestamped results after settlement.

The existing importer requires enabled sportsbook registry mappings and currently
hardcodes provider `oddsapi`. No ingestion adapter for these direct JSONL snapshots
has been implemented in this inventory task. No bookmaker accounts were accessed,
paid API requests issued, database registry entries changed, or scraping jobs started.
