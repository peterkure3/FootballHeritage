"""
Configuration file for football betting pipeline.
Contains API keys, database URIs, file paths, and other settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
MODEL_DIR = BASE_DIR / "models" / "model_store"

# API Configuration
FOOTBALL_DATA_ORG_API_KEY = os.getenv("FOOTBALL_DATA_ORG_API_KEY", "YOUR_FOOTBALL_DATA_ORG_API_KEY")
FOOTBALL_DATA_ORG_BASE_URL = "https://api.football-data.org/v4"

THE_ODDS_API_KEY = os.getenv("THE_ODDS_API_KEY", "YOUR_THE_ODDS_API_KEY")
THE_ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4"

# NCAA API Configuration
NCAA_API_BASE_URL = "https://ncaa-api.henrygd.me"
NCAA_RATE_LIMIT = 5  # requests per second

# API Request Configuration
API_TIMEOUT = 30  # seconds
API_RETRY_ATTEMPTS = 3
API_RETRY_BACKOFF_FACTOR = 2  # exponential backoff multiplier

# Database Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "football_betting")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "YOUR_DB_PASSWORD")

DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Data Source Paths
FOOTBALL_DATA_ORG_DIR = RAW_DATA_DIR / "football_data_org"
THE_ODDS_API_DIR = RAW_DATA_DIR / "the_odds_api"
NCAA_API_DIR = RAW_DATA_DIR / "ncaa_api"
HISTORICAL_CSV_DIR = RAW_DATA_DIR / "historical"

# Model Configuration
MODEL_VERSION = "1.0.0"
MODEL_NAME = f"model_v{MODEL_VERSION}.pkl"
MODEL_PATH = MODEL_DIR / MODEL_NAME

# XGBoost Hyperparameters
XGBOOST_PARAMS = {
    "objective": "multi:softprob",
    "num_class": 3,  # home win, draw, away win
    "max_depth": 6,
    "learning_rate": 0.1,
    "n_estimators": 100,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42,
    "n_jobs": -1,
}

# Feature Engineering
TEAM_FORM_WINDOW = 5  # last N matches for form calculation
MIN_MATCHES_FOR_TRAINING = 100  # minimum matches required to train model

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "json"  # json or text

# Airflow Configuration
AIRFLOW_DAG_SCHEDULE = "0 0 * * 0"  # Weekly on Sunday at midnight
AIRFLOW_DAG_CATCHUP = False

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "5555"))  # Changed from 8000 to 5555
API_TITLE = "Football Betting Predictions API"
API_VERSION = "1.0.0"
API_DESCRIPTION = "REST API for football match predictions and betting data"

# Competitions to track (football-data.org competition codes)
# Note: Free tier may have limited access to some competitions
# Using competition IDs instead of codes for better compatibility
TRACKED_COMPETITIONS = [
    "PL",    # Premier League (2021)
    "CL",    # Champions League (2001)
    "WC",    # World Cup (2000)
    "EC",    # European Championship (2018)
]

# Alternative: Use competition IDs directly
TRACKED_COMPETITION_IDS = [
    2021,  # Premier League
    2001,  # Champions League  
    2000,  # FIFA World Cup
    2018,  # European Championship
]

# The Odds API sports and markets
# Available sports: soccer_epl, soccer_spain_la_liga, soccer_germany_bundesliga, etc.
ODDS_API_SPORTS = [
    "soccer_epl",              # English Premier League
    "soccer_spain_la_liga",    # La Liga
    "soccer_germany_bundesliga", # Bundesliga
    "soccer_italy_serie_a",    # Serie A
    "soccer_france_ligue_one", # Ligue 1
]
ODDS_API_SPORT = "soccer_epl"  # Default sport
ODDS_API_REGIONS = "uk,us,eu"
ODDS_API_MARKETS = "h2h"  # head-to-head (match winner)
ODDS_API_ODDS_FORMAT = "decimal"

# NCAA Basketball Configuration
NCAA_SPORTS = {
    "basketball-men": {
        "name": "Men's Basketball",
        "division": "d1",  # Division I
        "season_start_month": 11,  # November
        "season_end_month": 4,  # April (March Madness)
    },
    "basketball-women": {
        "name": "Women's Basketball",
        "division": "d1",  # Division I
        "season_start_month": 11,  # November
        "season_end_month": 4,  # April
    },
}

# Sport-specific model configurations
SPORT_CONFIGS = {
    "football": {
        "num_classes": 3,  # home win, draw, away win
        "has_draw": True,
        "form_window": 5,
    },
    "basketball": {
        "num_classes": 2,  # home win, away win (no draws)
        "has_draw": False,
        "form_window": 10,  # Basketball teams play more games
    },
}

# File naming conventions
MATCHES_PARQUET_TEMPLATE = "matches_{sport}_{date}.parquet"
ODDS_PARQUET_TEMPLATE = "odds_{sport}_{date}.parquet"
