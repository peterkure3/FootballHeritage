# ⚽ Football Heritage - Sports Betting Platform

A comprehensive sports betting platform with AI-powered betting advice, real-time odds, and responsible gambling features.

## 🚀 Quick Start

### Backend (Rust + Actix-web)

```bash
cd backend

# 1. Setup database and run migrations
cargo sqlx database create
cargo sqlx migrate run

# 2. Initialize admin account (interactive)
cargo run --bin init_admin

# 3. Start the server
cargo run --release
```

If you run with HTTPS enabled locally, generate a dev certificate first:

```bash
powershell -ExecutionPolicy Bypass -File backend/scripts/generate_dev_tls.ps1
```

### Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

### AI Chatbot (Node.js + Genkit)

```bash
cd chatbot
npm install
npm run dev
```

### Prediction / Data Pipeline (Python + FastAPI)

```bash
cd pipeline
pip install -r requirements.txt
python -m api.main
```

### Odds Ingestion + Betting Intelligence (The Odds API)

This project ingests sportsbook odds from **The Odds API** (polling) into Postgres and computes:

- Devigged probabilities
- +EV bets
- Arbitrage opportunities

Core tables:

- `sportsbook_registry` (book configuration + enable/disable)
- `provider_events` (raw provider events)
- `odds_offers` (normalized odds offers, **decimal odds**)
- `devigged_odds`, `ev_bets`, `arbitrage` (computed betting intelligence)

Required pipeline environment variables (see `pipeline/.env.example`):

- `ODDS_API_KEY`
- `ODDS_API_REGIONS` (default: `us,eu`)
- `ODDS_API_MARKETS` (default: `h2h,spreads,totals`)
- `ODDS_API_SPORTS` (comma-separated sport keys, e.g. `soccer_epl,basketball_nba,...`)

Run the odds pipeline steps manually:

```bash
cd pipeline

# 1) Fetch raw OddsAPI JSON
python -m etl.fetch_raw_data --no-cache

# 2) Ingest raw JSON into provider_events + odds_offers
python -m etl.ingest_oddsapi_offers

# 3) Link provider events to canonical events (creates canonical events for OddsAPI as needed)
python -m etl.match_oddsapi_events

# 4) Compute devig/EV/arbitrage into intelligence tables
python -m etl.compute_intelligence
```

Notes:

- Odds are stored and displayed in **decimal format**.
- Soccer `h2h` can be 3-way (HOME/AWAY/DRAW). The initial intelligence compute step focuses on 2-way markets:
  - `spreads` (HOME/AWAY)
  - `totals` (OVER/UNDER)
  - `h2h` when it is 2-way (e.g. basketball)
- The Intelligence UI pulls match names by joining `events`.

## 📚 Documentation

### Core Features

- **[Setup Guide](SETUP_GUIDE.md)** - Initial setup and configuration
- **[Quick Start](QUICK_START.md)** - Get up and running in 5 minutes
- **[Chatbot Setup](CHATBOT_SETUP_GUIDE.md)** - Basic AI chatbot integration

### Advanced Features

- **[⚡ Super-Fast RAG System](RAG_IMPLEMENTATION_GUIDE.md)** - **NEW!** Implement sub-100ms GPT-style RAG for game and bet queries
- **[NBA Cup Integration](NBA_CUP_INTEGRATION_GUIDE.md)** - NBA In-Season Tournament support
- **[Parlay Calculator](PARLAY_INTEGRATION_GUIDE.md)** - Multi-bet parlay system
- **[Prediction Pipeline](PREDICTION_INTEGRATION_SUMMARY.md)** - ML-powered predictions
- **[Prediction History](pipeline/docs/API_DOCUMENTATION.md)** - Track prediction accuracy over time
- **[Admin Dashboard](ADMIN_DASHBOARD_COMPLETE.md)** - Admin panel features

### Mobile

- **[Mobile App Setup](MOBILE_APP_QUICK_START.md)** - React Native mobile app
- **[Expo Configuration](MOBILE_APP_EXPO_SETUP.md)** - Expo setup guide

