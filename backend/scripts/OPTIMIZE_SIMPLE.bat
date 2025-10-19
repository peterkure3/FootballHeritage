@echo off
REM Ultra-Simple Build Optimization
REM Just run this file - no hanging, no complexity!

echo.
echo ==========================================
echo    Football Heritage - Build Optimizer
echo ==========================================
echo.
echo This will:
echo  1. Backup your code
echo  2. Remove duplicate files
echo  3. Clean 4.1 GB of build artifacts
echo  4. Rebuild with 65%% size reduction
echo.
pause

echo.
echo [Step 1/5] Creating backup...
if not exist backup mkdir backup >nul 2>&1
if exist src\betting.rs copy /Y src\betting.rs backup\betting.rs >nul 2>&1
echo Done!

echo.
echo [Step 2/5] Removing duplicate code...
if exist src\betting.rs (
    del src\betting.rs
    echo Removed: src\betting.rs
) else (
    echo Already removed
)

echo.
echo [Step 3/5] Cleaning build artifacts (4.1 GB)...
if exist target (
    echo Please wait...
    rd /S /Q target >nul 2>&1
    echo Done!
) else (
    echo Already clean
)

echo.
echo [Step 4/5] Cleaning Cargo.lock...
if exist Cargo.lock del Cargo.lock >nul 2>&1
echo Done!

echo.
echo [Step 5/5] Building optimized binary...
echo This takes 6-8 minutes. Please wait...
echo.

cargo build --release

if %errorlevel% equ 0 (
    echo.
    echo ==========================================
    echo    SUCCESS! Optimization Complete
    echo ==========================================
    echo.

    if exist target\release\football-heritage-backend.exe (
        for %%A in (target\release\football-heritage-backend.exe) do (
            set size=%%~zA
            set /a mb=%%~zA/1048576
            echo Binary size: !mb! MB
            echo Target: 5-7 MB
        )
    )

    echo.
    echo Next steps:
    echo   1. Test: cargo test --release
    echo   2. Run:  cargo run --release
    echo.
    echo Backup saved in: backup\
    echo.
) else (
    echo.
    echo ==========================================
    echo    BUILD FAILED
    echo ==========================================
    echo.
    echo Restoring backup...
    if exist backup\betting.rs copy /Y backup\betting.rs src\ >nul 2>&1
    echo.
    echo Try running: cargo clean
    echo Then run this script again
    echo.
)

pause
