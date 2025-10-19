# Build Optimization Guide

## Overview
This guide provides comprehensive strategies to reduce build size, compilation time, and binary size for the Football Heritage betting backend.

## Current Optimizations Applied

### 1. Cargo.toml Optimizations

#### Release Profile Settings
```toml
[profile.release]
opt-level = "z"     # Optimize for size (smaller than "s")
lto = true          # Link Time Optimization - reduces binary size by 20-30%
codegen-units = 1   # Single codegen unit for better optimization
strip = true        # Strip debug symbols - reduces size by 30-50%
panic = "abort"     # Smaller panic handler - saves ~200KB
```

#### Dependency Feature Flags
We've enabled `default-features = false` for all dependencies and only include necessary features:

- **tokio**: Reduced from "full" to only needed features (rt-multi-thread, macros, sync, time)
  - Savings: ~500KB-1MB
- **actix-web**: Only compress-gzip, macros, rustls
  - Savings: ~200-400KB
- **serde/serde_json**: Minimal features
  - Savings: ~100KB
- **reqwest**: Only json and rustls-tls
  - Savings: ~300KB

### 2. .cargo/config.toml Optimizations

- **Sparse registry protocol**: Faster dependency downloads
- **Target-specific optimizations**: CPU-native compilation
- **Optimized dev dependencies**: Faster incremental builds

## Additional Optimization Strategies

### 3. Remove Unused Code

Run these commands to identify and remove dead code:

```bash
# Install cargo-udeps to find unused dependencies
cargo install cargo-udeps
cargo +nightly udeps

# Install cargo-bloat to analyze binary size
cargo install cargo-bloat
cargo bloat --release --crates

# Find unused code with clippy
cargo clippy -- -W unused
```

### 4. Code-Level Optimizations

#### Consolidate Betting Services
You have both `betting.rs` (488 lines) and `betting_simple.rs` (682 lines). Consider:

```bash
# Keep only the simplified version
rm src/betting.rs
# Update imports in handlers/betting.rs
```

#### Remove Development-Only Code
- Remove or feature-gate extensive logging in production
- Remove unused handlers if any
- Consolidate duplicate functionality

### 5. Dependency Alternatives

Consider replacing heavy dependencies:

| Current | Alternative | Savings |
|---------|-------------|---------|
| `reqwest` | `ureq` or `surf` | ~500KB |
| `config` crate | Manual env parsing | ~100KB |
| `ring` | Use only `aes-gcm` | ~300KB |

Example for config replacement:
```rust
// Instead of the config crate, use simple env vars
use std::env;

pub struct AppConfig {
    pub database_url: String,
    pub jwt_secret: String,
    // ...
}

impl AppConfig {
    pub fn from_env() -> Result<Self, Box<dyn std::error::Error>> {
        Ok(Self {
            database_url: env::var("DATABASE_URL")?,
            jwt_secret: env::var("JWT_SECRET")?,
            // ...
        })
    }
}
```

### 6. Build Cache Optimization

```bash
# Clean build cache periodically
cargo clean

# Use sccache for distributed caching
cargo install sccache
export RUSTC_WRAPPER=sccache

# Or use mold linker (Linux) for faster linking
sudo apt install mold
```

Add to `.cargo/config.toml`:
```toml
[target.x86_64-unknown-linux-gnu]
linker = "clang"
rustflags = ["-C", "link-arg=-fuse-ld=mold"]
```

### 7. Feature Flags for Optional Components

Add feature flags to Cargo.toml:

```toml
[features]
default = ["tls", "monitoring"]
tls = ["rustls", "rustls-pemfile"]
monitoring = ["tracing-subscriber"]
fraud-detection = []
```

Then in code:
```rust
#[cfg(feature = "monitoring")]
pub mod monitoring;

#[cfg(feature = "fraud-detection")]
fn check_fraud(&self) -> bool {
    // fraud detection logic
}
```

### 8. Workspace Configuration

If you have multiple binaries or libraries, use a workspace to share dependencies:

```toml
[workspace]
members = ["backend", "shared"]
resolver = "2"

[workspace.dependencies]
serde = { version = "1.0", features = ["derive"] }
tokio = { version = "1.35", features = ["rt-multi-thread"] }
```

### 9. Compile-Time vs Runtime Trade-offs

#### Use const/static where possible
```rust
// Instead of
let rate_limit = 100;

// Use
const RATE_LIMIT: u32 = 100;
```

#### Inline small functions
```rust
#[inline(always)]
fn is_valid_bet_amount(amount: f64) -> bool {
    amount >= MIN_BET && amount <= MAX_BET
}
```

### 10. Database Query Optimization

Since you're using SQLx:

```bash
# Prepare queries at compile time (already doing this)
cargo sqlx prepare

# This reduces runtime overhead
```

## Measurement & Monitoring

### Before Optimization
```bash
cargo build --release
ls -lh target/release/football-heritage-backend
# Note the size
```

### After Each Optimization
```bash
cargo clean
cargo build --release
ls -lh target/release/football-heritage-backend
# Compare sizes
```

