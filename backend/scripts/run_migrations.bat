@echo off
REM ============================================================================
REM  Football Heritage - Database Migrations Runner
REM ============================================================================

echo.
echo ========================================
echo   Database Migrations
echo ========================================
echo.

REM Set database URL
set DATABASE_URL=postgresql://postgres:jumpman13@localhost:5432/football_heritage

echo Database: football_heritage
echo User:     postgres
echo Host:     localhost:5432
echo.

REM Check if database exists
echo [Step 1/3] Checking database...
psql -U postgres -lqt | findstr /C:"football_heritage" >nul 2>&1
if %errorlevel% neq 0 (
    echo Database does not exist. Creating...
    psql -U postgres -c "CREATE DATABASE football_heritage;"
    if %errorlevel% equ 0 (
        echo Created database successfully!
    ) else (
        echo Failed to create database!
        pause
        exit /b 1
    )
) else (
    echo Database already exists.
)

echo.
echo [Step 2/3] Running migrations...
echo.

REM Check if sqlx-cli is installed
where sqlx >nul 2>&1
if %errorlevel% equ 0 (
    echo Using SQLx CLI...
    sqlx migrate run
    if %errorlevel% equ 0 (
        echo.
        echo Migrations completed successfully!
        sqlx migrate info
    ) else (
        echo.
        echo Migration failed!
        pause
        exit /b 1
    )
) else (
    echo SQLx CLI not found. Installing...
    echo This may take a few minutes...
    cargo install sqlx-cli --no-default-features --features postgres
    if %errorlevel% equ 0 (
        echo SQLx CLI installed successfully!
        echo Running migrations...
        sqlx migrate run
    ) else (
        echo Failed to install SQLx CLI!
        pause
        exit /b 1
    )
)

echo.
echo [Step 3/3] Verifying tables...
psql -U postgres -d football_heritage -c "\dt" 2>nul
if %errorlevel% equ 0 (
    echo.
    echo Checking sample data...
    psql -U postgres -d football_heritage -c "SELECT COUNT(*) as event_count FROM events;" 2>nul
)

echo.
echo ========================================
echo   Migration Complete!
echo ========================================
echo.
echo Next steps:
echo   1. Run the application: .\run.ps1
echo   2. Or: cargo run --release
echo.
echo Tables created:
echo   - users
echo   - wallets
echo   - transactions
echo   - events
echo   - bets
echo   - gambling_limits
echo   - user_activity
echo   - betting_patterns
echo.

pause
