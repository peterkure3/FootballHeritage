@echo off
REM Daily automated football data fetch + backend sync script
REM Run this via Windows Task Scheduler

cd /d "%~dp0"

REM Resolve Python interpreter: prefer "python", fall back to "py -3".
REM Must actually RUN it ("where python" is not enough — the Microsoft Store
REM alias stub exists on PATH but exits with an error when invoked).
set "PYTHON=python"
%PYTHON% --version >nul 2>&1
if %errorlevel% neq 0 set "PYTHON=py -3"
%PYTHON% --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: No working Python found - tried "python" and "py -3".
    echo Install Python 3 or ensure the py launcher is on PATH.
    exit /b 1
)
echo Using Python interpreter: %PYTHON%

echo ========================================
echo Football Data Daily Fetch + Backend Sync
echo Started: %date% %time%
echo ========================================

REM Activate virtual environment if you have one
REM call venv\Scripts\activate

REM Fetch football data
echo.
echo [1/7] Fetching football data...
%PYTHON% -m etl.fetch_raw_data
if %errorlevel% neq 0 (
    echo WARNING: Football data fetch had issues, but continuing with other steps...
)

REM Fetch NBA data
echo.
echo [2/7] Fetching NBA data...
%PYTHON% -m etl.fetch_nba_data_wrapper
if %errorlevel% neq 0 (
    echo WARNING: NBA data fetch had issues, but continuing with other steps...
)

REM Fetch NCAAB data (March Madness)
echo.
echo [3/7] Fetching NCAAB data...
%PYTHON% -m etl.fetch_ncaab_odds
if %errorlevel% neq 0 (
    echo WARNING: NCAAB data fetch had issues, but continuing with other steps...
)

REM Transform data
echo.
echo [4/7] Transforming data...
%PYTHON% -m etl.transform
if %errorlevel% neq 0 (
    echo ERROR: Transform failed
    exit /b 1
)

REM Load to pipeline database (creates tables if needed)
echo.
echo [5/7] Loading to pipeline database...
%PYTHON% -m etl.load_to_db
if %errorlevel% neq 0 (
    echo ERROR: Database load failed
    exit /b 1
)

REM Validate database schema (after load, tables should exist)
echo.
echo [6/7] Validating database schema...
%PYTHON% check_schema.py --ensure nba_games
if %errorlevel% neq 0 (
    echo WARNING: Schema validation had issues, but continuing...
)

REM Sync to backend database
echo.
echo [7/7] Syncing to backend database...
%PYTHON% sync_to_backend.py
if %errorlevel% neq 0 (
    echo ERROR: Backend sync failed
    exit /b 1
)

echo.
echo ========================================
echo Daily fetch + sync completed successfully!
echo Finished: %date% %time%
echo ========================================
