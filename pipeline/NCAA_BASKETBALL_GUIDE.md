# NCAA Basketball Integration Guide

## Overview

The pipeline now supports NCAA Division I Men's and Women's Basketball alongside football predictions. This guide covers how to fetch, process, and predict NCAA basketball games.

## Features

✅ **Men's Basketball** (NCAA Division I)  
✅ **Women's Basketball** (NCAA Division I)  
✅ **No-draw predictions** (basketball has only win/loss outcomes)  
✅ **Extended form window** (10 games vs 5 for football)  
✅ **Rate-limited API** (5 requests/second)  
✅ **Season-aware** (November - April)

## NCAA API

The pipeline uses the free NCAA API: https://ncaa-api.henrygd.me

- **No API key required** ✅
- **Rate limit**: 5 requests per second
- **Data**: Scores, schedules, team info, game details
- **Coverage**: All NCAA sports, focused on basketball

### Available Endpoints

```
GET /scoreboard/{sport}/{division}/{date}/all-conf
GET /game/{game_id}
GET /team/{team_slug}
GET /schools-index
```

## Quick Start

### 1. Fetch NCAA Basketball Data

```bash
# Fetch both men's and women's basketball (last 30 days)
python -m etl.fetch_ncaa_data

# Fetch only men's basketball
python -m etl.fetch_ncaa_data --sport basketball-men --days 60

# Fetch only women's basketball
python -m etl.fetch_ncaa_data --sport basketball-women --days 60
```

### 2. Transform Data

```bash
# Transform both sports
python -m etl.transform_ncaa

# Transform specific sport
python -m etl.transform_ncaa --sport basketball-men
```

### 3. Load to Database

```bash
# Load NCAA data (will be added to existing matches table)
python -m etl.load_to_db
```

### 4. Train Basketball Model

```bash
# Train separate model for basketball
python -m models.train_basketball_model
```

### 5. Generate Predictions

```bash
# Get predictions for upcoming NCAA games
python -m models.predict --sport basketball
```

## Configuration

### config.py

```python
# NCAA API Configuration
NCAA_API_BASE_URL = "https://ncaa-api.henrygd.me"
NCAA_RATE_LIMIT = 5  # requests per second

# NCAA Sports
NCAA_SPORTS = {
    "basketball-men": {
        "name": "Men's Basketball",
        "division": "d1",
        "season_start_month": 11,  # November
        "season_end_month": 4,     # April
    },
    "basketball-women": {
        "name": "Women's Basketball",
        "division": "d1",
        "season_start_month": 11,
        "season_end_month": 4,
    },
}

# Sport-specific configurations
SPORT_CONFIGS = {
    "football": {
        "num_classes": 3,  # home win, draw, away win
        "has_draw": True,
        "form_window": 5,
    },
    "basketball": {
        "num_classes": 2,  # home win, away win (no draws)
        "has_draw": False,
        "form_window": 10,  # More games in basketball season
    },
}
```

## Data Structure

### Raw Data Location

```
data/
└── raw/
    └── ncaa_api/
        ├── basketball-men/
        │   └── scoreboard_20251030_143000.json
        └── basketball-women/
            └── scoreboard_20251030_143000.json
```

### Processed Data

```
data/
└── processed/
    ├── matches_ncaa_basketball-men_20251030.parquet
    └── matches_ncaa_basketball-women_20251030.parquet
```

## Features Engineered

### Basketball-Specific Features

1. **Team Form** (last 10 games)
   - Wins
   - Losses
   - Average score
   - Average score differential

2. **No Draw Handling**
   - Binary classification (home win / away win)
   - Adjusted model architecture

3. **Season Context**
   - Regular season vs tournament games
   - Conference games

## Database Schema

The `matches` table now includes a `sport_type` column:

```sql
CREATE TABLE matches (
    match_id INTEGER PRIMARY KEY,
    sport_type TEXT DEFAULT 'football' CHECK (sport_type IN ('football', 'basketball')),
    -- ... other columns
);
```

Basketball games have:
- `sport_type = 'basketball'`
- `result IN ('home_win', 'away_win')` (no 'draw')
- Additional form features for 10-game window

## Model Training

### Basketball Model Differences

```python
# Basketball uses binary classification
XGBOOST_PARAMS_BASKETBALL = {
    "objective": "binary:logistic",  # vs multi:softprob for football
    "num_class": 2,                  # vs 3 for football
    "max_depth": 6,
    "learning_rate": 0.1,
    "n_estimators": 150,             # More trees for basketball
    "subsample": 0.8,
    "colsample_bytree": 0.8,
}
```

