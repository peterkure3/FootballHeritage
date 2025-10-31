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

REM Fetch new data
echo.
echo [1/5] Fetching raw data...
python -m etl.fetch_raw_data
if %errorlevel% neq 0 (
    echo ERROR: Data fetch failed
    exit /b 1
)

REM Transform data
echo.
echo [2/5] Transforming data...
python -m etl.transform
if %errorlevel% neq 0 (
    echo ERROR: Transform failed
    exit /b 1
)

REM Load to pipeline database
echo.
echo [3/5] Loading to pipeline database...
python -m etl.load_to_db
if %errorlevel% neq 0 (
    echo ERROR: Database load failed
    exit /b 1
)

REM Sync to backend database
echo.
echo [4/5] Syncing to backend database...
python sync_to_backend.py
if %errorlevel% neq 0 (
    echo ERROR: Backend sync failed
    exit /b 1
)

REM Generate predictions
echo.
echo [5/5] Generating predictions...
python -m models.predict
if %errorlevel% neq 0 (
    echo ERROR: Prediction generation failed
    exit /b 1
)

echo.
echo ========================================
echo Daily fetch + sync completed successfully!
echo Finished: %date% %time%
echo ========================================
