# Discovery Dossier — FootballHeritage

## 1. Data Source Deep-Dive

### The Odds API (Primary Odds Source)
- **Coverage:** 70+ sports, 40+ bookmakers, h2h/spreads/totals/outrights
- **Supports expansion sports:** `americanfootball_nfl`, `baseball_mlb`, `icehockey_nhl`, `americanfootball_ncaaf`, plus more soccer leagues
- **Regions:** US, EU, UK, AU bookmakers available
- **Markets:** moneyline, spreads, totals, some player props (US/AU bookmakers)
- **Historical data:** Available from mid-2020 for featured markets
- **Limitations:** Free tier quota limits; rate-limited polling needed
- **Status:** Already integrated — ETL pipeline exists (fetch → ingest → match → compute)

### football-data.org (Match Data)
- **Coverage:** European soccer competitions
- **Current:** PL, CL, EC tracked
- **Expansion:** Can add more leagues (Bundesliga, Serie A already partially covered via The Odds API)
- **Limitation:** No odds data — used for match info, standings, team stats
- **Status:** Already integrated in ETL pipeline

### balldontlie.io (NBA Stats)
- **Coverage:** NBA player/game stats
- **Status:** Already integrated
- **Expansion:** Can enhance NBA feature engineering

### NCAA API (College Sports)
- **Coverage:** NCAA basketball (men's + women's)
- **Status:** Already integrated
- **Expansion:** Could add NCAA football if needed

### Basketball Reference (Web Scrape)
- **Current:** NBA historical stats
- **Status:** ETL module exists
- **Risk:** Scraping reliability, terms of service changes

### FPL API (Fantasy Premier League)
- **Coverage:** FPL player data, fixtures, gameweeks
- **Status:** Integrated with dedicated FPL advisor pages

## 2. ML Landscape Analysis

### Current Model Performance vs Benchmarks

| Source | Accuracy | Notes |
|--------|----------|-------|
| **FootballHeritage v2** | **72.74% live** | Stacking Ensemble, 38 features, isotonic calibration |
| **FootballHeritage (high conf)** | **94.86%** | Top confidence tier |
| XGBoost benchmarks (soccer 3-way) | 60-68% | Typical range for 3-class football prediction |
| XGBoost (NBA binary) | 91% | NBA has no draw class — easier problem |
| LightGBM (soccer) | 51.8% (best log loss) | Better calibration, worse accuracy |
| UniSportXGB (multi-sport) | 68.3% football, 71.4% cricket | Academic baseline |
| World Cup 2026 XGBoost | 60-61% | Live accuracy on international football |

**Key finding:** FootballHeritage's ML model already performs at or above published benchmarks. The edge strategy (value betting over pure accuracy) is what drives profitability.

### Improvement Opportunities
1. **Feature expansion** — add xG (Expected Goals) data from Understat or similar for soccer
2. **Player-level features** — injuries, suspensions, key player form for all sports
3. **Model specialization** — separate models per league/sport instead of one ensemble
4. **Calibration refinement** — LightGBM showed better log loss in benchmarks; consider adding as ensemble component
5. **Live/in-play model** — train on in-game features for live betting (60-min mark prediction as seen in XCALIBUR)

### Competitor Landscape
| Competitor Type | Examples | Approach |
|-----------------|----------|----------|
| **DIY bettors** | GitHub projects (EPL-betting, WM_2026) | XGBoost/LightGBM, edge strategy, Kelly sizing |
| **Commercial tipsters** | Action Network, Covers | Human analysis + basic stats, subscription model |
| **Data platforms** | Sportradar, Opta | Expensive enterprise APIs, not available to individuals |
| **ML platforms** | Unibet/Pinnacle internal | Proprietary models, not public |

**Differentiator:** FootballHeritage combines full-stack platform + RAG chatbot + ML pipeline in a single integrated system. Most competitors are either pure prediction models without UI, or commercial services without transparency.

## 3. User Journeys

### Journey 1: Bettor Seeking Value
1. Logs in → Dashboard (sees balance, recent activity, trending bets)
2. Browses **Odds** page → filters by sport/league → views moneyline/spreads/totals
3. Checks **Best Bets** → sees ML-recommended bets with edge % and Kelly stake
4. Reviews **+EV Bets** → sorts by EV % → selects a bet
5. Clicks odds → places bet via **BetConfirmationModal** (limit check, balance check)
6. Tracks bet on **Bet History** page → sees result after match settles

### Journey 2: Analytics User
1. Opens **Predictions** page → views accuracy metrics (overall, by league, by confidence)
2. Filters history by date range → reviews correct/incorrect model calls
3. Uses **"What If" Predictor** → enters two teams → sees model probability
4. Opens **Smart Assistant** → asks "Who wins Arsenal vs Liverpool?" → gets RAG response
5. Reviews **Devigged Odds** → sees true probabilities vs bookmaker margins

### Journey 3: Admin Managing Platform
1. Logs in → navigates to **Admin Dashboard** → sees KPIs (users, bets, revenue, alerts)
2. Manages **Events** → creates/edit events, updates statuses
3. Reviews **Users** → checks activity, suspends if needed
4. Monitors **Fraud Alerts** → investigates suspicious patterns
5. Views **Analytics** → revenue trends, user growth, bet volume

## 4. Gap Analysis & Recommendations

| Gap | Priority | Recommendation |
|-----|----------|----------------|
| No live/in-play betting | High | Add live event status, WebSocket odds push, in-play bet placement |
| No player props market | High | Support player prop markets from The Odds API + UI for prop bets |
| Missing sports (NFL, MLB, NHL) | High | Add sport keys to `ODDS_API_SPORTS`, create UI pages |
| No xG data for soccer | Medium | Add Understat scraper or xG API for soccer feature improvement |
| Test coverage low | Medium | Expand backend `cargo test`, frontend Vitest, Playwright E2E |
| No monitoring/alerting | Medium | Add health check dashboards, error rate alerts |
| Playwright test config disabled | Low | Re-enable and fix test config |
| Port/env inconsistencies | Low | Standardize frontend .env, fix port references |

## 5. Validation Summary

| Assumption | Status | Source |
|------------|--------|--------|
| The Odds API covers target sports | ✅ Confirmed | API docs show NFL, MLB, NHL, more soccer |
| Current ML accuracy is competitive | ✅ Confirmed | 72.74% beats published benchmarks (60-68%) |
| Solo developer can ship this scope | ⚠️ Feasible | Need to prioritize: ML + UI + 1-2 new sports first |
| Free-tier APIs sufficient | ⚠️ Monitor | The Odds API quota may need upgrade with more sports |
| Existing architecture extensible | ✅ Confirmed | Clean module separation, easy to add new sports |
