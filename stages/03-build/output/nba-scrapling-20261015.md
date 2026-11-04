# NBA Scrapling capture — 2026-10-15

Collected 121 unique games from the official NBA games pages for October 8–29, 2026: 36 completed games and 85 upcoming games. The capture includes 50 preseason games and 71 regular-season games, 30 NBA teams plus the Lions preseason opponent, and 72 player-leader observations. These are game leaders, not full player box scores.

## Files

Capture directory: `pipeline/data/raw/nba/scrapling/20261015T162855408757Z/`.

- `games.json` / `games.csv`: fixtures, UTC start times, opponents and IDs, status, season type, scores, and source links.
- `teams.json` / `teams.csv`: 31 observed team identities, including the preseason guest team.
- `player_leaders.json` / `player_leaders.csv`: provider-selected player leaders and points/rebounds/assists/blocks/steals.
- `games-YYYY-MM-DD-raw.json`: embedded NBA page data for each of 22 dates.
- `manifest.json`: counts, source URLs, capture checksums, export checksums, and collection outcomes.

Re-run from `pipeline/`:

```powershell
.\.venv-scrapling\Scripts\python.exe ..\stages\03-build\output\collect-nba-official-scrapling.py
```

Each run creates a new timestamped directory and uses a rolling seven-day lookback and fourteen-day lookahead. The collector uses the existing `ScraplingTransport`, checks robots policy, and pauses one second between game pages.

## Verification and limits

All 22 daily requests returned HTTP 200. Every extracted daily game count matched the NBA page's date index. Verified 121 unique game IDs, all raw and export checksums, CSV/JSON game-count parity, and null scores for unplayed games. Collector exited successfully with zero failures.

NBA team names follow game-card labels (for example, Cavaliers rather than Cleveland Cavaliers). Preseason and regular-season games remain explicitly labeled. Do not treat preseason guest teams or games as regular-season training data. No odds, standings, full box scores, database ingestion, or model training were performed.

The initial ESPN attempt and the NBA CDN attempt stopped because their robots endpoints returned HTTP 403. The empty ESPN attempt is retained at `pipeline/data/raw/nba/scrapling/20261015T162540493838Z/` as failure evidence. The successful collection uses `https://www.nba.com/games?date=YYYY-MM-DD`, whose robots policy and pages were accessible.
