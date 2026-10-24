# Rust deployment binary selection

The API package now sets `default-run = "football-heritage-backend"`. Its explicit target is `src/main.rs`, which contains the existing Actix application. This removes the ambiguous default binary choice; it does not convert the application into a native Vercel Rust Function.

Automatic binary discovery is disabled. Targets are declared explicitly:

| Target | Purpose | Availability |
| --- | --- | --- |
| `football-heritage-backend` | Existing HTTP API and Rust RAG agent | Default executable |
| `migrate` | Existing one-shot additive migrations | Explicit operator command; never the container startup command |
| `init_admin` | Administrative initialization | Requires `maintenance-tools` |
| `init_wallets` | Wallet initialization | Requires `maintenance-tools` |
| `reset_wallets` | Wallet reset | Requires `maintenance-tools` |

Normal API builds should select the target explicitly:

```sh
cargo build --locked --release --bin football-heritage-backend
```

Without the opt-in feature, Cargo refuses to build/run any of the three maintenance targets, even when its name is supplied. They remain available for separately authorized operator work using `--features maintenance-tools --bin TARGET`. Do not enable that feature in deployment build commands. CI uses `cargo test --locked --all-features` to compile their code and run unit-test harnesses; this does not call their operational `main` functions.

The existing Dockerfile builds/copies only the API and dedicated migrator and starts `/app/server`. No initialization/reset executable is copied into its runtime image. Existing startup migration behavior is preserved: `RUN_MIGRATIONS=false` is needed when using the separate migrator and non-owner runtime role. Historical bootstrap seeding inside existing migrations is a separate previously documented release risk; this change does not rewrite or execute those migrations.

## Separate Vercel runtime blockers

Repository inspection found no active backend `vercel.json`, `Dockerfile.vercel`, or `vercel_runtime` dependency. `deploy/vercel-services.example.json` is an optional example, not an active root configuration. The frontend's Vercel configuration belongs to the Vite project and does not adapt the Rust API.

1. **Rust runtime modes (corrected 2026-10-24):** the documented `api/` function-handler mode uses `vercel_runtime`. However, the current upstream `@vercel/rust` adapter also selects standalone HTTP proxy mode for whole-app binaries without that dependency. Our Actix `HttpServer` can satisfy that mode by honoring `PORT`; adding `vercel_runtime` or rewriting routes is not required for the standalone adapter. Confirm the deployed adapter version and entrypoint before choosing a mode. See [upstream standalone implementation](https://github.com/vercel/vercel/blob/main/packages/rust/src/standalone-server.ts) and [handler documentation](https://vercel.com/docs/functions/runtimes/rust).
2. **Container runtime:** Vercel supports HTTP containers in Beta through a `Dockerfile.vercel` or an explicitly selected container service entrypoint. That is a different deployment model and has not been activated or verified here. It scales instances down, so it must not be treated as an always-on host. See [Container Runtime](https://vercel.com/docs/functions/runtimes/container).
3. **Sessions/rate limits:** the current API stores these in process-local memory. Automatic multi-instance scaling would lose consistent authentication/rate-limit state. Use the existing single-instance persistent-host plan until shared state is implemented and tested.
4. **Artifact/configuration:** the previously documented local container-build failure remains unresolved. Verify the intended Git SHA and `backend` project root: current source also declares `migrate`, whereas the reported error listed only four binaries. Dashboard runtime settings and a hosted deployment were not verified by this change.

No adapter, deployment, account/bootstrap operation, database connection or migration is introduced by this fix. Routes, authentication, feature middleware, migration files and financial restrictions remain unchanged. Staging URLs, private-service ingress and secure environment settings must be verified before hosted runtime acceptance.

## Adapter config failure — 2026-10-24

The subsequent `Cannot read properties of undefined (reading 'target')` is reproducible from the adapter expression `cargoBuildConfiguration?.build.target`. Our valid `.cargo/config.toml` existed without a `[build]` table. Optional chaining guards the config object, but not its missing `build` property. The project workaround adds an empty `[build]` table, retaining Cargo's host target and artifact layout. Do not force a Linux target globally: local Windows builds must continue to work. The upstream fix would guard `build` as well.

The same expression exists in standalone build and dev-server startup; the legacy handler builder also reads this property. The upstream source explains both reported errors: standalone binary selection respects `default-run`, then artifact discovery encounters the missing table. This is an adapter assumption about a valid Cargo configuration, not a Rust compiler diagnostic. The exact failed remote build's adapter version and stack remain unverified because team-scoped API access returned 403.

Local verification and complete logs: [2026-10-24 investigation](../../stages/05-deploy/output/rust-vercel-20261024.md). No Cargo manifest, lockfile, API route or migration change is needed for this exception.

## SQLx compile-time database failure — authenticated follow-up

The later hosted build at commit `3eae0b3` passed binary resolution but failed with 16 SQLx macro `Connection refused` errors. Cargo configuration now defaults `SQLX_OFFLINE=true` through `[env]`, using the checked-in `.sqlx` cache without connecting to a database at build time. Existing environment overrides remain supported for separately authorized query-cache maintenance. This build setting does not disable runtime migrations: explicitly configure `RUN_MIGRATIONS=false` and `APP_ENV=production` before invoking the deployed API.

Authenticated inspection found the hosted project root set to `backend/src`; use the package root `backend` for a reviewed deployment configuration. Both Vercel projects currently designate `feature/footballheritage-frontend` as their production branch. No project root, environment scope, deployment or database was changed by this follow-up. See the [updated hosted findings](../../stages/05-deploy/output/vercel-staging-20261024.md).

## Persistent-container PORT contract

`AppConfig::from_env` reads `PORT` as a `u16`; `main.rs` constructs its bind address from `config.host` and `config.port` and passes it to Actix. The source fallback is `8080`; the existing Docker image overrides it to `8888`. Set `HOST=0.0.0.0` and `HTTPS_ENABLED=false` behind trusted TLS ingress and let the host's `PORT` override the image default. For a future Vercel container project, configure its `PORT` setting explicitly to match the server; an image's `EXPOSE` declaration alone is not an ingress configuration.

Verification includes Cargo metadata/default-target checks, refusal to build maintenance targets without their feature, locked checks of default/all-feature targets, and unit tests. An isolated probe uses the actual `AppConfig` implementation and an Actix listener with an injected non-default `PORT`, without starting the API or accessing a database. Full API/container startup and database-backed tests remain pending verified staging configuration.

Verification on 2026-10-23:

- `cargo check --locked` and `cargo check --locked --all-features`: passed.
- `cargo test --locked --all-features` with the two database-backed feature/financial checks explicitly filtered: 36 unit tests passed, 3 existing DB tests ignored. No database was contacted.
- The three maintenance targets were each rejected by Cargo without `maintenance-tools`.
- Actual configuration/Actix listener probe: bound `0.0.0.0:60213` using injected `PORT=60213`. Its initial dummy fixture lacked the required internal token; supplying a test-only value fixed that fixture without weakening validation.
- `Cargo.lock`, API source and migration files are unchanged. The existing SQLx 0.7.4 future-compatibility warning remains; no Vercel build, hosted startup or deployment was performed.