### Testing & Deployment

- **[Playwright Testing](PLAYWRIGHT_TESTING_GUIDE.md)** - E2E testing guide
- **[Pipeline Integration](PIPELINE_INTEGRATION_GUIDE.md)** - Data pipeline setup

## 🎯 Key Features

### 1. 📈 Prediction History & Accuracy Tracking (NEW!)

- **Date range picker** with quick presets (7/30/90 days) and custom date selection
- **Confidence distribution chart** showing correct vs incorrect predictions by tier
- **Model versioning** tracking accuracy per model version over time
- **Paginated history** with filters by league, result (correct/incorrect), and date
- **Real-time accuracy metrics** including overall accuracy, by league, and by confidence

**Access:** `/predictions` → Results tab

### 2. 🎯 Best Value Bets

- **ML-powered value detection** using ensemble model (56.6% accuracy)
- **Kelly criterion stake sizing** for optimal bankroll management
- **Edge calculation** comparing model probability vs bookmaker odds
- **Real-time filtering** by minimum edge, bankroll, and bet count

**Access:** `/best-bets` or via Smart Assistant

### 3. 🤖 Smart Betting Assistant

- **No LLM required** - uses intelligent pattern matching
- **Natural language queries** for bets, predictions, and team analysis
- **Rich response cards** with bet details, probabilities, and recommendations
- **Contextual suggestions** for follow-up queries

**Example Queries:**

- "Show me the best value bets"
- "Predict Arsenal vs Liverpool"
- "What matches are on today?"
- "How is Manchester City doing?"

**Access:** `/assistant` or AI Tools menu

### 4. 📊 Enhanced Parlay Builder

- **ML predictions for each leg** with win probability
- **Edge % display** showing value vs bookmaker odds
- **Correlation warnings** for same-league/same-team bets
- **Combined EV calculation** for entire parlay
- **Auto-enrichment** when bets are added

**Access:** `/parlay-calculator` or parlay sidebar on Odds page

### 5. ⚡ Super-Fast RAG System

- **Sub-100ms response time** for natural language queries
- **Hybrid search** combining vector similarity and keyword matching
- **Redis caching** with 60-70% hit rate
- **Streaming responses** for real-time feel
- **Intent routing** for optimized query handling

👉 **[Read the RAG Implementation Guide](RAG_IMPLEMENTATION_GUIDE.md)**

### 6. ⚽ FPL Advisor (NEW!)

AI-powered Fantasy Premier League team optimization:

- **Optimal 15-player squad** within £100m budget
- **Valid formations** (3-4-3, 4-3-3, 4-4-2, etc.)
- **Captain & vice-captain picks** based on expected points
- **Differential picks** (high-potential, low-ownership players)
- **Value picks** (best points-per-million under £6m)
- **Fixture difficulty analysis** for next 5 gameweeks
- **Real-time data** from official FPL API

**Access:** `/fpl-advisor` or Explore menu

### 7. 🎲 Comprehensive Betting Options

- Moneyline bets
- Point spreads
- Over/Under totals
- Parlay calculator
- Live odds updates

### 8. 🛡️ Responsible Gambling

- Daily/weekly/monthly betting limits
- Self-exclusion options
- Session time limits
- Fraud detection and pattern analysis

### 9. 📊 Advanced Analytics

- Win rate tracking
- Profit/loss analysis
- Betting pattern insights
- Team statistics and trends

### 10. 🔒 Security

- JWT authentication
- Encrypted wallet balances
- Rate limiting
- SQL injection prevention
- XSS protection

## 🏗️ Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                         │
│  - Vite + TailwindCSS + Lucide Icons                            │
│  - Smart Assistant, Best Bets, Parlay Builder                   │
│  - Real-time odds & predictions                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
┌──────────────────────┐      ┌──────────────────────────────────┐
│  Backend (Rust)      │      │  ML Pipeline (Python + FastAPI)  │
│  - JWT auth          │      │  - XGBoost/LightGBM Ensemble     │
│  - Betting API       │      │  - ELO ratings, H2H stats        │
│  - Wallet/Users      │      │  - Value bet detection           │
└──────────┬───────────┘      │  - Parlay enrichment             │
           │                  │  - Smart Assistant (no LLM)      │
           │                  └──────────────┬───────────────────┘
           │                                 │
           └─────────────┬───────────────────┘
                         ▼
              ┌──────────────────────┐
              │  PostgreSQL Database │
              │  - Matches & Odds    │
              │  - ML Predictions    │
              │  - Users & Bets      │
              │  - Vector Embeddings │
              └──────────────────────┘
