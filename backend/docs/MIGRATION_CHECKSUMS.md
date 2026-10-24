# Migration byte integrity

SQLx checksums the exact migration bytes. With `core.autocrlf=true`, the earlier checkout converted `20261007000001_add_ai_picks.sql` and `20261008000001_add_rust_rag_chat.sql` from their originally applied LF bytes to CRLF. Their SQL content was unchanged, but SQLx correctly rejected the different checksums.

The original LF bytes are restored. `.gitattributes` now keeps migrations from October 2026 onward in LF on every platform. Older migrations retain their existing text handling because their applied history contains mixed line endings; they were not globally renormalized. The not-yet-applied wallet-index source was also normalized to the existing Git LF blob before use. No migration SQL statement or version was changed.

Verification on 2026-10-24:

- Read-only comparison initially identified exactly the two LF/CRLF mismatches among 16 applied records.
- `cargo check --locked` passed after restoring the files.
- A compiled `sqlx::migrate!` verifier matched all 18 records present at its final read. It used a read-only transaction and never called `Migrator::run`; it did not apply the additional records.
- Git attributes enforce LF for the affected migrations while leaving older source bytes unchanged.

Rebuild with Cargo before reusing an old executable: migration checksums are embedded in the binary. SQLx 0.7.4 emits `include_str!` references so Cargo tracks changes to existing migration files. Do not fix this error by deleting migration history, updating stored checksums, disabling validation, or rewriting applied SQL. A checksum that does not match an original source/line-ending variant requires its own investigation. Compare target-database checksums read-only before moving older migration history across platforms.
