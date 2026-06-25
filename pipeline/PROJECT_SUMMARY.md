# Football Betting Pipeline - Project Summary

## Overview

Production-ready football betting prediction pipeline with ETL, ML models, REST API, and orchestration.

## Project Structure

```
sports-betting-pipeline/
├── config.py                      # Central configuration
├── requirements.txt               # Python dependencies
├── schema.sql                     # PostgreSQL schema
├── run_pipeline.py               # Manual pipeline runner
├── README.md                      # Full documentation
├── QUICKSTART.md                  # Quick start guide
├── .env.example                   # Environment template
├── .gitignore                     # Git ignore rules
│
├── data/                          # Data storage
│   ├── raw/
│   │   ├── football_data_org/    # API data from football-data.org
│   │   ├── the_odds_api/         # API data from The Odds API
│   │   └── historical/           # Historical CSV files
│   ├── interim/                   # Intermediate processing
│   └── processed/                 # Final parquet files
│
├── etl/                           # ETL pipeline
│   ├── __init__.py
│   ├── utils.py                   # Logging, retry logic, helpers
│   ├── fetch_raw_data.py         # Fetch from APIs
│   ├── transform.py              # Feature engineering
│   └── load_to_db.py             # Database loading
│
├── models/                        # ML models
│   ├── __init__.py
│   ├── train_model.py            # XGBoost training
│   ├── predict.py                # Generate predictions
│   ├── evaluate.py               # Model evaluation
│   └── model_store/              # Saved models & metrics
│
├── api/                           # FastAPI application
│   ├── __init__.py
│   ├── main.py                   # FastAPI app setup
│   └── routes.py                 # API endpoints
│
└── dags/                          # Airflow orchestration
    └── betting_pipeline.py       # Weekly DAG
```

## Components

### 1. Configuration (`config.py`)
- API keys and endpoints
- Database connection
- Model hyperparameters
- Feature engineering settings
- File paths and naming conventions

### 2. ETL Pipeline

#### `etl/utils.py`
- JSON-structured logging
- Retry decorators with exponential backoff
- HTTP session management
- File I/O helpers

#### `etl/fetch_raw_data.py`
- Fetches from football-data.org (matches, competitions)
- Fetches from The Odds API (odds, scores)
- Saves raw JSON to `data/raw/`
- Implements retry logic and error handling

#### `etl/transform.py`
- Normalizes JSON/CSV to DataFrames
- Feature engineering:
  - Team form (last 5 matches)
  - Goal difference averages
  - Odds spreads
- Saves processed Parquet files

#### `etl/load_to_db.py`
- Upserts data to PostgreSQL
- Idempotent operations
- Transactional writes

### 3. ML Models

#### `models/train_model.py`
- Loads processed data
- Trains XGBoost classifier
- Saves model, encoder, features, metrics
- Generates feature importance

#### `models/predict.py`
- Loads trained model
- Fetches upcoming matches
- Generates predictions with probabilities
- Saves to predictions table

#### `models/evaluate.py`
- Evaluates model performance
- Generates metrics and confusion matrix
- Saves evaluation reports

### 4. API (`api/`)

#### Endpoints

**GET /api/v1/predictions/{match_id}**
- Returns prediction with probabilities

**GET /api/v1/matches**
- Lists matches with odds
- Filters: competition, date, limit

**GET /api/v1/health**
- Health check and pipeline status

### 5. Orchestration (`dags/betting_pipeline.py`)

Weekly Airflow DAG:
1. Fetch raw data
2. Transform data
3. Load to database
4. Train model
5. Generate predictions
6. Cleanup old files

## Database Schema

### Tables

**matches**
- Match details, scores, statistics
- Team form features
- Status tracking

**odds**
- Bookmaker odds
- Multiple bookmakers per match
- Timestamp tracking

**predictions**
- Model predictions
- Probabilities for each outcome
- Model version tracking

## Features

### Engineered Features
1. **Team Form** (last 5 matches)
   - Wins, draws, losses
   - Separate for home/away

2. **Goal Difference**
   - Average over last 5 matches
   - Per team

3. **Odds Data**
   - Home win, draw, away win
   - Odds spread

### Model
- **Algorithm**: XGBoost Classifier
- **Target**: 3-class (home_win, draw, away_win)
- **Output**: Winner prediction + probabilities

## Key Features

✅ **Modular Design**: Separate ETL, models, API
✅ **Error Handling**: Retries, transactions, logging
✅ **Idempotency**: Safe to re-run
✅ **Versioning**: Model and data versioning
✅ **Observability**: JSON logging throughout
✅ **Scalability**: Handles 10-30 matches/week
✅ **Documentation**: Comprehensive README and docstrings
✅ **Type Hints**: Full type annotations
✅ **Configuration**: Centralized config file

## Data Flow

```
APIs (football-data.org, The Odds API)
    ↓
Raw JSON (data/raw/)
    ↓
Transform & Feature Engineering
    ↓
Processed Parquet (data/processed/)
    ↓
PostgreSQL Database
    ↓
XGBoost Model Training
    ↓
Predictions → Database
    ↓
FastAPI → Users
```

## Running the Pipeline

### Manual Execution
```bash
python run_pipeline.py
```

### Individual Steps
```bash
python -m etl.fetch_raw_data
python -m etl.transform
python -m etl.load_to_db
python -m models.train_model
python -m models.predict
```

### API Server
```bash
python -m api.main
```

### Airflow (Automated)
```bash
airflow scheduler
airflow webserver
```

## Environment Variables

Required in `.env`:
- `FOOTBALL_DATA_ORG_API_KEY`
- `THE_ODDS_API_KEY`
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`

## Dependencies

Core packages:
- `fastapi` - REST API framework
- `uvicorn` - ASGI server
- `pandas` - Data manipulation
- `xgboost` - ML model
- `sqlalchemy` - Database ORM
- `psycopg2-binary` - PostgreSQL driver
- `apache-airflow` - Orchestration
- `requests` - HTTP client

## Next Steps

1. Add API keys to `.env`
2. Create PostgreSQL database
3. Run `schema.sql`
4. Execute pipeline
5. Start API server
6. (Optional) Setup Airflow

## Notes

- No authentication required (local deployment)
- Weekly retraining schedule
- Supports multiple competitions
- Extensible for additional features
- Ready for production with proper deployment setup

---

**Created**: 2025-10-26  
**Author**: Peter Kure  
**Python**: 3.10+  
**Framework**: FastAPI, Airflow  
**Database**: PostgreSQL
