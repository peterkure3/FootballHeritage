# Automated Fetching Setup Guide

This guide covers three options for automating your football betting pipeline.

## 📋 Quick Overview

| Method | Best For | Complexity | Always Running? |
|--------|----------|------------|-----------------|
| **Windows Task Scheduler** | Windows users | Easy | No (runs on schedule) |
| **Python Scheduler** | Any OS | Medium | Yes (background process) |
| **Apache Airflow** | Production | Advanced | Yes (full orchestration) |

---

## Option 1: Windows Task Scheduler (Recommended)

### ✅ Pros
- Built into Windows
- No additional dependencies
- Easy to set up
- Runs even when not logged in

### 📝 Setup Steps

#### 1. Test the Scripts

First, make sure the batch files work:

```bash
# Test daily fetch
run_daily_fetch.bat

# Test weekly retrain
run_weekly_retrain.bat
```

#### 2. Open Task Scheduler

- Press `Win + R`
- Type `taskschd.msc`
- Press Enter

#### 3. Create Daily Fetch Task

1. Click **"Create Basic Task"**
2. Name: `Football Data Daily Fetch`
3. Trigger: **Daily**
4. Start time: `08:00 AM` (or your preferred time)
5. Action: **Start a program**
6. Program: Browse to `run_daily_fetch.bat`
7. Start in: `d:\Github\FootballHeritgae\pipeline`
8. Finish

#### 4. Create Weekly Retrain Task

1. Click **"Create Basic Task"**
2. Name: `Football Model Weekly Retrain`
3. Trigger: **Weekly**
4. Day: **Sunday**
5. Start time: `02:00 AM`
6. Action: **Start a program**
7. Program: Browse to `run_weekly_retrain.bat`
8. Start in: `d:\Github\FootballHeritgae\pipeline`
9. Finish

#### 5. Configure Advanced Settings

For each task, right-click → **Properties**:

- **General** tab:
  - ✅ Run whether user is logged on or not
  - ✅ Run with highest privileges
  
- **Conditions** tab:
  - ✅ Wake the computer to run this task
  - ❌ Start only if on AC power (uncheck if laptop)
  
- **Settings** tab:
  - ✅ Allow task to be run on demand
  - ✅ If task fails, restart every: 10 minutes
  - Attempt to restart up to: 3 times

### 📊 Monitoring

View task history:
1. Open Task Scheduler
2. Find your task
3. Click **History** tab

Logs are saved in the pipeline directory.

---

## Option 2: Python Scheduler

### ✅ Pros
- Cross-platform (Windows, Mac, Linux)
- Python-based (easy to customize)
- Detailed logging

### ❌ Cons
- Must keep running in background
- Requires `schedule` package

### 📝 Setup Steps

#### 1. Install Dependencies

```bash
pip install schedule
```

#### 2. Test the Scheduler

```bash
python scheduler.py
```

You should see:
```
FOOTBALL BETTING PIPELINE SCHEDULER
Schedule:
  - Daily fetch: Every day at 08:00
  - Weekly retrain: Every Sunday at 02:00
Scheduler started. Press Ctrl+C to stop.
```

#### 3. Run as Background Service

**Windows (PowerShell):**
```powershell
# Start in background
Start-Process python -ArgumentList "scheduler.py" -WindowStyle Hidden -WorkingDirectory "d:\Github\FootballHeritgae\pipeline"
```

**Linux/Mac:**
```bash
# Run with nohup
nohup python scheduler.py > scheduler.log 2>&1 &
```

#### 4. Create Windows Service (Optional)

Use NSSM (Non-Sucking Service Manager):

```bash
# Download NSSM from https://nssm.cc/download
nssm install FootballScheduler "C:\Python313\python.exe" "d:\Github\FootballHeritgae\pipeline\scheduler.py"
nssm start FootballScheduler
```

### 📊 Monitoring

Check logs:
```bash
tail -f scheduler.log
```

---

## Option 3: Apache Airflow

### ✅ Pros
- Production-grade orchestration
- Web UI for monitoring
- Advanced scheduling and retry logic
- Task dependencies

### ❌ Cons
- More complex setup
- Requires additional services (database, web server)

### 📝 Setup Steps

#### 1. Install Airflow

```bash
pip install apache-airflow
```

