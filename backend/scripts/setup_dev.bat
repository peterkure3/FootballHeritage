@echo off
REM Football Heritage Backend - Development Setup Script (Windows)
REM This script sets up the local development environment on Windows

echo.
echo ========================================
echo Football Heritage Backend - Dev Setup
echo ========================================
echo.

REM Check if Rust is installed
where cargo >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Rust is not installed
    echo Please install Rust from https://rustup.rs/
    pause
    exit /b 1
)
echo [OK] Rust is installed

REM Check if PostgreSQL is installed
where psql >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] PostgreSQL client not found
    echo Please ensure PostgreSQL is installed and accessible
) else (
    echo [OK] PostgreSQL client found
)

REM Check if .env file exists
if not exist .env (
    echo [WARNING] .env file not found, creating from .env.example
    copy .env.example .env >nul
    echo [OK] Created .env file
    echo.
    echo [IMPORTANT] Please edit .env and configure:
    echo    - DATABASE_URL (PostgreSQL connection string)
    echo    - JWT_SECRET (256-bit random secret)
    echo    - ENCRYPTION_KEY (32-byte random key)
    echo.
) else (
    echo [OK] .env file exists
)

REM Create necessary directories
echo.
echo Creating directories...
if not exist logs mkdir logs
if not exist certs mkdir certs
if not exist data mkdir data
echo [OK] Created directories

REM Generate secure keys using PowerShell
echo.
echo ========================================
echo Security Keys Setup
echo ========================================
echo.

REM Check if keys need generation
findstr /C:"your-super-secure-jwt-secret-key-here" .env >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Generating JWT_SECRET...
    powershell -Command "$bytes = New-Object byte[] 64; (New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($bytes); [Convert]::ToBase64String($bytes)" > temp_jwt.txt
    set /p JWT_SECRET=<temp_jwt.txt
    powershell -Command "(Get-Content .env) -replace 'JWT_SECRET=.*', 'JWT_SECRET=%JWT_SECRET%' | Set-Content .env"
    del temp_jwt.txt
    echo [OK] Generated JWT_SECRET
)

findstr /C:"your-256-bit-encryption-key-for-wallet-balances-here" .env >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Generating ENCRYPTION_KEY...
    powershell -Command "$bytes = New-Object byte[] 32; (New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($bytes); [Convert]::ToBase64String($bytes)" > temp_enc.txt
    set /p ENC_KEY=<temp_enc.txt
    powershell -Command "(Get-Content .env) -replace 'ENCRYPTION_KEY=.*', 'ENCRYPTION_KEY=%ENC_KEY%' | Set-Content .env"
    del temp_enc.txt
    echo [OK] Generated ENCRYPTION_KEY
)

REM Check database configuration
echo.
echo ========================================
echo Database Setup
echo ========================================
echo.

findstr /C:"postgresql://username:password@localhost" .env >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [WARNING] Database URL is using example credentials
    echo Please update DATABASE_URL in .env with your PostgreSQL credentials
    echo.
    echo Default format:
    echo DATABASE_URL=postgresql://username:password@localhost:5432/football_heritage_betting
    echo.
    set DB_CONFIGURED=false
) else (
    echo [OK] Database URL is configured
    set DB_CONFIGURED=true
)

REM Install dependencies
echo.
echo ========================================
echo Installing Dependencies
echo ========================================
echo.
echo This may take a few minutes...
cargo build
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to build dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies installed

REM Generate self-signed certificate for development
if not exist certs\server.crt (
    echo.
    echo Would you like to generate self-signed TLS certificates for development?
    echo (This requires OpenSSL to be installed)
    set /p GENERATE_CERTS="Generate certificates? (y/n): "
    if /i "%GENERATE_CERTS%"=="y" (
        where openssl >nul 2>nul
        if %ERRORLEVEL% EQU 0 (
            echo Generating self-signed certificate...
            openssl req -x509 -newkey rsa:4096 -nodes -keyout certs\server.key -out certs\server.crt -days 365 -subj "/C=US/ST=State/L=City/O=FootballHeritage/CN=localhost"
            echo [OK] Self-signed certificate generated
            echo [WARNING] This is for development only. Use proper certificates in production!
        ) else (
            echo [WARNING] OpenSSL not found. Cannot generate certificates.
            echo You can install OpenSSL or manually create certificates later.
        )
    )
) else (
    echo [OK] TLS certificates already exist
)

REM Final summary
echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next Steps:
echo.
echo 1. Review and update .env with your configuration
echo    - Verify DATABASE_URL is correct
echo    - Ensure JWT_SECRET and ENCRYPTION_KEY are set
echo.
echo 2. Create the database (if not exists):
echo    psql -U postgres -c "CREATE DATABASE football_heritage_betting;"
echo.
echo 3. Run database schema:
echo    psql -U postgres -d football_heritage_betting -f schema.sql
echo.
echo 4. Install SQLx CLI (optional):
echo    cargo install sqlx-cli --no-default-features --features postgres
echo.
echo 5. Run migrations (if using SQLx migrations):
echo    sqlx migrate run
echo.
echo 6. Start the development server:
echo    cargo run
echo.
echo 7. Run tests:
echo    cargo test
echo.
echo 8. Run with hot reload (install cargo-watch):
echo    cargo install cargo-watch
echo    cargo watch -x run
echo.
echo Useful Commands:
echo    cargo check          - Quick compile check
echo    cargo test          - Run tests
echo    cargo build         - Build project
echo    cargo run           - Run server
echo    cargo clippy        - Linter
echo    cargo fmt           - Format code
echo.
echo Documentation:
echo    - BETTING_SERVICE_GUIDE.md - Complete API guide
echo    - TRANSACTION_FIXES.md - Technical details
echo    - DEPLOYMENT_CHECKLIST.md - Production deployment
echo    - QUICK_REFERENCE.md - Quick reference card
echo.
echo Happy coding!
echo.
pause
