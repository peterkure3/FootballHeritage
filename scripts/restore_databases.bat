@echo off
setlocal
REM Quick restore script for Football Heritage databases
REM Usage: restore_databases.bat <backup_folder> [password]
REM Example: restore_databases.bat ..\backups\20260131_170000 mypassword

cd /d "%~dp0"

call "%~dp0find_python.bat"
if errorlevel 1 exit /b 1
if /i "%~1"=="--help" (
    %FH_PYTHON% "%~dp0restore_databases.py" --help
    exit /b
)

echo ========================================
echo Football Heritage Database Restore
echo ========================================

set "BACKUP_DIR=%~1"
if "%BACKUP_DIR%"=="" (
    echo ERROR: Please specify backup directory
    echo Usage: restore_databases.bat ^<backup_folder^> [password]
    echo Example: restore_databases.bat ..\backups\20260131_170000
    pause
    exit /b 1
)

set "DB_PASSWORD=%~2"
if "%DB_PASSWORD%"=="" (
    set /p DB_PASSWORD="Enter database password: "
)

%FH_PYTHON% "%~dp0restore_databases.py" --backup-dir "%BACKUP_DIR%" --db-password "%DB_PASSWORD%"
set "RESULT=%ERRORLEVEL%"

echo.
pause
exit /b %RESULT%
