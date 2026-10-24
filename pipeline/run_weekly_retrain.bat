@echo off
REM Weekly model retraining using data already ingested by the daily script
REM Run run_daily_fetch_with_sync.bat first and let it finish before retraining.
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
echo Using existing processed files and imported historical data.
echo ========================================

REM Activate virtual environment if you have one
REM call venv\Scripts\activate

REM Train model
echo.
echo [1/2] Training model...
REM Forward optional tuning flags, e.g. --threads 4 --selection-max-rows 100000.
%PYTHON% -u -m models.train_model_v2 %*
if %errorlevel% neq 0 (
    echo ERROR: Model training failed
    exit /b 1
)

REM Generate predictions
echo.
echo [2/2] Generating predictions...
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
