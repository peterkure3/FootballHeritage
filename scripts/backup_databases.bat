@echo off
setlocal
REM Quick backup script for Football Heritage databases
REM Usage: backup_databases.bat [password]

cd /d "%~dp0"

call "%~dp0find_python.bat"
if errorlevel 1 exit /b 1
if /i "%~1"=="--help" (
    %FH_PYTHON% "%~dp0backup_databases.py" --help
    exit /b
)

echo ========================================
echo Football Heritage Database Backup
echo ========================================

set "DB_PASSWORD=%~1"
if "%DB_PASSWORD%"=="" (
    set /p DB_PASSWORD="Enter database password: "
)

%FH_PYTHON% "%~dp0backup_databases.py" --db-password "%DB_PASSWORD%"
set "RESULT=%ERRORLEVEL%"

echo.
pause
exit /b %RESULT%
