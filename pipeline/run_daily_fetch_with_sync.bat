@echo off
REM Daily automated football data fetch + backend sync script
REM Run this via Windows Task Scheduler

cd /d "%~dp0"

echo ========================================
echo Football Data Daily Fetch + Backend Sync
echo Started: %date% %time%
echo ========================================

REM Activate virtual environment if you have one
REM call venv\Scripts\activate

REM Fetch football data
echo.
echo [1/7] Fetching football data...
python -m etl.fetch_raw_data
if %errorlevel% neq 0 (
    echo WARNING: Football data fetch had issues, but continuing with other steps...
)

REM Fetch NBA data
echo.
echo [2/7] Fetching NBA data...
python -m etl.fetch_nba_data_wrapper
if %errorlevel% neq 0 (
    echo WARNING: NBA data fetch had issues, but continuing with other steps...
)

REM Fetch NCAAB data (March Madness)
echo.
echo [3/7] Fetching NCAAB data...
python -m etl.fetch_ncaab_odds
if %errorlevel% neq 0 (
    echo WARNING: NCAAB data fetch had issues, but continuing with other steps...
)

REM Transform data
echo.
echo [4/7] Transforming data...
python -m etl.transform
if %errorlevel% neq 0 (
    echo ERROR: Transform failed
    exit /b 1
)

REM Load to pipeline database (creates tables if needed)
echo.
echo [5/7] Loading to pipeline database...
python -m etl.load_to_db
if %errorlevel% neq 0 (
    echo ERROR: Database load failed
    exit /b 1
)

REM Validate database schema (after load, tables should exist)
echo.
echo [6/7] Validating database schema...
python check_schema.py --ensure nba_games
if %errorlevel% neq 0 (
    echo WARNING: Schema validation had issues, but continuing...
)

REM Sync to backend database
echo.
echo [7/7] Syncing to backend database...
python sync_to_backend.py
if %errorlevel% neq 0 (
    echo ERROR: Backend sync failed
    exit /b 1
)

echo.
echo ========================================
echo Daily fetch + sync completed successfully!
echo Finished: %date% %time%
echo ========================================
