# Blockers — Stage 02 Architecture

## No Blockers

Architecture work is based on existing, well-understood patterns. All ADRs document decisions with clear consequences. Key items to validate before build:

1. **The Odds API quota** — add NFL/MLB/NHL incrementally, test quota consumption
2. **Understat scraper** — confirm data availability and scraper approach before committing to xG integration
3. **Player props** — verify The Odds API covers player props for target sports/regions
