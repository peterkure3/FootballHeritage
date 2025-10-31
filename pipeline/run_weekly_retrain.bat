@echo off
REM Weekly model retraining script
REM Run this via Windows Task Scheduler

cd /d "%~dp0"

echo ========================================
echo Football Model Weekly Retrain
echo Started: %date% %time%
echo ========================================

REM Activate virtual environment if you have one
REM call venv\Scripts\activate

REM Fetch fresh data
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

REM Load to database
echo.
echo [3/5] Loading to database...
python -m etl.load_to_db
if %errorlevel% neq 0 (
    echo ERROR: Database load failed
    exit /b 1
)

REM Train model
echo.
echo [4/5] Training model...
python -m models.train_model
if %errorlevel% neq 0 (
    echo ERROR: Model training failed
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
echo Weekly retrain completed successfully!
echo Finished: %date% %time%
echo ========================================
