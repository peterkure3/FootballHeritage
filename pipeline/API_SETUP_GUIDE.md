# API Setup Guide

## API Test Results

✅ **Both APIs are working correctly!**

### football-data.org API
- **Status**: Active
- **Available Competitions**: 13
- **Premier League Matches**: 380 available
- **Key**: Valid and working

**Available Competitions:**
- Campeonato Brasileiro Série A (ID: 2013, Code: BSA)
- Championship (ID: 2016, Code: ELC)
- **Premier League (ID: 2021, Code: PL)** ✓
- **UEFA Champions League (ID: 2001, Code: CL)** ✓
- **European Championship (ID: 2018, Code: EC)** ✓

### The Odds API
- **Status**: Active
- **Remaining Requests**: 183/500 (per month)
- **Available Sports**: 71
- **Upcoming EPL Events**: 15

**Key Soccer Leagues Available:**
- EPL (soccer_epl) - 15 upcoming events
- La Liga (soccer_spain_la_liga) - 15 upcoming events
- Bundesliga (soccer_germany_bundesliga)
- Serie A (soccer_italy_serie_a)
- Ligue 1 (soccer_france_ligue_one)
- UEFA Champions League (soccer_uefa_champs_league)
- And 40+ more leagues

## Configuration Updates

Based on the API test results, the following configurations are recommended:

### Recommended Competitions (config.py)

```python
# Use these competition codes - they're available on your tier
TRACKED_COMPETITIONS = [
    "PL",   # Premier League (2021) - 380 matches available
    "CL",   # Champions League (2001)
    "EC",   # European Championship (2018)
]

# Or use IDs directly
TRACKED_COMPETITION_IDS = [
    2021,  # Premier League
    2001,  # Champions League
    2018,  # European Championship
]
```

### Recommended Sports for The Odds API

```python
ODDS_API_SPORTS = [
    "soccer_epl",                  # EPL - 15 events, 19 bookmakers
    "soccer_spain_la_liga",        # La Liga - 15 events, 17 bookmakers
    "soccer_germany_bundesliga",   # Bundesliga
    "soccer_italy_serie_a",        # Serie A
    "soccer_france_ligue_one",     # Ligue 1
    "soccer_uefa_champs_league",   # Champions League
]
```

## Rate Limits

### football-data.org
- **Free Tier**: 10 requests/minute
- **Restrictions**: Limited competitions, no live scores
- **Best Practice**: Cache responses, use date filters

### The Odds API
- **Free Tier**: 500 requests/month
- **Current Usage**: 317 requests remaining
- **Best Practice**: 
  - Fetch odds once per day
  - Focus on 2-3 main leagues
  - Monitor `x-requests-remaining` header

## Running the Pipeline

Now that APIs are verified, you can run the pipeline:

### Option 1: Test API Connection First
```bash
python test_apis.py
```

### Option 2: Run Full Pipeline
```bash
python run_pipeline.py
```

### Option 3: Run Individual Steps
```bash
# 1. Fetch data
python -m etl.fetch_raw_data

# 2. Transform
python -m etl.transform

# 3. Load to DB
python -m etl.load_to_db

# 4. Train model
python -m models.train_model

# 5. Generate predictions
python -m models.predict
```

### Option 4: Start API Server
```bash
python -m api.main
```

## Troubleshooting

### 400 Bad Request
- ✓ **Fixed**: API keys are now loaded from .env file
- ✓ **Fixed**: Proper headers added to requests

### 403 Forbidden
- Some competitions may not be available on free tier
- Use the competitions listed above

### 429 Rate Limit
- **football-data.org**: Wait 1 minute between bursts
- **The Odds API**: You have 183 requests remaining this month
- Consider reducing fetch frequency

## Sample Data Available

### Premier League (PL)
- 380 matches available
- Includes historical and upcoming matches
- Sample: Liverpool FC vs AFC Bournemouth (2025-08-15)

### The Odds API (EPL)
- 15 upcoming events
- 19 bookmakers per event
- Sample: Arsenal vs Crystal Palace (2025-10-26)
- Odds format: Decimal

## Next Steps

1. ✅ API keys validated
2. ✅ Data sources confirmed
3. ✅ Rate limits checked
4. ⏭️ Run pipeline: `python run_pipeline.py`
5. ⏭️ Start API: `python -m api.main`
6. ⏭️ Access docs: http://localhost:8000/docs

## API Documentation Links

- **football-data.org**: https://www.football-data.org/documentation/quickstart
- **The Odds API**: https://the-odds-api.com/liveapi/guides/v4

## Notes

- Both APIs are working perfectly with your keys
- You have sufficient data to train the model (380+ matches)
- The Odds API has good coverage with 19 bookmakers
- Consider setting up Airflow for weekly automated runs
- Monitor your API usage to stay within free tier limits
