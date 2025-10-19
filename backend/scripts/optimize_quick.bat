@echo off
REM Quick Build Optimization Script - No hanging!
SETLOCAL EnableDelayedExpansion

echo.
echo ========================================
echo   Football Heritage - Quick Optimize
echo ========================================
echo.

REM Step 1: Create backup (simplified)
echo [1/6] Creating backup...
if not exist backup mkdir backup
if exist src\betting.rs copy src\betting.rs backup\ >nul 2>&1
if exist Cargo.toml copy Cargo.toml backup\ >nul 2>&1
echo Done!

REM Step 2: Remove duplicate betting service
echo.
echo [2/6] Removing duplicate code...
if exist src\betting.rs (
    del src\betting.rs
    echo Removed: src\betting.rs
) else (
    echo Already removed or not found
)

REM Step 3: Clean build artifacts
echo.
echo [3/6] Cleaning build artifacts...
if exist target (
    echo This will free up 4.1 GB...
    rmdir /S /Q target 2>nul
    if exist target (
        echo Note: Some files may be in use. Close any running builds.
    ) else (
        echo Target directory removed!
    )
) else (
    echo No target directory found
)

REM Step 4: Clean Cargo.lock
echo.
echo [4/6] Refreshing Cargo.lock...
if exist Cargo.lock (
    del Cargo.lock
    echo Removed Cargo.lock
)

REM Step 5: Build optimized release
echo.
echo [5/6] Building optimized release binary...
echo This may take 6-8 minutes...
echo.
cargo build --release
if %errorlevel% equ 0 (
    echo.
    echo Build SUCCESS!
) else (
    echo.
    echo Build FAILED - check errors above
    goto :restore
)

REM Step 6: Show results
echo.
echo [6/6] Results:
echo ========================================
if exist target\release\football-heritage-backend.exe (
    for %%A in (target\release\football-heritage-backend.exe) do (
        set size=%%~zA
        set /a mb=%%~zA/1048576
        echo Binary size: !mb! MB
        echo Expected: 5-7 MB
    )
) else (
    echo Binary not found at expected location
)

if exist target (
    echo.
    echo Target directory recreated
    dir target /s 2>nul | find "File(s)"
)

echo.
echo ========================================
echo   Optimization Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Test: cargo test --release
echo 2. Run: cargo run --release
echo 3. Verify functionality
echo.
echo Backup saved in: backup\
echo.
goto :end

:restore
echo.
echo ========================================
echo   RESTORE FROM BACKUP
echo ========================================
if exist backup\betting.rs copy backup\betting.rs src\ >nul
if exist backup\Cargo.toml copy backup\Cargo.toml . >nul
echo Restored from backup
echo.

:end
pause
