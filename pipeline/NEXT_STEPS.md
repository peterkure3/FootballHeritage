# Next Steps - Get More Data & Train Model

## 🎯 Current Status

✅ API server is running  
✅ Database is set up  
✅ APIs are working  
⚠️ Need more data for training

## 🚀 Quick Solution - Get 10,000+ Matches Now!

### Step 1: Download Historical Data (2 minutes)

```bash
python download_sample_data.py
```

When prompted, choose option **1** (Download real data)

This will download:
- ✅ 5 seasons of data (2019-2024)
- ✅ 5 major leagues (EPL, La Liga, Bundesliga, Serie A, Ligue 1)
- ✅ ~10,000+ matches with results and betting odds
- ✅ FREE - No API limits

### Step 2: Process the Data (1 minute)

```bash
python -m etl.transform
python -m etl.load_to_db
```

### Step 3: Train the Model (1 minute)

```bash
python -m models.train_model
```

### Step 4: Generate Predictions

```bash
python -m models.predict
```

### Step 5: Test the API

Your API is already running! Visit:
- **Interactive Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health
- **Matches**: http://localhost:8000/api/v1/matches

## 📊 Data Options

### Option A: Quick Start (Recommended)
**Best for**: Getting started immediately

```bash
# Download free historical data
python download_sample_data.py
# Choose option 1

# Process and train
python -m etl.transform
python -m etl.load_to_db
python -m models.train_model
python -m models.predict
```

**Result**: Model trained on 10,000+ matches ✅

### Option B: Maximum Data
**Best for**: Best model performance

```bash
# Get historical data
python download_sample_data.py
# Choose option 1

# Get API data
python fetch_more_data.py

# Process everything
python -m etl.transform
python -m etl.load_to_db
python -m models.train_model
python -m models.predict
```

**Result**: Model trained on 12,000+ matches ✅

### Option C: API Only
**Best for**: If you want only recent data

```bash
python fetch_more_data.py
python -m etl.transform
python -m etl.load_to_db
python -m models.train_model
```

**Result**: Model trained on ~2,000 matches ✅

## 📁 What Gets Downloaded

### Historical CSV Data (football-data.co.uk)

```
data/raw/historical/
├── Premier_League_2324.csv      (~380 matches)
├── Premier_League_2223.csv      (~380 matches)
├── Premier_League_2122.csv      (~380 matches)
├── La_Liga_2324.csv             (~380 matches)
├── Bundesliga_2324.csv          (~306 matches)
├── Serie_A_2324.csv             (~380 matches)
├── Ligue_1_2324.csv             (~380 matches)
└── ... (25 total files)

Total: ~10,000+ matches
```

### API Data (football-data.org + The Odds API)

```
data/raw/football_data_org/
├── matches_2021_Premier_League_*.json
├── matches_2001_Champions_League_*.json
└── ...

data/raw/the_odds_api/
├── odds_soccer_epl_*.json
├── odds_soccer_spain_la_liga_*.json
└── ...
```

## 🔧 Troubleshooting

### "pandas installation failed"

```bash
# Install pandas separately first
pip install --upgrade pip
pip install pandas --prefer-binary

# Then install rest
pip install -r requirements.txt
```

### "Not enough data to train model"

```bash
# Download historical data
python download_sample_data.py
# Choose option 1
```

### "API rate limit exceeded"

Use historical CSV data instead - it's FREE and has more data!

```bash
python download_sample_data.py
```

## 📈 Expected Results

### After Downloading Data

- **Matches in database**: 10,000+
- **Training data**: Sufficient ✅
- **Model accuracy**: ~55-65% (typical for football)
- **Predictions**: Available for upcoming matches

### API Endpoints Working

```bash
# Get health status
curl http://localhost:8000/api/v1/health

# Get matches
curl http://localhost:8000/api/v1/matches?limit=10

# Get prediction (after training)
curl http://localhost:8000/api/v1/predictions/{match_id}
```

## 🎓 Understanding the Data

### Historical CSV Columns

- `Date`: Match date
- `HomeTeam`, `AwayTeam`: Team names
- `FTHG`, `FTAG`: Full-time goals (home/away)
- `FTR`: Result (H=home win, D=draw, A=away win)
- `B365H`, `B365D`, `B365A`: Bet365 odds
- Plus 20+ other bookmaker odds

### Our Normalized Schema

```python
{
    'match_id': int,
    'home_team': str,
    'away_team': str,
    'home_score': int,
    'away_score': int,
    'result': str,  # 'home_win', 'draw', 'away_win'
    'date': datetime,
    'competition': str,
    'status': str
}
```

## 📚 Documentation

- **Full Guide**: See `GET_MORE_DATA.md`
- **API Setup**: See `API_SETUP_GUIDE.md`
- **Quick Start**: See `QUICKSTART.md`
- **README**: See `README.md`

## ⚡ TL;DR - Just Run This

```bash
# 1. Get data (choose option 1 when prompted)
python download_sample_data.py

# 2. Process and train
python -m etl.transform
python -m etl.load_to_db
python -m models.train_model
python -m models.predict

# 3. Your API is already running at http://localhost:8000/docs
```

## 🎉 Success Criteria

After running the above commands, you should have:

✅ 10,000+ matches in database  
✅ Trained XGBoost model  
✅ Predictions for upcoming matches  
✅ Working API with endpoints  
✅ Model metrics and evaluation reports  

## 💡 Tips

1. **Start with historical data** - It's free and plentiful
2. **Save API calls** for live predictions
3. **Retrain weekly** with new data
4. **Monitor model performance** using `python -m models.evaluate`
5. **Check API health** at http://localhost:8000/api/v1/health

---

**Ready to go?** Run `python download_sample_data.py` now!
