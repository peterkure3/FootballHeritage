#!/bin/bash
# Football Heritage Backend - Code Optimization Script
# This script consolidates duplicate code and optimizes the build

set -e

echo "========================================"
echo "Football Heritage - Code Optimization"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Backup current code
echo "[1/8] Creating backup..."
mkdir -p backup
cp -r src backup/ 2>/dev/null || true
cp Cargo.toml backup/ 2>/dev/null || true
echo -e "${GREEN}✓ Backup created in ./backup/${NC}"

# Step 2: Remove duplicate betting service
echo ""
echo "[2/8] Removing duplicate betting service..."
if [ -f "src/betting.rs" ]; then
    rm src/betting.rs
    echo -e "${GREEN}✓ Removed old betting.rs (use betting_simple.rs instead)${NC}"
else
    echo "- betting.rs already removed"
fi

# Step 3: Update main.rs to use simplified betting service
echo ""
echo "[3/8] Updating imports..."
if [ -f "src/main.rs" ]; then
    sed -i.bak 's/mod betting;/\/\/ mod betting; \/\/ Removed - use betting_simple instead/' src/main.rs
    rm src/main.rs.bak 2>/dev/null || true
    echo -e "${GREEN}✓ Updated main.rs${NC}"
else
    echo -e "${RED}✗ main.rs not found${NC}"
fi

# Step 4: Clean build artifacts
echo ""
echo "[4/8] Cleaning build artifacts..."
if [ -d "target" ]; then
    echo "Removing target directory..."
    rm -rf target
    echo -e "${GREEN}✓ Removed target/ directory${NC}"
else
    echo "- No target directory found"
fi

# Step 5: Remove Cargo.lock to rebuild with new optimizations
echo ""
echo "[5/8] Refreshing Cargo.lock..."
if [ -f "Cargo.lock" ]; then
    rm Cargo.lock
    echo -e "${GREEN}✓ Removed Cargo.lock (will be regenerated)${NC}"
else
    echo "- No Cargo.lock found"
fi

# Step 6: Check for unused dependencies
echo ""
echo "[6/8] Checking for unused code..."
if command -v cargo-udeps &> /dev/null; then
    cargo +nightly udeps 2>/dev/null || echo -e "${YELLOW}! Could not run udeps (nightly toolchain may be missing)${NC}"
else
    echo -e "${YELLOW}! cargo-udeps not installed. Install with:${NC}"
    echo "  cargo install cargo-udeps"
    echo "  Then run: cargo +nightly udeps"
fi

# Step 7: Build with optimizations
echo ""
echo "[7/8] Building optimized release binary..."
echo "This may take a few minutes..."
if cargo build --release --locked; then
    echo -e "${GREEN}✓ Build successful!${NC}"
else
    echo -e "${RED}✗ Build failed. Check errors above.${NC}"
    exit 1
fi

# Step 8: Analyze binary size
echo ""
echo "[8/8] Analyzing binary size..."
if [ -f "target/release/football-heritage-backend" ]; then
    SIZE=$(stat -f%z "target/release/football-heritage-backend" 2>/dev/null || stat -c%s "target/release/football-heritage-backend" 2>/dev/null)
    MB=$((SIZE / 1048576))
    echo -e "${GREEN}✓ Binary size: ${MB} MB (${SIZE} bytes)${NC}"

    # Strip if not already stripped
    if command -v strip &> /dev/null; then
        echo "Stripping debug symbols..."
        strip target/release/football-heritage-backend
        SIZE_AFTER=$(stat -f%z "target/release/football-heritage-backend" 2>/dev/null || stat -c%s "target/release/football-heritage-backend" 2>/dev/null)
        MB_AFTER=$((SIZE_AFTER / 1048576))
        SAVED=$((SIZE - SIZE_AFTER))
        SAVED_MB=$((SAVED / 1048576))
        echo -e "${GREEN}✓ After stripping: ${MB_AFTER} MB (saved ${SAVED_MB} MB)${NC}"
    fi
else
    echo "- Binary not found"
fi

# Check if cargo-bloat is available
echo ""
echo "Detailed size analysis:"
if command -v cargo-bloat &> /dev/null; then
    cargo bloat --release --crates | head -20
else
    echo -e "${YELLOW}! cargo-bloat not installed. Install with:${NC}"
    echo "  cargo install cargo-bloat"
    echo "  Then run: cargo bloat --release --crates"
fi

# Display target directory size comparison
echo ""
echo "Build artifacts size:"
du -sh target 2>/dev/null || echo "No target directory"

# Summary
echo ""
echo "========================================"
echo "Optimization Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Test the application: cargo run --release"
echo "2. Run tests: cargo test --release"
echo "3. Check for warnings: cargo clippy"
echo "4. Profile binary: cargo bloat --release"
echo ""
echo "To restore backup: cp -r backup/src/* src/ && cp backup/Cargo.toml ."
echo ""
echo -e "${GREEN}Done!${NC}"
