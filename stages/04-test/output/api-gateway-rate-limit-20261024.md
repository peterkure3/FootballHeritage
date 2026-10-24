# Local API gateway and rate-limit correction

## Reported failures

- `/api/v1/pipeline/matches?limit=100` and `/api/v1/pipeline/prediction-dashboard/fixtures?page=1&page_size=6` returned 400 because the Rust gateway had no upstream URL or internal token. This was server configuration failure, not invalid pagination or CORS.
- Feature checks and login returned 429. Governor's refill period was incorrectly set to the entire quota window: after exhausting the burst, a 100/minute quota restored only one request per minute. Multiple feature consumers also each scheduled polling.

## Corrections

- All three limiter implementations share a quota constructor using `window / request_count` as the per-request refill period. Existing burst sizes and independent login, registration, betting and financial limits remain enforced.
- The application feature boundary owns the 15-second refresh timer. Navigation and other feature consumers share its cached query, with a 15-second freshness period. Failed policy requests continue to deny feature access; administrative invalidation remains supported.
- The Rust pipeline gateway validates its server configuration, normalizes `/api/v1` exactly once, and reports missing configuration as 503 `UPSTREAM_NOT_CONFIGURED`. Internal credentials are not returned to browsers. Existing feature and administrative guards remain in place.
- Local development requires `PIPELINE_API_URL=http://127.0.0.1:5555/api/v1` in `backend/.env` and the same newly generated `PIPELINE_INTERNAL_TOKEN` (at least 32 characters) in both `backend/.env` and `pipeline/.env`. These ignored files must never be committed. Restart both services after configuration changes; the Rust session store requires a fresh login after restart.

## Verification

- `cargo check --locked` and `cargo check --locked --all-features`: passed.
- `cargo test --locked --all-features`: database-dependent tests excluded or ignored because no verified disposable test database was provided; remaining tests passed. Added a simulated-clock regression proving both burst enforcement and replenishment after six seconds for 10/minute, plus three gateway tests covering configuration validation, 503 errors, and actual HTTP forwarding of both reported paths, queries and private headers.
- `npm run lint` and `npm run build` in `frontend`: passed, including TypeScript.
- `npx playwright test tests/feature-management.spec.js --project=chromium --reporter=line`: 4 passed, including shared polling, disabled-route/navigation protection, fail-closed behavior with login accessible, and admin mutations/audit display.
- Local API executable rebuilt successfully and localhost services reloaded. Eight live smoke checks passed: `/health` 200, `/ready` 200, `/me/features` 200, both originally failing pipeline URLs 200, direct unauthenticated Python access 403, internally authenticated Python health 200, and malformed login validation 400 rather than 429. The login probe deliberately did not authenticate or create an account; successful credential-based login was not retested.
- The separate isolated staging session remained running. The first executable build encountered its Windows file lock; rebuilding the localhost API in its original target directory resolved the lock without stopping that staging process.

These are local checks. No production deployment, database repair, real-money operation, cloud credential change, or verification of the pending staging infrastructure is implied.
