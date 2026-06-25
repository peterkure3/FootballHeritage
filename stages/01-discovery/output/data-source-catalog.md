# Data Source Catalog — FootballHeritage

## External APIs

### The Odds API
| Property | Value |
|----------|-------|
| **URL** | `https://api.the-odds-api.com/v4` |
| **Auth** | API key (query param `apiKey`) |
| **Data** | Live/upcoming sportsbook odds, scores |
| **Markets** | `h2h`, `spreads`, `totals`, `outrights`, some player props |
| **Regions** | `us`, `us2`, `uk`, `eu`, `au` |
| **Odds Format** | Decimal (American available) |
| **Refresh Cadence** | Poll every 5 minutes (configurable) |
| **Historical** | Available from mid-2020 (featured markets) |
| **Currently Tracked** | `soccer_epl`, `soccer_spain_la_liga`, `soccer_germany_bundesliga`, `soccer_italy_serie_a`, `soccer_france_ligue_one`, `basketball_nba`, `basketball_ncaab` |
| **To Add** | `americanfootball_nfl`, `baseball_mlb`, `icehockey_nhl`, `americanfootball_ncaaf`, more soccer |
| **ETL Module** | `pipeline/etl/fetch_raw_data.py`, `pipeline/etl/ingest_oddsapi_offers.py`, `pipeline/etl/match_oddsapi_events.py` |

### football-data.org
| Property | Value |
|----------|-------|
| **URL** | `https://api.football-data.org/v4` |
| **Auth** | API key (header `X-Auth-Token`) |
| **Data** | Match info, scores, standings, competitions |
| **Refresh Cadence** | Poll every 1 hour |
| **Currently Tracked** | PL (2021), CL (2001), EC (2018) |
| **ETL Module** | `pipeline/etl/fetch_raw_data.py` |

### balldontlie.io (NBA)
| Property | Value |
|----------|-------|
| **URL** | `https://api.balldontlie.io/v1` |
| **Auth** | API key |
| **Data** | NBA player stats, game stats, team info |
| **Refresh Cadence** | Poll every 1 hour |
| **Currently Tracked** | NBA 2024 season |
| **ETL Module** | `pipeline/etl/fetch_nba_data.py`, `pipeline/etl/transform_nba_data.py` |

### NCAA API
| Property | Value |
|----------|-------|
| **URL** | `https://ncaa-api.henrygd.me` |
| **Auth** | None (rate limited) |
| **Data** | NCAA basketball scores, schedules |
| **Refresh Cadence** | Poll every 15 minutes |
| **Currently Tracked** | Men's & Women's Division I basketball |
| **ETL Module** | `pipeline/etl/fetch_ncaa_data.py`, `pipeline/etl/transform_ncaa.py` |

### FPL API (Fantasy Premier League)
| Property | Value |
|----------|-------|
| **URL** | Official FPL API (no base URL constant visible) |
| **Auth** | None |
| **Data** | Player data, fixtures, gameweeks, expected points |
| **Refresh Cadence** | On-demand / daily |
| **ETL Module** | `pipeline/etl/fetch_fpl_data.py`, `pipeline/etl/fpl_optimizer.py` |

## Web Scrapers

### Basketball Reference
| Property | Value |
|----------|-------|
| **URL** | `https://www.basketball-reference.com` |
| **Data** | NBA historical stats, player stats, game logs |
| **Risk** | Terms of service, IP blocking at high frequency |
| **ETL Module** | `pipeline/etl/fetch_basketball_reference.py`, `pipeline/etl/fetch_basketball_reference_async.py` |

### Understat (Recommended — Not Yet Integrated)
| Property | Value |
|----------|-------|
| **URL** | `https://understat.com` |
| **Data** | Expected Goals (xG), xGA, xG per shot |
| **Use Case** | Soccer feature engineering — rolling xG averages improve model accuracy (benchmarks show ~1% gain) |
| **Status** | Not integrated — **recommended for Stage 03** |

## Internal Databases

### football_betting (Main)
| Property | Value |
|----------|-------|
| **Host** | `localhost:5432` |
| **Name** | `football_betting` |
| **Purpose** | Pipeline ETL storage — matches, odds, predictions, NBA games |
| **Key Tables** | `matches`, `odds`, `predictions`, `nba_games` |

### football_heritage (Platform)
| Property | Value |
|----------|-------|
| **Host** | `localhost:5432` |
| **Name** | `football_heritage` |
| **Purpose** | Platform state — users, wallets, bets, events, intelligence |
| **Key Tables** | `users`, `wallets`, `bets`, `events`, `parlays`, `devigged_odds`, `ev_bets`, `arbitrage` |
| **Redis** | Chatbot cache (RAG response caching, 65-70% hit rate) |

## Data Quality Notes
- **The Odds API:** Reliable, well-documented, JSON format. Free tier quota may be limiting with more sports.
- **football-data.org:** Reliable, but no odds data. Used for match metadata only.
- **balldontlie.io:** Reliable NBA data source. Good for feature engineering.
- **NCAA API:** Free, no auth, but less reliable (third-party proxy).
- **Basketball Reference:** Scraping is fragile. Prefer balldontlie.io where possible.
- **Historical gaps:** Some training data is from CSV files with inconsistent column naming — the v2 model handles this with normalization mappings.
