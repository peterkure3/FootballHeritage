# Sports Betting Prediction Pipeline and API

Production-ready pipeline for football and NCAA basketball predictions using XGBoost, with FastAPI REST API and Airflow orchestration.

## Features

- **Multi-Sport Support**: Football (soccer) and NCAA Basketball (Men's & Women's)
- **Data Ingestion**: Fetch data from football-data.org, The Odds API, and NCAA API
- **ETL Pipeline**: Transform and load data into PostgreSQL
- **ML Models**: XGBoost classifiers for match outcome predictions
  - Football: 3-class (win/draw/loss)
  - Basketball: 2-class (win/loss)
- **REST API**: FastAPI endpoints for predictions and match data
- **Orchestration**: Airflow DAG for weekly automated runs
- **Feature Engineering**: Team form, score differentials, odds spreads

## Architecture

```
sports-betting-pipeline/
├── data/
│   ├── raw/              # Raw JSON/CSV data
│   ├── interim/          # Intermediate processing
│   └── processed/        # Parquet files
├── etl/
│   ├── fetch_raw_data.py # API data fetching
│   ├── transform.py      # Feature engineering
│   ├── load_to_db.py     # Database loading
│   └── utils.py          # Shared utilities
├── models/
│   ├── train_model.py    # Model training
│   ├── predict.py        # Prediction generation
│   ├── evaluate.py       # Model evaluation
│   └── model_store/      # Saved models
├── api/
│   ├── main.py           # FastAPI app
│   └── routes.py         # API endpoints
├── dags/
│   └── betting_pipeline.py # Airflow DAG
├── config.py             # Configuration
├── schema.sql            # Database schema
└── requirements.txt      # Dependencies
```

## Prerequisites

- Python 3.10+
- PostgreSQL 12+
- Apache Airflow (optional, for orchestration)

## Setup

### 1. Install Dependencies

```bash
cd sports-betting-pipeline
pip install -r requirements.txt
```

### 2. Configure Environment

Set environment variables or edit `config.py`:

```bash
# API Keys
export FOOTBALL_DATA_ORG_API_KEY="your_key_here"
export THE_ODDS_API_KEY="your_key_here"

# Database
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_NAME="football_betting"
export DB_USER="postgres"
export DB_PASSWORD="your_password"
```

### 3. Create Database

```bash
# Create database
psql -U postgres -c "CREATE DATABASE football_betting;"

# Run schema
psql -U postgres -d football_betting -f schema.sql
```

### 4. Initialize Airflow (Optional)

```bash
# Set Airflow home
export AIRFLOW_HOME=$(pwd)/airflow

# Initialize database
airflow db init

# Create admin user
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com

# Copy DAG
cp dags/betting_pipeline.py $AIRFLOW_HOME/dags/
```

## Usage

### Manual Pipeline Execution

Run each step individually:

```bash
# 1. Fetch raw data
python -m etl.fetch_raw_data

# 2. Transform data
python -m etl.transform

# 3. Load to database
python -m etl.load_to_db

# 4. Train model
python -m models.train_model

# 5. Generate predictions
python -m models.predict

# 6. Evaluate model (optional)
python -m models.evaluate
```

### Run API Server

```bash
# Start FastAPI server
python -m api.main

# Or with uvicorn directly
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

API will be available at:
- **Docs**: http://localhost:8000/docs
- **Root**: http://localhost:8000/

### Airflow Orchestration

```bash
# Start Airflow scheduler
airflow scheduler

# Start Airflow webserver (in another terminal)
airflow webserver --port 8080

