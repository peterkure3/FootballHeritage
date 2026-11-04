# Hosted login/preflight failure — 2026-10-24

## Outcome

**Resolved and verified on the production backend alias.** Deployment `dpl_2QBGEaCYSgKtZHgg4GsW6WrJkejB` is Ready at the existing commit `d8aaa59`. The runtime/database configuration repair restored HTTP serving; neither the Actix API nor the frontend application needed a code change.

| Live check | Result |
|---|---|
| OPTIONS `/api/v1/auth/login`, requesting POST from the frontend | **200**, exact frontend allow-origin, requested headers/method allowed |
| OPTIONS `/api/v1/me/features`, requesting GET from the frontend | **200**, exact frontend allow-origin, requested headers/method allowed |
| OPTIONS login from `https://untrusted.example.test` | **400**, no allow-origin header |
| Anonymous GET `/api/v1/me/features` | **200**, exact frontend allow-origin; read-only database-backed feature lookup succeeded |
| POST `/api/v1/auth/login` with `{}` | **400**, exact frontend allow-origin; required-field validation rejects this before the login handler |

No platform invocation-error header remains on these checks. No real credentials, login attempts against an account, sessions or financial operations were submitted by the verification. The user should refresh the frontend and retry their own login; authenticated login itself was not claimed as tested.

## Root cause

The reported browser CORS errors were accompanied by backend **HTTP 500** responses. Existing Vercel request records route the failing paths to the Rust standalone function (`/rust`); WAF allowed them. Runtime logs show that Actix never reached its listener:

```text
Starting Football Heritage Betting API Server
Environment: Development
User server failed to start: server did not start listening on 127.0.0.1:<assigned-port> within 30s
```

An earlier deployment also reported `Failed to load configuration: DATABASE_URL must be set`. In the current source, the database pool must connect before the server binds. The logged startup reached the database-connect stage but did not log successful pool initialization before Vercel's 30-second startup deadline. The user confirmed that the backend Production `DATABASE_URL` had not pointed to the restored Neon `football_heritage` database, then updated it securely in Vercel. No database credential was retrieved or pasted into chat.

The browser cannot accept a preflight response without `Access-Control-Allow-Origin`, including platform-generated 500 responses. Adding a wildcard CORS header would not restore a backend that fails before serving HTTP. The existing Actix CORS layer already handles OPTIONS before feature-policy middleware and allows Authorization and Content-Type for explicitly configured origins.

## Configuration repair

- Added the previously absent backend Production **`APP_ENV=production`** and **`RUN_MIGRATIONS=false`**, preserving every existing environment value. Verified both values through non-secret configuration reads.
- The user confirmed saving the correct TLS-enabled Neon staging `DATABASE_URL`, an `ALLOWED_ORIGINS` list including `https://football-heritage-frontend.vercel.app` exactly (no trailing slash), `HOST=0.0.0.0`, and `HTTPS_ENABLED=false`.
- Secret-typed variables are unreadable through Vercel's API. Their values were not inferred from absent API fields. Origin/database/host settings are user-confirmed; the new two Config settings are API-verified.
- Kept certificate verification, the strict origin allowlist, authentication and financial feature restrictions intact. No Rust API or React application source change was necessary.
- Redeployed the existing backend commit `d8aaa59` using the user's existing production-deployment approval. Candidate URL: `https://footballheritage-backend-ap0pfaryg-peterkure3s-projects.vercel.app`.

The first repaired deployment became Ready, but an OPTIONS probe still returned HTTP 500 with `X-Vercel-Error: FUNCTION_INVOCATION_FAILED`. Its runtime log identified the next exact failure: **`Failed to load configuration: Invalid HTTPS_ENABLED`**. The user's intended boolean had been stored in a format Rust could not parse. Normalized only the three known non-secret HTTP settings to readable Config values: literal `false`, bind host `0.0.0.0`, and the exact frontend origin. API reads then verified these three settings plus production mode and disabled migrations. Database URLs, tokens and encryption/authentication keys were not retrieved or changed.

A second redeployment of the same existing commit was initiated at `https://footballheritage-backend-lyonk0l0x-peterkure3s-projects.vercel.app` (`dpl_2QBGEaCYSgKtZHgg4GsW6WrJkejB`). The initial OPTIONS verification was also affected by a transient Windows/Node connect timeout; Windows curl reached the endpoint and exposed the HTTP 500. The verification script supports that certificate-verified Windows transport as a fallback, without disabling TLS checks or changing DNS/proxy settings.

The initial array-shaped environment request was rejected by the CLI with HTTP 400 before any settings changed. Reissuing the two additions as individual JSON objects succeeded and preserved existing variables. The later normalization step deliberately replaced only the three non-secret HTTP values described above.

## Verification

Before the safeguards were configured, diagnosis used only platform log/configuration reads; no new application request was sent that could trigger startup migrations. Local code inspection established that OPTIONS bypasses the feature-policy database lookup, and the CORS middleware intercepts preflight requests. Deployment status/readiness is checked through the platform before sending the post-repair OPTIONS probes.

The manual verification command is `node stages/05-deploy/output/vercel-cors-20261024/verify-preflight.mjs`. It sends only OPTIONS requests for `/api/v1/auth/login` (POST preflight), `/api/v1/me/features` (GET preflight), and an untrusted-origin negative check. `verify-responses.mjs` additionally verifies the read-only feature response and the login extractor's empty-JSON rejection. Neither script supplies credentials or mutates application records. Results and sanitized before/after runtime evidence are stored in the companion directory. Windows curl retained normal certificate verification when used to work around intermittent Node connect timeouts.

No migrations, wallet initialization/reset utilities, financial operations or manual Neon writes were executed. Existing local changes to ignore files, migration line endings, frontend environment and unrelated index notes were preserved.