```

## 🧠 ML Model Performance

| Metric | v1.0.0 | v2.0.0 (Current) |
|--------|--------|------------------|
| **Validation Accuracy** | 46% | **56.6%** |
| **Live Accuracy** | N/A | **72.74%** |
| **High Confidence** | N/A | **94.86%** |
| **Features** | 13 | **38** |
| **Model Type** | XGBoost | **Stacking Ensemble** |
| **Calibration** | None | **Isotonic Regression** |

**v2.0.0 Features Include:**

- ELO ratings with home advantage
- Head-to-head historical stats
- Weighted form (exponential decay)
- Venue-specific performance
- Advanced odds engineering (implied probs, log odds, fair probs)

**Prediction Tracking:**

- 543+ predictions tracked with results
- Model version history with per-version accuracy
- Confidence-based accuracy breakdown (High: 94.86%, Medium: 62.55%, Low: 46.51%)

## 🎓 RAG System Performance

| Metric | Target | Achieved |
|--------|--------|----------|
| **Cached Response** | 20ms | 15-18ms |
| **Uncached Response** | 100ms | 95-110ms |
| **Cache Hit Rate** | 60% | 65-70% |
| **Throughput** | 100 req/s | 120+ req/s |

## 🛠️ Technology Stack

### Backend

- **Rust** - High-performance API server
- **Actix-web** - Async web framework
- **SQLx** - Type-safe SQL queries
- **PostgreSQL** - Primary database
- **pgvector** - Vector similarity search

### AI/ML

- **Node.js** - Chatbot microservice
- **Genkit** - AI framework
- **Google Gemini** - LLM (free tier)
- **Redis** - Response caching
- **text-embedding-004** - Embeddings (768 dims)

### Frontend

- **React** - UI framework
- **Vite** - Build tool
- **TailwindCSS** - Styling
- **Lucide Icons** - Icon library

### Mobile

- **React Native** - Mobile framework
- **Expo** - Development platform

## 📦 Installation

### Prerequisites

- Rust 1.70+
- Node.js 18+
- PostgreSQL 14+
- Redis 7+
- Gemini API key (free)

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/FootballHeritage.git
cd FootballHeritage
```

### 2. Setup Database

```bash
cd backend

# Create database and run migrations (requires sqlx-cli)
cargo install sqlx-cli --no-default-features --features postgres
cargo sqlx database create
cargo sqlx migrate run

# Optional: Install pgvector for RAG features
psql -U postgres -d football_heritage -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**Note:** If pgvector is not available, RAG migrations are skipped automatically.

### 3. Configure Environment

```bash
# Backend
cd backend
cp .env.example .env
# Edit .env with your database credentials and encryption key (must be 32 bytes)

# Set APP_ENV explicitly (recommended)
# APP_ENV=development|staging|production

# Chatbot
cd ../chatbot
cp .env.example .env
# Add your GEMINI_API_KEY from https://makersuite.google.com/app/apikey

# Pipeline
cd ../pipeline
cp .env.example .env
# Set DB_PASSWORD and API_ALLOWED_ORIGINS (e.g. http://localhost:5173)
```

### 4. Initialize Admin Account

```bash
cd backend
cargo run --bin init_admin
```

Follow the interactive prompts to create your first admin user.

### 5. Install Dependencies

```bash
# Backend
cd backend
cargo build --release

# Frontend
cd ../frontend
npm install

# Chatbot
cd ../chatbot
npm install
```

### 6. Run Services

```bash
# Terminal 1: Backend
cd backend
cargo run --release

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3: Chatbot
cd chatbot
npm run dev

