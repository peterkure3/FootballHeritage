# Automation Setup - Quick Summary

## ✅ What's Ready

Your football betting pipeline is now ready for automated fetching!

### Files Created
- ✅ `run_daily_fetch.bat` - Daily data fetch script
- ✅ `run_weekly_retrain.bat` - Weekly model retrain script
- ✅ `scheduler.py` - Python-based scheduler
- ✅ `test_automation.py` - Test automation setup
- ✅ `AUTOMATION_SETUP.md` - Complete setup guide

### Current Status
- ✅ 439 matches in database
- ✅ Model trained and ready
- ✅ Predictions generated
- ✅ API keys configured
- ✅ Database connected

---

## 🚀 Quick Start (5 Minutes)

### Option 1: Windows Task Scheduler (Recommended)

**Step 1: Test the scripts**
```bash
# Test daily fetch
run_daily_fetch.bat

# Test weekly retrain  
run_weekly_retrain.bat
```

**Step 2: Set up Task Scheduler**

1. Press `Win + R`, type `taskschd.msc`, press Enter
2. Click "Create Basic Task"
3. Name: `Football Data Daily Fetch`
4. Trigger: Daily at 8:00 AM
5. Action: Start a program
6. Program: `d:\Github\FootballHeritgae\pipeline\run_daily_fetch.bat`
7. Start in: `d:\Github\FootballHeritgae\pipeline`
8. Finish

Repeat for weekly retrain (Sunday at 2:00 AM).

**Done!** Your pipeline will now run automatically.

---

### Option 2: Python Scheduler

**Step 1: Install schedule package**
```bash
pip install schedule
```

**Step 2: Run the scheduler**
```bash
python scheduler.py
```

**Step 3: Keep it running**
- Leave the terminal open, OR
- Run as a Windows service (see AUTOMATION_SETUP.md)

---

## 📊 Recommended Schedule

### Daily Fetch (8:00 AM)
- Fetches new matches and odds
- Updates database
- Generates predictions
- **Duration**: ~2-3 minutes
- **API calls**: ~10 requests

### Weekly Retrain (Sunday 2:00 AM)
- Full pipeline with model retraining
- Uses all historical data
- **Duration**: ~10-15 minutes
- **API calls**: ~10 requests

---

## 🔍 Monitoring

### Check if automation is working

**Windows Task Scheduler:**
```
Task Scheduler → Your Task → History tab
```

**Python Scheduler:**
```bash
tail -f scheduler.log
```

**Database:**
```bash
python check_data.py
```

---

## 📈 What Gets Automated

### Daily
1. ✅ Fetch latest matches from football-data.org
2. ✅ Fetch latest odds from The Odds API
3. ✅ Transform and clean data
4. ✅ Load to PostgreSQL database
5. ✅ Generate predictions for upcoming matches

### Weekly
1. ✅ Everything from daily, PLUS:
2. ✅ Retrain XGBoost model with all historical data
3. ✅ Update model with latest patterns
4. ✅ Improve prediction accuracy

---

## 🎯 Next Steps

1. **Set up automation** (choose Windows Task Scheduler or Python Scheduler)
2. **Monitor first run** to ensure it works
3. **Check predictions** regularly
4. **Optional**: Add more leagues to `config.py`

---

## 📚 Documentation

- **AUTOMATION_SETUP.md** - Detailed setup guide
- **README.md** - Pipeline overview
- **NCAA_BASKETBALL_GUIDE.md** - Basketball integration (ready for Nov 2025)

---

## 🚨 Troubleshooting

### Task didn't run
- Check Task Scheduler history
- Verify batch file paths are correct
- Test batch file manually

### API rate limits
- Free tier: 500 requests/month (The Odds API)
- Daily fetch uses ~10 requests
- You have plenty of headroom

### Database issues
- Ensure PostgreSQL is running
- Check credentials in `.env`
- Run: `python check_data.py`

---

## ✨ Summary

**You're all set!** Your pipeline will now:
- ✅ Fetch new football data daily
- ✅ Retrain model weekly
- ✅ Generate predictions automatically
- ✅ Keep your database updated

**Choose your automation method and you're done!** 🎉

---

**Last Updated**: October 30, 2025  
**Status**: Ready for automation ✅