# Access UI at http://localhost:8080
# Enable the 'football_betting_pipeline' DAG
```

## API Endpoints

### GET /api/v1/predictions/{match_id}

Get prediction for a specific match.

**Response:**
```json
{
  "match_id": 12345,
  "winner": "home_win",
  "home_prob": 0.65,
  "draw_prob": 0.20,
  "away_prob": 0.15,
  "model_version": "1.0.0",
  "created_at": "2025-10-26T12:00:00"
}
```

### GET /api/v1/matches

Get matches with odds (filterable).

**Query Parameters:**
- `competition` (optional): Filter by competition name
- `date` (optional): Filter by date (YYYY-MM-DD)
- `limit` (optional): Max results (default: 100)

**Response:**
```json
[
  {
    "match_id": 12345,
    "competition": "Premier League",
    "date": "2025-10-27T15:00:00",
    "home_team": "Arsenal",
    "away_team": "Chelsea",
    "home_score": null,
    "away_score": null,
    "status": "SCHEDULED",
    "home_win_odds": 2.10,
    "draw_odds": 3.40,
    "away_win_odds": 3.50
  }
]
```

### GET /api/v1/health

Check API and pipeline health.

**Response:**
```json
{
  "status": "healthy",
  "last_pipeline_run": "2025-10-26T10:00:00",
  "database_connected": true
}
```

## Configuration

Edit `config.py` to customize:

- **API Keys**: football-data.org, The Odds API
- **Database**: Connection URI
- **Competitions**: Tracked leagues (PL, PD, BL1, SA, FL1, CL)
- **Model**: XGBoost hyperparameters
- **Features**: Team form window (default: 5 matches)
- **Schedule**: Airflow DAG schedule (default: weekly)

## Data Sources

### football-data.org
- **Endpoint**: https://api.football-data.org/v4
- **Data**: Matches, competitions, scores
- **Format**: JSON
- **Rate Limit**: Check API documentation

### The Odds API
- **Endpoint**: https://api.the-odds-api.com/v4
- **Data**: Pre-match odds, scores
- **Format**: JSON
- **Rate Limit**: Check API documentation

### Historical CSVs
Place historical match data in `data/raw/historical/` as CSV files.

## Model Features

The XGBoost model uses the following features:

1. **Team Form** (last 5 matches):
   - Wins, draws, losses for home/away teams
   
2. **Goal Difference**:
   - Average goal difference over last 5 matches
   
3. **Odds Data**:
   - Home win, draw, away win odds
   - Odds spread (home_win - away_win)

## Database Schema

### Tables

- **matches**: Match details, scores, statistics
- **odds**: Bookmaker odds for matches
- **predictions**: Model predictions with probabilities

See `schema.sql` for full schema definition.

## Logging

All scripts use JSON-structured logging:

```json
{
  "timestamp": "2025-10-26T12:00:00",
  "module": "etl.fetch_raw_data",
  "level": "INFO",
  "message": "Fetched 25 matches"
}
```

## Error Handling

- **API Retries**: Exponential backoff (3 attempts)
- **Database**: Transactional writes with rollback
- **Idempotency**: Upsert operations for matches
- **Validation**: Data type checks and constraints

## Troubleshooting

### Database Connection Issues

```bash
# Test PostgreSQL connection
psql -U postgres -d football_betting -c "SELECT 1;"

# Check DATABASE_URI in config.py
```

### API Key Errors

```bash
# Verify API keys are set
echo $FOOTBALL_DATA_ORG_API_KEY
echo $THE_ODDS_API_KEY

# Test API endpoints manually
curl -H "X-Auth-Token: YOUR_KEY" https://api.football-data.org/v4/competitions
```

### Model Training Fails

- Ensure sufficient data (minimum 100 matches with results)
- Check processed data exists: `ls data/processed/`
- Verify feature columns match in transform.py

### Airflow DAG Not Showing

```bash
# Check DAG file location
ls $AIRFLOW_HOME/dags/

# Check for syntax errors
python dags/betting_pipeline.py

# Refresh DAGs in UI or restart scheduler
```

## Development

### Running Tests

```bash
# Add tests in tests/ directory
pytest tests/
```

### Code Style

```bash
# Format code
black .

# Lint
flake8 .
```

## Production Deployment

1. **Use environment variables** for all secrets
2. **Set up monitoring** for API and pipeline
3. **Configure backups** for PostgreSQL
4. **Use reverse proxy** (nginx) for API
5. **Set up logging aggregation** (ELK stack)
6. **Schedule regular model retraining** via Airflow
7. **Implement rate limiting** for API endpoints

## License

MIT License

## Support

For issues and questions, please open an issue on the repository.

## Roadmap

- [ ] Add more leagues and competitions
- [ ] Implement ensemble models
- [ ] Add real-time odds tracking
- [ ] Create web dashboard
- [ ] Add betting strategy backtesting
- [ ] Implement A/B testing for models
