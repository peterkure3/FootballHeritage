@echo off
REM Football Heritage Backend - Code Optimization Script
REM This script consolidates duplicate code and optimizes the build

echo ========================================
echo Football Heritage - Code Optimization
echo ========================================
echo.

REM Step 1: Backup current code
echo [1/8] Creating backup...
if not exist "backup" mkdir backup
xcopy /E /I /Y src backup\src > nul
xcopy /Y Cargo.toml backup\Cargo.toml > nul
echo ✓ Backup created in ./backup/

REM Step 2: Remove duplicate betting service
echo.
echo [2/8] Removing duplicate betting service...
if exist "src\betting.rs" (
    del src\betting.rs
    echo ✓ Removed old betting.rs (use betting_simple.rs instead)
) else (
    echo - betting.rs already removed
)

REM Step 3: Update main.rs to use simplified betting service
echo.
echo [3/8] Updating imports...
powershell -Command "(Get-Content src\main.rs) -replace 'mod betting;', '// mod betting; // Removed - use betting_simple instead' | Set-Content src\main.rs"
echo ✓ Updated main.rs

REM Step 4: Clean build artifacts
echo.
echo [4/8] Cleaning build artifacts...
if exist "target" (
    echo Removing target directory...
    rmdir /S /Q target
    echo ✓ Removed target/ directory
) else (
    echo - No target directory found
)

REM Step 5: Remove Cargo.lock to rebuild with new optimizations
echo.
echo [5/8] Refreshing Cargo.lock...
if exist "Cargo.lock" (
    del Cargo.lock
    echo ✓ Removed Cargo.lock (will be regenerated)
) else (
    echo - No Cargo.lock found
)

REM Step 6: Check for unused dependencies
echo.
echo [6/8] Checking for unused code...
cargo +nightly udeps 2>nul
if %errorlevel% neq 0 (
    echo ! cargo-udeps not installed. Install with:
    echo   cargo install cargo-udeps
    echo   Then run: cargo +nightly udeps
) else (
    echo ✓ Unused dependency check complete
)

REM Step 7: Build with optimizations
echo.
echo [7/8] Building optimized release binary...
echo This may take a few minutes...
cargo build --release --locked
if %errorlevel% equ 0 (
    echo ✓ Build successful!
) else (
    echo ✗ Build failed. Check errors above.
    goto :error
)

REM Step 8: Analyze binary size
echo.
echo [8/8] Analyzing binary size...
if exist "target\release\football-heritage-backend.exe" (
    for %%A in (target\release\football-heritage-backend.exe) do (
        set size=%%~zA
        set /a mb=%%~zA/1048576
        echo ✓ Binary size: !mb! MB (%%~zA bytes)
    )
) else (
    echo - Binary not found
)

REM Check if cargo-bloat is available
echo.
echo Detailed size analysis:
cargo bloat --release --crates 2>nul
if %errorlevel% neq 0 (
    echo ! cargo-bloat not installed. Install with:
    echo   cargo install cargo-bloat
    echo   Then run: cargo bloat --release --crates
)

REM Summary
echo.
echo ========================================
echo Optimization Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Test the application: cargo run --release
echo 2. Run tests: cargo test --release
echo 3. Check for warnings: cargo clippy
echo 4. Profile binary: cargo bloat --release
echo.
echo To restore backup: xcopy /E /I /Y backup\src src
echo.
goto :end

:error
echo.
echo ========================================
echo Optimization Failed
echo ========================================
echo.
echo To restore from backup:
echo   xcopy /E /I /Y backup\src src
echo   xcopy /Y backup\Cargo.toml Cargo.toml
echo.
exit /b 1

:end
echo Done!
pause
