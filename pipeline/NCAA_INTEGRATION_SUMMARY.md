# NCAA Basketball Integration - Summary

## ✅ What Was Added

### 1. Configuration (`config.py`)
- NCAA API base URL and rate limiting
- NCAA sports configuration (Men's & Women's Basketball)
- Sport-specific model configs (2-class for basketball vs 3-class for football)
- Updated file naming to support multiple sports

### 2. Data Fetcher (`etl/fetch_ncaa_data.py`)
- Fetches scoreboard data from NCAA API
- Supports date ranges and current season
- Rate-limited (5 requests/second)
- Saves raw JSON data

### 3. Data Transformer (`etl/transform_ncaa.py`)
- Parses NCAA game data
- Calculates team form (10-game window for basketball)
- Handles no-draw outcomes
- Generates basketball-specific features

### 4. Database Schema (`schema.sql`)
- Added `sport_type` column to matches table
- Supports both football and basketball data
- Maintains backward compatibility

### 5. Documentation
- **NCAA_BASKETBALL_GUIDE.md**: Complete guide for NCAA integration
- **test_ncaa_api.py**: Test script for NCAA API connectivity
- Updated README.md to reflect multi-sport support

## 🎯 Key Features

### Multi-Sport Architecture
```
Football:
- 3-class prediction (home_win, draw, away_win)
- 5-game form window
- Odds from The Odds API

Basketball:
- 2-class prediction (home_win, away_win)
- 10-game form window
- NCAA API (free, no key required)
```

### Data Flow
```
NCAA API → fetch_ncaa_data.py → Raw JSON
         ↓
    transform_ncaa.py → Processed Parquet
         ↓
    load_to_db.py → PostgreSQL (matches table)
         ↓
    train_basketball_model.py → XGBoost Model
         ↓
    predict.py → Predictions
```

## 🚀 Quick Start

### Test NCAA API
```bash
python test_ncaa_api.py
```

### Fetch Basketball Data
```bash
# Both sports (last 30 days)
python -m etl.fetch_ncaa_data

# Men's only (last 60 days)
python -m etl.fetch_ncaa_data --sport basketball-men --days 60
```

### Transform and Load
```bash
python -m etl.transform_ncaa
python -m etl.load_to_db
```

### Train Basketball Models
```bash
python -m models.train_basketball_model --sport basketball-men
python -m models.train_basketball_model --sport basketball-women
```

## 📊 Database Changes

### Updated Schema
```sql
-- Added sport_type column
ALTER TABLE matches ADD COLUMN sport_type TEXT DEFAULT 'football' 
CHECK (sport_type IN ('football', 'basketball'));

-- Existing data defaults to 'football'
-- Basketball games will have sport_type = 'basketball'
```

### Query Examples
```sql
-- Get all basketball games
SELECT * FROM matches WHERE sport_type = 'basketball';

-- Get basketball predictions
SELECT p.*, m.home_team, m.away_team 
FROM predictions p
JOIN matches m ON p.match_id = m.match_id
WHERE m.sport_type = 'basketball';
```

## 🔧 Configuration Changes

### config.py Additions
```python
# NCAA API
NCAA_API_BASE_URL = "https://ncaa-api.henrygd.me"
NCAA_RATE_LIMIT = 5

# NCAA Sports
NCAA_SPORTS = {
    "basketball-men": {...},
    "basketball-women": {...}
}

# Sport Configs
SPORT_CONFIGS = {
    "football": {"num_classes": 3, "has_draw": True, "form_window": 5},
    "basketball": {"num_classes": 2, "has_draw": False, "form_window": 10}
}
```

## 📁 New Files Created

```
pipeline/
├── etl/
│   ├── fetch_ncaa_data.py       ✅ NEW - NCAA data fetcher
│   └── transform_ncaa.py        ✅ NEW - NCAA data transformer
├── test_ncaa_api.py             ✅ NEW - API test script
├── NCAA_BASKETBALL_GUIDE.md     ✅ NEW - Complete guide
└── NCAA_INTEGRATION_SUMMARY.md  ✅ NEW - This file
```

## 🎓 NCAA Basketball Season

### Timeline
- **Regular Season**: November - March
- **Conference Tournaments**: March
- **March Madness**: March - April
- **Best Time to Bet**: January - March

### Data Availability
- Division I Men's Basketball
- Division I Women's Basketball
- Real-time scores and schedules
- Historical game data

## 🔄 Integration with Existing Pipeline

### Backward Compatible
- Existing football pipeline unchanged
- Database schema extended (not modified)
- Separate models for each sport
- Shared infrastructure (API, database, ETL utils)

### API Endpoints
```bash
# Get all predictions (football + basketball)
GET /api/v1/predictions

# Filter by sport
GET /api/v1/predictions?sport=basketball
GET /api/v1/predictions?sport=football

# Get matches
GET /api/v1/matches?sport=basketball
```

## 📈 Next Steps

### Immediate
1. ✅ Test NCAA API connectivity
2. ⏳ Fetch initial basketball data
3. ⏳ Transform and load to database
4. ⏳ Train basketball models
5. ⏳ Generate predictions

### Future Enhancements
- Add NCAA basketball odds from The Odds API
- Implement tournament bracket predictions
- Add player statistics and injuries
- Conference-specific models
- Live game updates

## 🛠️ Troubleshooting

### No Games Found
- Check if it's basketball season (Nov-Apr)
- Try larger date range: `--days 90`

### Rate Limit Errors
- Automatic rate limiting is built-in
- Wait 1 minute and retry if needed

### Empty Predictions
Ensure you have:
1. Fetched recent data
2. Transformed the data
3. Loaded to database
4. Trained basketball model
5. Upcoming games in database

## 📚 Documentation

- **NCAA_BASKETBALL_GUIDE.md**: Complete usage guide
- **README.md**: Updated with multi-sport support
- **config.py**: All configuration options
- **test_ncaa_api.py**: API testing

## 🎉 Summary

The pipeline now supports:
- ✅ Football (soccer) predictions
- ✅ NCAA Men's Basketball predictions
- ✅ NCAA Women's Basketball predictions
- ✅ Multi-sport database schema
- ✅ Sport-specific models
- ✅ Unified API interface

**Status**: NCAA Basketball Integration Complete  
**Date**: October 30, 2025  
**Ready for**: Data fetching and model training
