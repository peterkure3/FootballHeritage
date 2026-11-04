@echo off
setlocal
cd /d "%~dp0"
py -3.12 --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Install Python 3.12 with the Windows Python launcher, then rerun this file.
    exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
    py -3.12 -m venv .venv
    if errorlevel 1 exit /b 1
)
REM Restore the tested stack; do not silently upgrade model-loading dependencies.
".venv\Scripts\python.exe" -m pip install -r requirements-automation-lock.txt
if errorlevel 1 exit /b 1
if not exist ".venv-scrapling\Scripts\python.exe" (
    py -3.12 -m venv .venv-scrapling
    if errorlevel 1 exit /b 1
    ".venv-scrapling\Scripts\python.exe" -m pip install -r requirements-scraping.txt
    if errorlevel 1 exit /b 1
    ".venv-scrapling\Scripts\scrapling.exe" install
    if errorlevel 1 exit /b 1
)
call run_pipeline.bat doctor
exit /b %errorlevel%
