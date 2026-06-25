# Quick Start Guide

Get the football betting pipeline running in 5 minutes.

## Prerequisites

- Python 3.10+
- PostgreSQL installed and running
- API keys (optional for testing with sample data)

## Step 1: Install Dependencies

```bash
cd sports-betting-pipeline
pip install -r requirements.txt
```

## Step 2: Setup Database

```bash
# Create database
psql -U postgres -c "CREATE DATABASE football_betting;"

# Create tables
psql -U postgres -d football_betting -f schema.sql
```

## Step 3: Configure

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
# Minimum required: DB_PASSWORD
```

## Step 4: Run Pipeline

### Option A: Full Pipeline (Recommended for first run)

```bash
python run_pipeline.py
```

This runs all steps: fetch → transform → load → train → predict

### Option B: Individual Steps

```bash
# 1. Fetch data
python -m etl.fetch_raw_data

# 2. Transform
python -m etl.transform

# 3. Load to DB
python -m etl.load_to_db

# 4. Train model
python -m models.train_model

# 5. Predict
python -m models.predict
```

## Step 5: Start API

```bash
python -m api.main
```

Visit http://localhost:8000/docs for interactive API documentation.

## Test the API

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Get matches
curl http://localhost:8000/api/v1/matches?limit=10

# Get prediction (replace 12345 with actual match_id)
curl http://localhost:8000/api/v1/predictions/12345
```

## Next Steps

1. **Add API Keys**: Get keys from [football-data.org](https://www.football-data.org/) and [The Odds API](https://the-odds-api.com/)
2. **Add Historical Data**: Place CSV files in `data/raw/historical/`
3. **Setup Airflow**: For automated weekly runs (see README.md)
4. **Customize**: Edit `config.py` for your leagues and parameters

## Troubleshooting

### "No data found"
- Add API keys to fetch live data, or
- Place sample CSV files in `data/raw/historical/`

### "Database connection failed"
- Check PostgreSQL is running: `pg_isready`
- Verify credentials in `.env`

### "Model training failed"
- Ensure at least 100 matches with results in database
- Check `data/processed/` has parquet files

## Sample Data Structure

If using CSV files, format them like this:

```csv
match_id,home_team,away_team,home_score,away_score,date,competition,status,result
1,Arsenal,Chelsea,2,1,2025-01-15,Premier League,FINISHED,home_win
2,Liverpool,Man City,1,1,2025-01-15,Premier League,FINISHED,draw
```

## Support

See full documentation in README.md or open an issue.
