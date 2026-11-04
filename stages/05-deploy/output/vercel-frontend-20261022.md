# FootballHeritage frontend on Vercel

Deploy the existing `frontend/` React/Vite application. Use `frontend` as the
Vercel project Root Directory, `npm run build` as Build Command, and `dist` as
Output Directory. `frontend/vercel.json` includes the SPA rewrite needed for
direct visits to client-side routes. Local environment files are excluded from
CLI uploads by `.vercelignore`.

## Required service connections

Set these public build-time variables in the Vercel project before deploying:

| Variable | Value |
|---|---|
| `VITE_API_URL` | Hosted Rust backend HTTPS URL ending in `/api/v1` |
| `VITE_PIPELINE_API_URL` | Hosted Python pipeline HTTPS URL ending in `/api/v1` |

Both currently fall back to localhost in the frontend source. A production build
without hosted values cannot provide working remote authentication/data access.
Redeploy after changing Vite environment variables: they are embedded at build time.

The Rust backend and Python pipeline need their own API services and background
workers. Current Vercel Services and container-image Functions can host HTTP servers,
including Rust, without converting each handler into an individual function. Vercel
Daemons can run background containers, subject to beta availability and limits.
These deployment adaptations have not been implemented. See the companion
`neon-vercel-assessment-20261022.md`. The simulation baseline is a CLI research
artifact and is not automatically exposed through the frontend or an inference API.

The `frontend/vercel.json` configuration is for a standalone frontend deployment.
A combined Vercel Services deployment would instead use repository-root service
configuration and explicit API routing; do not treat this frontend-only file as
the full-stack deployment manifest.

## PostgreSQL

Current project databases are `football_heritage` for the Rust application and
`football_betting` for the Python pipeline. Preserve their separate schemas/data.
Provision managed PostgreSQL or use existing hosted PostgreSQL; do not assume
that deploying frontend files migrates either database.

Database URLs, JWT secrets, encryption keys and provider API credentials belong in
the backend/pipeline host settings, never in any `VITE_*` variable or static files.
Configure Rust `HOST=0.0.0.0`, its host-assigned `PORT`, and `ALLOWED_ORIGINS` for
the final Vercel/custom domain. The pipeline uses `API_ALLOWED_ORIGINS` via config;
check its environment mapping when preparing that service.

## Deployment sequence

1. Confirm backend/pipeline hosting and database destinations.
2. Back up existing data and review migrations before changing a hosted database.
3. Deploy and smoke-test the HTTPS APIs against their intended databases.
4. Configure Vercel public API URLs and API CORS origins.
5. Deploy from `frontend/` using the linked Vercel project.
6. Verify `/`, a direct client route, authentication, prediction requests and failed
   requests; confirm the browser never calls localhost in supported active flows.

No database migration, paid resource provisioning or backend deployment has been
performed by preparing this frontend configuration.

References: https://vercel.com/docs/frameworks/frontend/vite and
https://vercel.com/docs/postgres (external Postgres integrations).
