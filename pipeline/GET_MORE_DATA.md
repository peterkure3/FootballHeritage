# How to Get More Data

## Quick Start - Get Data Now

### Option 1: Download Free Historical Data (Recommended)
```bash
python download_sample_data.py
```

This downloads **real historical match data** from football-data.co.uk:
- ✅ **FREE** - No API limits
- ✅ **5 seasons** of data (2019-2024)
- ✅ **5 major leagues** (EPL, La Liga, Bundesliga, Serie A, Ligue 1)
- ✅ **~10,000+ matches** with results and odds
- ✅ Automatically normalized to our schema

### Option 2: Fetch More from APIs
```bash
python fetch_more_data.py
```

This fetches **historical data from your APIs**:
- ✅ Last 12 months of matches
- ✅ Multiple competitions
- ✅ Current odds for all configured sports
- ⚠️ Uses API quota (monitor limits)

### Option 3: Both (Maximum Data)
```bash
# First download free data
python download_sample_data.py

# Then fetch from APIs
python fetch_more_data.py

# Then process everything
python -m etl.transform
python -m etl.load_to_db
python -m models.train_model
```

## Data Sources

### 1. football-data.co.uk (FREE)
**Best for**: Historical training data

- **URL**: https://www.football-data.co.uk/data.php
- **Cost**: FREE
- **Coverage**: 20+ years of historical data
- **Leagues**: 50+ leagues worldwide
- **Includes**: Results, odds, statistics
- **Format**: CSV files

**What you get**:
- Premier League: ~380 matches/season
- La Liga: ~380 matches/season
- Bundesliga: ~306 matches/season
- Serie A: ~380 matches/season
- Ligue 1: ~380 matches/season

**Total**: ~10,000+ matches over 5 seasons

### 2. football-data.org API
**Best for**: Live/recent matches

- **Your Tier**: Free
- **Limit**: 10 requests/minute
- **Coverage**: 13 competitions
- **Current Data**: 380 Premier League matches available

**Available Competitions**:
- Premier League (ID: 2021)
- Champions League (ID: 2001)
- European Championship (ID: 2018)
- And 10 more

### 3. The Odds API
**Best for**: Current betting odds

- **Your Tier**: Free
- **Limit**: 500 requests/month
- **Remaining**: 183 requests
- **Coverage**: 71 sports/leagues
- **Current Events**: 15 EPL matches with 19 bookmakers

## Recommended Workflow

### For Training (Need Lots of Data)

```bash
# Step 1: Download free historical data
python download_sample_data.py
# Choose option 1 (Download real data)

# Step 2: Transform and load
python -m etl.transform
python -m etl.load_to_db

# Step 3: Train model
python -m models.train_model

# You now have a model trained on 10,000+ matches!
```

### For Production (Keep Data Fresh)

```bash
# Weekly: Fetch latest matches and odds
python fetch_more_data.py

# Process new data
python -m etl.transform
python -m etl.load_to_db

# Retrain model
python -m models.train_model

# Generate predictions
python -m models.predict
```

## Data Volume Estimates

### Current Situation
- football-data.org: 380 matches
- The Odds API: 15 current events
- **Total**: ~400 matches

### After download_sample_data.py
- Historical CSV: ~10,000 matches
- API data: 380 matches
- **Total**: ~10,400 matches ✅

### After fetch_more_data.py
- Historical: ~10,000 matches
- Last 12 months: ~2,000 matches
- Current odds: 50+ events
- **Total**: ~12,000+ matches ✅

## Managing API Limits

### football-data.org
**Limit**: 10 requests/minute

**Strategy**:
- Fetch once per day
- Use date filters to get specific periods
- Cache responses locally
- Focus on 2-3 main competitions

**Example**:
```python
# Fetch last 30 days only
date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
date_to = datetime.now().strftime("%Y-%m-%d")
```

### The Odds API
**Limit**: 500 requests/month (183 remaining)

**Strategy**:
- Fetch odds once per day (~30 requests/month)
- Focus on 2-3 main leagues
- Use historical CSV for training data
- Save API calls for live predictions

**Budget**:
- Daily odds fetch: 3 sports × 30 days = 90 requests/month
- Leaves 410 requests for ad-hoc queries

## File Locations

After running data scripts:

```
data/
├── raw/
│   ├── football_data_org/
│   │   ├── all_competitions_*.json
│   │   ├── matches_2021_Premier_League_*.json
│   │   └── matches_2001_Champions_League_*.json
│   ├── the_odds_api/
│   │   ├── odds_soccer_epl_*.json
│   │   └── odds_soccer_spain_la_liga_*.json
│   └── historical/
│       ├── Premier_League_2324.csv
│       ├── La_Liga_2324.csv
│       ├── normalized_Premier_League_2324.csv
│       └── ... (25+ CSV files)
└── processed/
    ├── matches_2025-10-26.parquet
    └── odds_2025-10-26.parquet
```

## Troubleshooting

### "Not enough data to train model"
**Solution**: Run `python download_sample_data.py`

Minimum required: 100 matches
After download: 10,000+ matches ✅

### "API rate limit exceeded"
**Solution**: Use historical CSV data instead

```bash
# Skip API fetch, use CSV only
python download_sample_data.py
python -m etl.transform
python -m etl.load_to_db
```

### "No CSV files found"
**Solution**: Check internet connection and retry

```bash
# Try manual download
# Visit: https://www.football-data.co.uk/englandm.php
# Download CSV files to data/raw/historical/
```

### "Pandas installation failed"
**Solution**: Use pre-built wheels

```bash
# Install pandas separately
pip install --upgrade pip
pip install pandas --prefer-binary

# Then install rest
pip install -r requirements.txt
```

## Data Quality

### Historical CSV Data
- ✅ Complete match results
- ✅ Betting odds from multiple bookmakers
- ✅ 5+ years of history
- ✅ Verified and cleaned
- ⚠️ No live updates (use APIs for that)

### API Data
- ✅ Live/recent matches
- ✅ Current odds
- ✅ Multiple bookmakers
- ⚠️ Limited by API tier
- ⚠️ Rate limits apply

## Next Steps

1. **Get Data**:
   ```bash
   python download_sample_data.py
   ```

2. **Process Data**:
   ```bash
   python -m etl.transform
   python -m etl.load_to_db
   ```

3. **Train Model**:
   ```bash
   python -m models.train_model
   ```

4. **Generate Predictions**:
   ```bash
   python -m models.predict
   ```

5. **Start API**:
   ```bash
   python -m api.main
   ```

## Summary

| Data Source | Cost | Volume | Best For |
|------------|------|--------|----------|
| football-data.co.uk | FREE | 10,000+ | Training |
| football-data.org API | FREE | 380+ | Recent matches |
| The Odds API | FREE | 50+ | Live odds |

**Recommended**: Start with `download_sample_data.py` for instant access to 10,000+ matches!
