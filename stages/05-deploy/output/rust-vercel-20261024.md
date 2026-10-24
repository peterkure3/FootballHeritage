# Rust Vercel failure and Windows database launchers — 2026-10-24

## Outcome and confidence

Reproduced the exact JavaScript `Cannot read properties of undefined (reading 'target')` exception using the actual Cargo configuration and the upstream adapter expression. Added an empty `[build]` table as a minimal workaround. This is a valid Cargo configuration exposing an unsafe adapter assumption, not a Rust source/compiler error. The exact remote stack, adapter version, project settings and deployed Git SHA remain unverified: the Vercel connector located `footballheritage-backend` but team-scoped reads returned 403. A consent link was supplied; no cloud settings or deployments were changed.

The previous binary ambiguity is already addressed by commit `862f5cd`: `default-run = "football-heritage-backend"`, `autobins = false`, explicit targets and feature-gated maintenance tools. Do not remove these protections or use maintenance tools as deployment entrypoints.

## Evidence

- `backend/Cargo.toml`: API at `src/main.rs`; `migrate` is a separate operator binary; `init_admin`, `init_wallets` and `reset_wallets` require `maintenance-tools`. Cargo metadata confirms the default binary. Feature-gated binaries still appear in metadata, so hiding them behind a feature alone does not disambiguate an adapter that enumerates all targets. `default-run` does.
- `backend/Cargo.lock`: format 4, unchanged from Git. Locked Actix 4.11.0, SQLx 0.7.4, time 0.3.44 and home 0.5.11. No dependency upgrade or lockfile regeneration was necessary.
- No `rust-toolchain` file or global Cargo build target was found. Windows toolchain: Rust/Cargo 1.99.0, `x86_64-pc-windows-msvc` only. Docker base: Rust/Cargo 1.90.0, `x86_64-unknown-linux-gnu`. Existing Linux flags request host CPU instructions and lld; the Dockerfile already overrides them with portable `RUSTFLAGS`. Their suitability on a remote Vercel builder still needs verification.
- `.cargo/config.toml` existed with target-specific flags and profiles, but no `[build]`. Upstream reads `cargoBuildConfiguration?.build.target`, guarding the config but not the `build` object. The added table parses as `{}`; reading its missing `target` returns `undefined`, preserving the host artifact location.
- Active Vercel config: `frontend/vercel.json`, for Vite only. No root or backend `vercel.json` or local `.vercel` project link exists. `deploy/vercel-services.example.json` is an inactive combined-container example. `.github/workflows/vercel-preview.yml` builds the frontend. No backend Vercel configuration was invented or activated.
- Intended backend project root: `backend`; entrypoint: `src/main.rs` or binary `football-heritage-backend`. These are recommendations from the repository and adapter resolution rules, not confirmed dashboard values. The reported four-binary error predates the current fifth target (`migrate`), so verify the deployed commit.

## Runtime compatibility correction

The public handler guide describes `api/` Rust Functions using `vercel_runtime`. Current upstream `@vercel/rust` source also has standalone HTTP proxy mode for whole-app binaries without that dependency. It chooses the Cargo default binary and passes an assigned `PORT`. Actix starts `HttpServer`, reads `HOST`/`PORT` through `AppConfig`, and can satisfy that contract without an API rewrite. The error is therefore not evidence that Actix itself is incompatible.

Compatibility depends on the actual installed adapter supporting standalone mode and the correct whole-app entrypoint. Older handler-only runtimes need a bridge or a container. Vercel container runtime is another option, subject to account/runtime availability. Existing process-local sessions/rate limits and startup database dependencies still prevent claiming production readiness under replacement, autoscaling or scale-to-zero. Keep the existing persistent single-replica container topology until these behaviors are tested.

Sources inspected (upstream `main` is mutable; its package manifest reported 8.0.1):

