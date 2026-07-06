@echo off
REM Weekly model retraining script
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
echo Football Model Weekly Retrain
echo Started: %date% %time%
echo ========================================

REM Activate virtual environment if you have one
REM call venv\Scripts\activate

REM Fetch fresh data
echo.
echo [1/5] Fetching raw data...
%PYTHON% -m etl.fetch_raw_data
if %errorlevel% neq 0 (
    echo ERROR: Data fetch failed
    exit /b 1
)

REM Transform data
echo.
echo [2/5] Transforming data...
%PYTHON% -m etl.transform
if %errorlevel% neq 0 (
    echo ERROR: Transform failed
    exit /b 1
)

REM Load to database
echo.
echo [3/5] Loading to database...
%PYTHON% -m etl.load_to_db
if %errorlevel% neq 0 (
    echo ERROR: Database load failed
    exit /b 1
)

REM Train model
echo.
echo [4/5] Training model...
%PYTHON% -m models.train_model_v2
if %errorlevel% neq 0 (
    echo ERROR: Model training failed
    exit /b 1
)

REM Generate predictions
echo.
echo [5/5] Generating predictions...
%PYTHON% -m models.predict_v2
if %errorlevel% neq 0 (
    echo ERROR: Prediction generation failed
    exit /b 1
)

echo.
echo ========================================
echo Weekly retrain completed successfully!
echo Finished: %date% %time%
echo ========================================