# Terminal 4: Redis
redis-server

# Terminal 5: Pipeline API (optional)
cd pipeline
python -m api.main
```

To view betting intelligence in the UI:

- `http://localhost:5173/devigged-odds`
- `http://localhost:5173/ev-bets`
- `http://localhost:5173/arbitrage`

### 7. Initialize RAG System

```bash
cd chatbot
node scripts/sync-embeddings.js
```

## 🧪 Testing

### Backend Tests

```bash
cd backend
cargo test
```

### Frontend Tests

```bash
cd frontend
npm run lint
```

### E2E Tests

```bash
npx playwright test
```

### API Tests

```bash
# Test health endpoint
curl http://localhost:8080/api/v1/health

# Test chat endpoint (requires JWT)
curl -X POST http://localhost:8080/api/v1/chat \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Show me todays games"}'
```

## 📊 Performance Monitoring

### Metrics Endpoint

```bash
curl http://localhost:8080/metrics
```

**Response:**

```json
{
  "total": {
    "count": 1000,
    "avg": "45.23",
    "p95": "120.50"
  },
  "cached": {
    "count": 680,
    "avg": "16.80",
    "hitRate": "68.0"
  },
  "uncached": {
    "count": 320,
    "avg": "102.45"
  }
}
```

## 🚀 Deployment

### Production Checklist

- [ ] Set `NODE_ENV=production`
- [ ] Enable database SSL
- [ ] Configure Redis persistence
- [ ] Set up reverse proxy (nginx)
- [ ] Enable HTTPS
- [ ] Configure monitoring (Prometheus/Grafana)
- [ ] Set up log aggregation
- [ ] Configure backup strategy
- [ ] Run embedding sync cron job
- [ ] Test cache invalidation

### Docker Deployment

```bash
docker-compose up -d
```

## 💾 Database Backup & Restore

### Backup Databases

Create a backup of both databases (pipeline + backend):

```bash
cd scripts

# Using Python script
python backup_databases.py --db-password YOUR_PASSWORD

# Or using batch file (Windows)
backup_databases.bat YOUR_PASSWORD
```

Backups are saved to `backups/<timestamp>/` with:
- `football_betting_<timestamp>.sql` - Pipeline data (matches, odds, predictions)
- `football_heritage_<timestamp>.sql` - Backend data (users, wallets, bets, events)
- `backup_manifest_<timestamp>.txt` - Backup details and restore instructions

### Restore Databases

Restore from a backup after data loss or on a new machine:

```bash
cd scripts

# Restore all databases
python restore_databases.py --backup-dir ../backups/20260131_170000 --db-password YOUR_PASSWORD

# Clean restore (drops existing data first)
python restore_databases.py --backup-dir ../backups/20260131_170000 --db-password YOUR_PASSWORD --clean

# Restore specific database only
python restore_databases.py --backup-dir ../backups/20260131_170000 --db-password YOUR_PASSWORD --database football_heritage
```

### Recommended Backup Schedule

| Frequency | What to Backup | Why |
|-----------|---------------|-----|
| **Daily** | Both databases | Protect against data loss |
| **Before updates** | Both databases | Rollback if issues |
| **Weekly** | Copy to external drive | Disaster recovery |

### Quick Recovery Steps

If you need to set up on a new machine:

1. Install PostgreSQL and create the databases
2. Clone the repository
3. Restore databases:
   ```bash
   python scripts/restore_databases.py --backup-dir backups/LATEST --db-password YOUR_PASSWORD --clean
   ```
4. Configure `.env` files in `backend/` and `pipeline/`
5. Start services

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Google Gemini for free AI API
- pgvector for vector search
- Actix-web community
- React and Vite teams

## 📞 Support

For issues or questions:

1. Check the [RAG Implementation Guide](RAG_IMPLEMENTATION_GUIDE.md)
2. Review [Troubleshooting](CHATBOT_SETUP_GUIDE.md#troubleshooting)
3. Open an issue on GitHub
4. Check metrics endpoint for performance issues

---

**Built with ⚡ by Football Heritage Team**