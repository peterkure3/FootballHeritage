@echo off
REM Quick restore script for Football Heritage databases
REM Usage: restore_databases.bat <backup_folder> [password]
REM Example: restore_databases.bat ..\backups\20260131_170000 mypassword

cd /d "%~dp0"

echo ========================================
echo Football Heritage Database Restore
echo ========================================

set BACKUP_DIR=%1
if "%BACKUP_DIR%"=="" (
    echo ERROR: Please specify backup directory
    echo Usage: restore_databases.bat ^<backup_folder^> [password]
    echo Example: restore_databases.bat ..\backups\20260131_170000
    pause
    exit /b 1
)

set DB_PASSWORD=%2
if "%DB_PASSWORD%"=="" (
    set /p DB_PASSWORD="Enter database password: "
)

python restore_databases.py --backup-dir "%BACKUP_DIR%" --db-password "%DB_PASSWORD%"

echo.
pause
