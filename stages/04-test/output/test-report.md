# Test Report — Stage 04

## Summary
| Area | Result | Details |
|------|--------|---------|
| Backend compile | ✅ PASS | `cargo check` passes with 3 pre-existing warnings |
| Backend tests | ✅ 16 PASS | All tests pass after fixing test fixtures |
| Frontend build | ✅ PASS | `vite build` production build successful |
| Frontend lint | ⚠️ Pre-existing | ~10 unused-variable warnings in error handlers (pre-existing) |
| New code lint | ✅ PASS | `PlayerProps.jsx` clean after fix |

## Backend Test Fixes Applied

| Test Location | Fix |
|--------------|------|
| `src/auth.rs` (tests) | Added `app_env` to `get_test_config()`, added `role` to second `User` struct, added `create_session` call before `validate_token` |
| `src/betting_simple.rs` (tests) | Added `get_test_config()` with `AppConfig`, updated `CryptoService::new(&config)` calls, added `use crate::config::AppConfig` import |
| `src/crypto.rs` (tests) | Added `app_env` to `get_test_config()` |
| `examples/betting_integration.rs` | Moved to `docs/examples/` (was never compilable — no `[lib]` target in crate) |

**Result: 16/16 tests pass.**

## ML Prediction Accuracy

| Tier | Current Accuracy | Benchmark | Status |
|------|-----------------|-----------|--------|
| Overall (live) | 72.74% | 60-68% typical | ✅ Above benchmark |
| High Confidence | 94.86% | N/A | ✅ Excellent |
| Medium Confidence | 62.55% | N/A | ✅ Good |
| Low Confidence | 46.51% | N/A | ⚠️ Near baseline |

No regression testing performed on the new xG features — requires training pipeline run with new data.

## Frontend Build Output
| Asset | Size | Compressed |
|-------|------|------------|
| JS (index) | 663.62 KB | 155.18 KB (gzip) |
| CSS | 82.64 KB | 11.78 KB (gzip) |
| React vendor | 46.08 KB | 16.51 KB (gzip) |
| UI vendor | 39.03 KB | 10.76 KB (gzip) |

## Recommendations
1. Train model with new xG features and compare accuracy against v2.0.0 baseline
2. Verify player props ETL end-to-end once The Odds API key is configured
