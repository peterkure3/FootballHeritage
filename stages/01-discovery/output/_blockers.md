# Blockers — Stage 01 Discovery

## None Critical

No blockers that prevent proceeding to architecture. Key risks to monitor:

- **The Odds API quota** — adding NFL, MLB, NHL simultaneously may hit free tier limits. May need to stagger rollout or upgrade plan.
- **Basketball Reference scraping** — fragile scraping approach. Prefer balldontlie.io API where possible.
- **No live odds WebSocket/streaming** — current polling approach (5-min) is acceptable for pre-match but will not support live betting.
