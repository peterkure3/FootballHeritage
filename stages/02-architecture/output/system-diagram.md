# System Architecture — FootballHeritage

## Current Architecture (Component Diagram)

```mermaid
graph TB
    subgraph External["External Data Sources"]
        OAPI[The Odds API]
        FD[football-data.org]
        BDI[balldontlie.io]
        NCAA[NCAA API]
        FPL[FPL API]
        BR[Basketball Reference<br/>Scraper]
    end

    subgraph Pipeline["Data Pipeline (Python/FastAPI :5555)"]
        ETL[ETL Modules<br/>fetch → transform → load]
        ML[ML Models<br/>Stacking Ensemble<br/>Elo Ratings]
        IQ[Intelligence<br/>Devig / EV / Arbitrage]
        PA[Pipeline API<br/>24 endpoints]
    end

    subgraph Backend["Backend (Rust/Actix :8080)"]
        GW[API Gateway<br/>40+ endpoints]
        AUTH[Auth Service<br/>JWT + Sessions]
        BET[Betting Service<br/>Placement / Limits]
        WAL[Wallet Service<br/>Encrypted Balances]
        PAR[Parlay Service<br/>Calculator + Enrichment]
        MON[Monitoring<br/>Metrics + Rate Limits]
    end

    subgraph Frontend["Frontend (React/Vite :5173)"]
        UI[27 Pages<br/>Components + Hooks]
        STORE[Zustand Stores<br/>Auth / Betting / Parlay / Settings]
        Q[React Query<br/>Data Fetching + Cache]
    end

    subgraph Frontend["Frontend (React/Vite :5173)"]
        UI[27 Pages<br/>Components + Hooks]
        CHAT[Chatbot Feature<br/>RAG + Gemini 2.0<br/>Integrated in Frontend]
        STORE[Zustand Stores<br/>Auth / Betting / Parlay / Settings]
        Q[React Query<br/>Data Fetching + Cache]
    end

    subgraph DB["PostgreSQL"]
        MAIN[(football_betting<br/>Matches / Odds / Predictions)]
        HERITAGE[(football_heritage<br/>Users / Bets / Events / Intelligence)]
    end

    External -->|REST / Scrape| ETL
    ETL -->|Write| MAIN
    ETL -->|Write| HERITAGE
    PA -->|Read| MAIN
    PA -->|Read| HERITAGE
    ML -->|Predictions| MAIN
    IQ -->|Intelligence| HERITAGE
    
    GW -->|Auth| AUTH
    GW -->|Bets| BET
    GW -->|Wallet| WAL
    GW -->|Parlays| PAR
    GW -->|Metrics| MON
    
    BET --> HERITAGE
    WAL --> HERITAGE
    PAR --> HERITAGE
    PAR --> PA
    
    PA -->|REST| GW
    
    UI -->|REST / WS| GW
    UI -->|REST| PA
    UI -->|POST /chat| GW
    
    GW -->|Proxy /chat| Chatbot
    ROUTER --> RAG
    RAG --> CACHE
    RAG --> HERITAGE
    CACHE --> REDIS[(Redis)]
```

## Planned Additions (Next 3 Months)

```mermaid
graph TB
    subgraph New["New / Enhanced Components"]
        US[Understat Scraper<br/>xG Data]
        PP[Player Props Engine<br/>The Odds API + UI]
        EP[Enhanced Parlay<br/>System Bets + Correlation]
        LS[Live Scores<br/>WebSocket Push]
        MON2[Monitoring Stack<br/>Prometheus + Grafana]
    end

    subgraph Existing["Existing Components"]
        OAPI[The Odds API<br/>NFL / MLB / NHL / more]
        FR[Frontend Pages<br/>New sport views]
        PL[Pipeline ETL<br/>New sport ETL jobs]
    end

    US -->|xG features| ML
    PP -->|Props odds| OAPI
    PP -->|Props UI| FR
    EP -->|System bets| PL
    LS -->|Live updates| OAPI
    
    MON2 -->|Metrics scrape| GW
    MON2 -->|Metrics scrape| PA
    MON2 -->|Dashboard| FR
```

## Data Flow for New Sports (NFL / MLB / NHL)

```
1. Config: Add sport keys to ODDS_API_SPORTS env var
2. ETL: Existing fetch_raw_data.py handles any sport key generically
3. Transform: Add transform_{sport}.py (or reuse generic odds transform)
4. Load: Existing load_to_db.py handles any sport
5. Backend: Events table has sport + league columns — works generically
6. Frontend: Add sport-specific pages or expand filters in Odds page
```

## Key Integration Points
| Integration | Protocol | Data Format |
|-------------|----------|-------------|
| Pipeline → Backend | REST | JSON |
| Backend → Frontend | REST + WebSocket | JSON |
| Backend → Chatbot | REST (proxy) | JSON |
| Pipeline → DB | SQL (sqlx) | PostgreSQL |
| Chatbot → Gemini | REST | JSON (Gemini SDK) |
| Chatbot → Redis | RESP (ioredis) | String (JSON) |
