# Backend warning fixes — 2026-10-13

Compared warning fixes with `C:/Users/Peter Kure/Downloads/FootballHeritage-multisport-framework` and ported the relevant changes into this workspace.

- Removed unused `Claims` and `HttpResponse` imports.
- Recorded withdrawal metrics after a successful transaction commit. Preserved this workspace's newer transaction schema repair; the reference wallet SQL predates that repair.
- Enabled event date and all eight odds/spread/total update fields. Used an explicit text-to-timestamp cast for the string date parameter.
- Removed the unused user-limits request type after confirming no consumers.
- Preserved the reserved superadmin middleware with narrowly scoped dead-code allowances, matching the reference approach.
- Removed unconditional Windows `/LTCG` linker arguments. The reference still had this flag; release LTO remains configured in Cargo.toml.

## Verification

- `SQLX_OFFLINE=true cargo check --offline`: passed, no listed source warnings.
- `SQLX_OFFLINE=true cargo test --offline --no-fail-fast`: 32 passed across the backend and utility binaries; database regression ignored by default.
- `SQLX_OFFLINE=true cargo test --offline update_event_persists_date_and_odds -- --ignored`: passed against local PostgreSQL using connection-local temporary tables. Verified nine previously ignored fields, timezone conversion, updater identity, and a subsequent single-field update preserving the other values. No persistent event or audit records were changed.
- No `/LTCG` warning during test linking.
- `rustfmt --edition 2021 --check` on all six changed Rust files and scoped `git diff --check`: passed.

Existing limitations: SQLx 0.7.4 still emits its future-compatibility notice. Whole-backend `cargo fmt --all -- --check` reports pre-existing formatting differences in `src/handlers/ai_picks.rs` and `src/main.rs`; those unrelated edits were preserved. Fallow was unavailable locally (`npx --no-install fallow --summary` could not find an installed package); Rust usage searches and compiler checks were used for this change.

The workspace already contained extensive uncommitted work. No commits were created and unrelated changes were preserved.
