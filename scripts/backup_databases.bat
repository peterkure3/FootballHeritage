@echo off
REM Quick backup script for Football Heritage databases
REM Usage: backup_databases.bat [password]

cd /d "%~dp0"

echo ========================================
echo Football Heritage Database Backup
echo ========================================

set DB_PASSWORD=%1
if "%DB_PASSWORD%"=="" (
    set /p DB_PASSWORD="Enter database password: "
)

python backup_databases.py --db-password "%DB_PASSWORD%"

echo.
pause