- [Adapter build and dev-server config access / standalone proxy](https://github.com/vercel/vercel/blob/main/packages/rust/src/standalone-server.ts)
- [Cargo configuration parsing and binary resolution](https://github.com/vercel/vercel/blob/main/packages/rust/src/lib/cargo.ts)
- [Artifact path resolution](https://github.com/vercel/vercel/blob/main/packages/rust/src/lib/compile.ts)
- [Adapter Windows prebuilt restriction](https://github.com/vercel/vercel/blob/main/packages/rust/src/index.ts)
- [Rust function handler documentation](https://vercel.com/docs/functions/runtimes/rust)
- [Vercel HTTP containers](https://vercel.com/docs/functions/runtimes/container)
- [Railway Dockerfiles](https://docs.railway.com/builds/dockerfiles)

## Verification

Complete command outputs are in [rust-vercel-20261024/](rust-vercel-20261024/).

| Check | Result |
|---|---|
| Parsed real Cargo config with the adapter property access | Exact original exception reproduced; empty-table fix passes (`adapter-reproduction.log`, reproducible CJS probe included) |
| `SQLX_OFFLINE=true cargo check --locked`, from `backend/` | Pass, exit 0 (`cargo-check.log`) |
| `SQLX_OFFLINE=true cargo test --locked --bin football-heritage-backend -- --skip database_policy_and_http_enforcement --skip financial_operations_are_serialized_and_balance_reads_do_not_create_wallets` | 31 passed, 0 failed, 3 ignored, 2 explicitly filtered; exit 0 (`cargo-test.log`) |
| Backup/restore BAT `--help` | Both exit 0, no credential prompts or database operations (`backup-help.log`, `restore-help.log`) |
| Interpreter fallback with isolated command stubs | 5 tests passed: prefer `py -3`, fallback `python`, failed Store alias to `python3`, no interpreters, all failing (`python-launcher-tests.log`) |
| Fallow repository summary | Ran successfully as an analysis command; gate exit 1 reports 38 dead-code issues, 43 clone groups, and 177 functions above the health threshold (`fallow-summary.log`). These findings are outside this config/launcher fix; no broad cleanup was attempted. |
| Fallow post-change audit | Final exit 0: zero new dead-code, complexity or duplication findings (`fallow-audit.json`). The initial audit flagged the manually invoked adapter probe as an unimported file; its documented diagnostic purpose is now annotated. Verdict remains `warn` because root `node_modules` is absent, limiting dependency classification. |
| Existing Dockerfile build | Failed, missing `/app/target/release/football-heritage-backend` (`docker-build.log`) |
| Isolated base-image container, network disabled | Rust/Cargo 1.90.0 work (`docker-toolchain.log`) |
| BuildKit-only base toolchain probe | `/usr/local/cargo/bin/rustup` is zero bytes during build; cargo/rustc/rustup silently return without output (`docker-build-toolchain.log`) |

The Docker probe reproduces the missing-toolchain behavior without project source. This is a local image/build-layer problem, not an established Dockerfile or API defect. Refresh/repair the local Docker build environment and rebuild before accepting a Railway image; no speculative Dockerfile change was made. No successful Linux release build is claimed. Native Vercel prebuilt compilation on Windows is explicitly rejected by the upstream adapter, so the reproduction here targets the failing config-access step rather than claiming a full local Vercel build.

SQLx 0.7.4 reports its existing future-compatibility warning. Initial diagnostic attempts encountered the sandbox process-launcher failure and a missing output directory; the requested check was rerun successfully from `backend/` after preparing the correct directory. Only final complete check/test outputs are used above.

Final `git diff --check` passed, and `git diff --exit-code -- backend/Cargo.toml backend/Cargo.lock` confirmed both files are unchanged.

## Backup and restore launcher fix

Both `.bat` scripts previously invoked `python` directly, selecting Windows' Store execution alias on this workstation. They now call `scripts/find_python.bat`, which probes actual Python 3 execution using `py -3`, `python`, then `python3`. Failed probes are quiet. If none works, it prints installation/alias guidance and exits nonzero before requesting a password. `setlocal` scopes launcher variables; quoted argument assignment supports backup-folder paths with spaces. Child command exit codes survive the existing pause. The Python database implementations are unchanged.

## Remaining blockers and Railway fallback

1. Team access is required to read the original build logs, confirm exact adapter/version, root, entrypoint, Git SHA and environment. No remote fix or deployment success is claimed.
2. Repair the zero-byte BuildKit toolchain layer and produce a successful locked Linux container build. Do not infer Linux success from a Windows check.
3. If the selected Vercel runtime lacks standalone support or its lifecycle is unsuitable, use a Railway Docker service with Root Directory `backend`, existing `Dockerfile`, startup `/app/server`, one replica and platform-assigned `PORT`; set `HOST=0.0.0.0`, `HTTPS_ENABLED=false`, `APP_ENV=production`. No API rewrite is needed.
4. Before hosted verification, supply the existing secret/config contract and exact frontend CORS origin through host settings. Set `RUN_MIGRATIONS=false` and keep demo wallet funding disabled. Use a separately approved isolated staging database and reviewed migration process; starting the API otherwise connects to PostgreSQL and defaults to running migrations. No database-backed startup was attempted here.

No wallet initialization/reset utility, migration binary, production database command, backup, restore, real-money enablement or deployment was executed. Pre-existing working-tree changes were preserved.