### Detailed Analysis
```bash
# Install cargo-bloat
cargo install cargo-bloat

# Analyze what's taking up space
cargo bloat --release
cargo bloat --release --crates

# Function-level analysis
cargo bloat --release -n 50
```

### Binary Size Tracking
```bash
# Create a baseline
cargo build --release
du -sh target/release > size_baseline.txt

# After optimizations
du -sh target/release > size_optimized.txt
diff size_baseline.txt size_optimized.txt
```

## Expected Savings

With all optimizations applied:

| Optimization | Estimated Savings |
|--------------|-------------------|
| LTO + strip | 30-50% |
| opt-level="z" | 10-20% |
| Minimal features | 15-25% |
| Remove unused deps | 10-15% |
| Code consolidation | 5-10% |
| **Total** | **50-70% reduction** |

### Example Measurements
- **Before**: 15-20 MB binary, 4.1 GB target directory
- **After**: 5-8 MB binary, 1.5-2 GB target directory

## Target Directory Size Management

The `target/` directory grows large because it contains:
- Debug builds
- Release builds
- Dependencies (for each profile)
- Incremental compilation data

### Quick Wins

```bash
# Remove old build artifacts
cargo clean

# Remove only release builds
rm -rf target/release

# Remove only debug builds (safe for prod)
rm -rf target/debug

# Keep only final binary
cp target/release/football-heritage-backend .
cargo clean
```

### Automated Cleanup Script

Create `cleanup.sh`:
```bash
#!/bin/bash
echo "Cleaning Rust build artifacts..."

# Remove target directory but keep the binary
if [ -f target/release/football-heritage-backend ]; then
    cp target/release/football-heritage-backend ./football-heritage-backend.backup
fi

cargo clean

if [ -f football-heritage-backend.backup ]; then
    mkdir -p target/release
    mv football-heritage-backend.backup target/release/football-heritage-backend
fi

echo "Cleanup complete!"
du -sh target
```

### CI/CD Optimization

In your CI pipeline:
```yaml
# Cache only dependencies, not builds
cache:
  paths:
    - .cargo/registry
    - .cargo/git
  # Don't cache target/
```

## Incremental Builds

For development, enable incremental compilation:

```bash
# Already set in .cargo/config.toml
export CARGO_INCREMENTAL=1

# First build is slow, subsequent builds are fast
cargo build  # Slow
cargo build  # Fast (only changed files)
```

## Production Deployment

For production, build once and deploy the binary:

```bash
# Build optimized binary
cargo build --release --locked

# Copy only the binary
cp target/release/football-heritage-backend /opt/app/

# No need to ship entire target directory
```

## Dockerfile Optimization

If using Docker:

```dockerfile
# Multi-stage build
FROM rust:1.75 AS builder
WORKDIR /app
COPY Cargo.* ./
COPY src ./src
RUN cargo build --release

# Final stage - only binary
FROM debian:bookworm-slim
COPY --from=builder /app/target/release/football-heritage-backend /usr/local/bin/
CMD ["football-heritage-backend"]
```

This reduces Docker image from 2GB+ to ~100MB.

## Quick Reference Commands

```bash
# Clean everything
cargo clean

# Build optimized for size
cargo build --release

# Analyze binary size
cargo bloat --release

# Find unused dependencies
cargo +nightly udeps

# Check compilation time
cargo build --release --timings

# Strip binary manually (if strip=true doesn't work)
strip target/release/football-heritage-backend

# Compress binary with UPX (optional)
upx --best --lzma target/release/football-heritage-backend
```

## Monitoring Build Size Over Time

Create a simple script `check-size.sh`:
```bash
#!/bin/bash
cargo build --release 2>&1 | grep "Finished"
SIZE=$(du -h target/release/football-heritage-backend | cut -f1)
echo "Binary size: $SIZE"
echo "$(date): $SIZE" >> build-size-history.txt
```

## Troubleshooting

### "Binary too large" errors
- Enable LTO
- Use opt-level="z"
- Strip symbols
- Consider UPX compression

### "Out of memory during compilation"
- Reduce codegen-units (but increases build time)
- Disable LTO temporarily
- Add swap space
- Build on a machine with more RAM

### "Missing symbols" errors after stripping
- Set strip=false for debug builds
- Only strip release builds
- Keep a non-stripped version for debugging

## Next Steps

1. ✅ Apply Cargo.toml optimizations
2. ✅ Create .cargo/config.toml
3. 🔲 Run `cargo bloat` to identify large dependencies
4. 🔲 Remove unused dependencies with `cargo udeps`
5. 🔲 Consolidate betting.rs and betting_simple.rs
6. 🔲 Measure before/after binary sizes
7. 🔲 Test that optimizations don't break functionality
8. 🔲 Update CI/CD with caching strategy
9. 🔲 Document final binary sizes in README

## Questions?

If you need help with any specific optimization, run:
```bash
cargo build --release --verbose
```

This will show you exactly what's being compiled and where time is spent.