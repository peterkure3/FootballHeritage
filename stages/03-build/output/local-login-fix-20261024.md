# Local frontend login routing repair — 2026-10-24

The local frontend used `http://localhost:8888/api/v1`. On this machine,
`localhost:8888` reached a Docker/WSL service with a different API contract,
while `127.0.0.1:8888` reached this repository's native Rust backend.

Changed only `VITE_API_URL` in the existing local `frontend/.env` to
`http://127.0.0.1:8888/api/v1`, preserving other local settings. Vite picked
up the environment change. No containers or existing account credentials changed.

## Verification

- Compared `/health` and nonexistent-account login responses on both hosts:
  localhost returned a `success/data` envelope; IPv4 returned the Rust API contract.
- Rust CORS preflight accepted `http://localhost:5173` with HTTP 200 and the
  matching `Access-Control-Allow-Origin` header.
- Existing browser smoke test registered an isolated account and reached the
  dashboard, then failed on a competing navigation after logout before login.
- A separate real Chromium check created an isolated account, revoked its initial
  session, logged in through the frontend (HTTP 200), followed `/profile`, reloaded
  with authentication intact, fetched the authenticated profile (HTTP 200), and
  revoked the test login session (HTTP 200). No mocked API responses.
- Two isolated QA accounts remain for normal administrative cleanup; no bets or
  deposits were made. IDs: `480e1e62-0186-4756-b4c8-08052e8a3c2e` and
  `afa28e1f-c34c-407c-a85d-5c2fe1256b25`. Credentials were generated in memory.
- Fallow summary still reports existing repository findings: 37 dead-code issues,
  43 clone groups, 177 functions above the complexity threshold. Root dependency
  resolution warning remains. No application source files changed.

Open `http://localhost:5173/login` and refresh any tab opened before the fix.
Keep the explicit IPv4 API address while the conflicting Docker/WSL listener
remains present.