#### 2. Initialize Airflow

```bash
# Set Airflow home
export AIRFLOW_HOME=~/airflow

# Initialize database
airflow db init

# Create admin user
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com
```

#### 3. Copy DAG File

```bash
# Copy the DAG to Airflow's DAG folder
cp dags/betting_pipeline.py ~/airflow/dags/
```

#### 4. Start Airflow

```bash
# Start web server (terminal 1)
airflow webserver --port 8080

# Start scheduler (terminal 2)
airflow scheduler
```

#### 5. Access Web UI

Open browser: http://localhost:8080

- Login with admin credentials
- Find `football_betting_pipeline` DAG
- Toggle it ON

### 📊 Monitoring

- View DAG runs in web UI
- Check task logs
- Set up email alerts

---

## 🎯 Recommended Schedule

### Daily Fetch (No Retraining)
- **Time**: 8:00 AM
- **Tasks**:
  1. Fetch new matches and odds
  2. Transform data
  3. Load to database
  4. Generate predictions
- **Duration**: ~2-3 minutes
- **API Usage**: ~10 requests

### Weekly Retrain (Full Pipeline)
- **Time**: Sunday 2:00 AM
- **Tasks**:
  1. Fetch data
  2. Transform data
  3. Load to database
  4. **Train model** (with all historical data)
  5. Generate predictions
- **Duration**: ~10-15 minutes
- **API Usage**: ~10 requests

---

## 📈 Customizing the Schedule

### Windows Task Scheduler
- Right-click task → Properties → Triggers
- Edit or add new triggers

### Python Scheduler
Edit `scheduler.py`:

```python
# Change daily time
schedule.every().day.at("10:00").do(daily_fetch_job)

# Run multiple times per day
schedule.every().day.at("08:00").do(daily_fetch_job)
schedule.every().day.at("20:00").do(daily_fetch_job)

# Change weekly day
schedule.every().monday.at("02:00").do(weekly_retrain_job)
```

### Airflow
Edit `config.py`:

```python
# Daily at 8 AM
AIRFLOW_DAG_SCHEDULE = "0 8 * * *"

# Every 6 hours
AIRFLOW_DAG_SCHEDULE = "0 */6 * * *"

# Twice daily (8 AM and 8 PM)
AIRFLOW_DAG_SCHEDULE = "0 8,20 * * *"
```

---

## 🔍 Monitoring & Logs

### Check if Tasks Ran

**Windows Task Scheduler:**
- Task Scheduler → Task → History tab

**Python Scheduler:**
```bash
tail -f scheduler.log
```

**Airflow:**
- Web UI → DAG Runs

### Check Logs

All scripts log to:
- Console output
- JSON logs in pipeline directory

### Database Check

```bash
python check_data.py
```

---

## 🚨 Troubleshooting

### Task Didn't Run

**Windows Task Scheduler:**
1. Check task history for errors
2. Verify "Run whether user is logged on or not" is checked
3. Test batch file manually
4. Check Windows Event Viewer

**Python Scheduler:**
1. Check if process is running: `tasklist | findstr python`
2. Check `scheduler.log` for errors
3. Verify schedule times are correct

### API Rate Limits

If you hit rate limits:
1. Reduce fetch frequency
2. Check remaining requests: `python test_apis.py`
3. The Odds API: 500 requests/month on free tier

### Database Connection Issues

1. Verify PostgreSQL is running
2. Check credentials in `.env`
3. Test connection: `python check_data.py`

---

## 🎉 Quick Start (Recommended)

For most users, **Windows Task Scheduler** is the best option:

```bash
# 1. Test the scripts
run_daily_fetch.bat
run_weekly_retrain.bat

# 2. Set up Task Scheduler (see steps above)

# 3. Monitor
# Check Task Scheduler history
# Or run: python check_data.py
```

---

## 📚 Additional Resources

- **Task Scheduler Guide**: https://docs.microsoft.com/en-us/windows/win32/taskschd/
- **Python Schedule**: https://schedule.readthedocs.io/
- **Apache Airflow**: https://airflow.apache.org/docs/

---

**Status**: Automation scripts ready ✅  
**Last Updated**: October 30, 2025  
**Recommended**: Windows Task Scheduler for simplicity
