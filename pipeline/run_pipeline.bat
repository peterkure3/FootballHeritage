@echo off
setlocal
cd /d "%~dp0"
REM Optional explicit interpreter; otherwise prefer the installed pipeline environments.
if defined FH_PIPELINE_PYTHON goto configured
if exist "%~dp0.venv\Scripts\python.exe" set "FH_PIPELINE_PYTHON=%~dp0.venv\Scripts\python.exe"
if defined FH_PIPELINE_PYTHON goto configured
REM Python 3.12 has the parquet/training stack; scraping stays in its own environment.
py -3.12 -c "import pyarrow,pandas,sklearn,xgboost,lightgbm,sqlalchemy,fastapi" >nul 2>&1
if not errorlevel 1 (
    py -3.12 -u -m scripts.run_pipeline %*
    exit /b
)
call "%~dp0..\scripts\find_python.bat"
if errorlevel 1 exit /b 1
%FH_PYTHON% -u -m scripts.run_pipeline %*
exit /b %errorlevel%
:configured
if not exist "%FH_PIPELINE_PYTHON%" (
    echo ERROR: FH_PIPELINE_PYTHON must point to an existing Python executable.
    exit /b 1
)
"%FH_PIPELINE_PYTHON%" -u -m scripts.run_pipeline %*
exit /b %errorlevel%