### Training Command

```bash
# Train basketball model separately
python -m models.train_basketball_model --sport basketball-men
python -m models.train_basketball_model --sport basketball-women
```

## API Endpoints

### Get Basketball Predictions

```bash
# Get predictions for specific game
curl http://localhost:5555/api/v1/predictions/basketball/12345

# Get upcoming basketball games
curl http://localhost:5555/api/v1/matches?sport=basketball&limit=20
```

### Response Format

```json
{
  "match_id": 12345,
  "sport_type": "basketball",
  "winner": "home_win",
  "home_prob": 0.68,
  "away_prob": 0.32,
  "model_version": "1.0.0_basketball",
  "created_at": "2025-10-30T14:00:00"
}
```

## Full Pipeline Example

```bash
# Complete NCAA basketball pipeline
cd pipeline

# 1. Fetch data (last 60 days)
python -m etl.fetch_ncaa_data --days 60

# 2. Transform data
python -m etl.transform_ncaa

# 3. Load to database
python -m etl.load_to_db

# 4. Train models
python -m models.train_basketball_model --sport basketball-men
python -m models.train_basketball_model --sport basketball-women

# 5. Generate predictions
python -m models.predict --sport basketball

# 6. Start API
python -m api.main
```

## Season Schedule

### Men's Basketball
- **Regular Season**: November - March
- **Conference Tournaments**: March
- **March Madness**: March - April
- **Peak betting period**: January - March

### Women's Basketball
- **Regular Season**: November - March
- **Conference Tournaments**: March
- **NCAA Tournament**: March - April
- **Peak betting period**: January - March

## Best Practices

### 1. Data Freshness
```bash
# Fetch daily during season
python -m etl.fetch_ncaa_data --days 7
```

### 2. Rate Limiting
The fetcher automatically enforces 5 req/sec limit. For large date ranges, expect:
- 30 days = ~30 requests = ~6 seconds
- 60 days = ~60 requests = ~12 seconds

### 3. Model Retraining
```bash
# Retrain weekly during season
python -m models.train_basketball_model --sport basketball-men
```

### 4. Separate Models
Keep separate models for:
- Men's basketball
- Women's basketball
- Football

Different dynamics require different models.

## Troubleshooting

### No Games Found

```bash
# Check if it's basketball season (Nov-Apr)
# Try increasing date range
python -m etl.fetch_ncaa_data --days 90
```

### Rate Limit Errors

The fetcher handles rate limiting automatically. If you see errors:
- Wait 1 minute
- Retry the fetch

### Empty Predictions

Ensure you have:
1. ✅ Fetched recent data
2. ✅ Transformed the data
3. ✅ Loaded to database
4. ✅ Trained basketball model
5. ✅ Upcoming games in database

## Integration with Existing Pipeline

### Mixed Sport Predictions

```bash
# Get all predictions (football + basketball)
curl http://localhost:5555/api/v1/predictions?limit=50

# Filter by sport
curl http://localhost:5555/api/v1/predictions?sport=basketball
curl http://localhost:5555/api/v1/predictions?sport=football
```

### Database Queries

```sql
-- Get all basketball games
SELECT * FROM matches WHERE sport_type = 'basketball';

-- Get basketball predictions
SELECT p.*, m.home_team, m.away_team, m.date
FROM predictions p
JOIN matches m ON p.match_id = m.match_id
WHERE m.sport_type = 'basketball'
ORDER BY m.date DESC;

-- Compare football vs basketball accuracy
SELECT 
    m.sport_type,
    COUNT(*) as total_predictions,
    AVG(CASE WHEN p.winner = m.result THEN 1.0 ELSE 0.0 END) as accuracy
FROM predictions p
JOIN matches m ON p.match_id = m.match_id
WHERE m.result IS NOT NULL
GROUP BY m.sport_type;
```

## Resources

- **NCAA API Docs**: https://github.com/henrygd/ncaa-api
- **NCAA.com**: https://www.ncaa.com/
- **Basketball Reference**: https://www.sports-reference.com/cbb/

## Next Steps

1. ✅ Fetch NCAA data
2. ✅ Transform and load
3. ✅ Train basketball models
4. ⏳ Add odds data (The Odds API supports NCAA basketball)
5. ⏳ Implement tournament bracket predictions
6. ⏳ Add player statistics
7. ⏳ Conference-specific models

---

**Status**: NCAA Basketball Integration Complete ✅  
**Last Updated**: October 30, 2025  
**Supported Sports**: Football, Men's Basketball, Women's Basketball
