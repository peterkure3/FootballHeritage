# Neon + Vercel assessment for FootballHeritage

Checked 22 October 2026 against current official documentation and repository code.
Decision: viable candidate for a full-stack proof of deployment. No cloud resources
have been provisioned, no database migrated, and no production deployment published.

## Recommended component map

| Component | Candidate destination | Project-specific work |
|---|---|---|
| React/Vite frontend | Vercel static frontend/service | Build passes; standalone SPA config is prepared |
| Rust/Actix API | Vercel Services with container runtime | Add a Linux `Dockerfile.vercel`; verify HTTP startup, migrations, pooling and runtime state |
| Python/FastAPI API | Vercel Python service or container | Audit startup/import dependencies, model loading, write paths and request limits |
| Scraping/training/simulation workers | Vercel Daemons, subject to beta access/limits | Replace Task Scheduler/local-directory assumptions with durable job inputs, checkpoints and external storage |
| Application PostgreSQL | Neon `football_heritage` | Preserve schema/data; separate app credentials and reviewed migration access |
| Pipeline PostgreSQL | Neon `football_betting` | Preserve schema/data; explicitly map its own connection URL |
| Raw event archives and model artifacts | Durable object storage, e.g. Vercel Blob | Worker scratch disks are not the durable dataset/model store |

Neon supplies PostgreSQL, not the Rust/Python processes. Vercel hosts the application
compute. Keep browser code behind the existing backend API and existing JWT auth;
adopting Neon storage does not require replacing application authentication.

## What current Vercel documentation changes

An earlier recommendation that the Rust backend necessarily needed a different
host was too restrictive. Vercel announced Services and Dockerfile-based HTTP
backends on 30 June 2026. Current Services documentation supports `runtime:
"container"`; the Rust function runtime is also documented, but adapting Actix
through a container is the more direct initial path than rewriting every handler.

Container Functions run an HTTP server on `$PORT` (default routing port 80), remain
stateless, and retain function lifecycle/resource limits. They are not equivalent
to an unrestricted always-on VM. Docker Compose itself is not a deployment target.
The Rust service must bind `HOST=0.0.0.0`, honor `PORT`, and let Vercel terminate
public HTTPS rather than requiring local TLS certificate files.

Services and container capabilities are beta. Vercel Daemons are documented as
public beta on all plans, with production-only deployments, manual instance counts
and ephemeral storage; preview workers, automatic scaling and persistent storage
are not supported during the beta. Account entitlement, target regions, resource
limits and cost suitability remain deployment-time checks.

Sources:
- https://vercel.com/docs/services
- https://vercel.com/changelog/run-multiple-frameworks-in-one-project-with-vercel-services
- https://vercel.com/changelog/bring-your-dockerfile-to-vercel-functions
- https://vercel.com/docs/daemons

## Neon compatibility and required database changes

The inspected Rust backend uses SQLx/PostgreSQL and migrations requiring
`uuid-ossp`; Neon documents this extension. Keep the two existing databases rather
than merging their different schemas during a hosting migration. They may share
a Neon project's compute initially, subject to sizing and permissions; separate
projects remain an option for independent capacity and isolation.

Repository issues to address before using production Neon connections:

1. `backend/src/main.rs` opens a pool with minimum 10 and maximum 50 connections
   **per instance**. Make those limits configurable and size conservatively for
   autoscaling, including the separate RAG pool in `backend/src/rag.rs`.
2. The Rust server automatically runs SQLx migrations using the request-serving
   pool at startup. Separate reviewed migrations onto a direct Neon connection or
   a release job. Do not simply feed the pooled URL to all migration operations:
   transaction pooling does not support session-level advisory locks.
3. `pipeline/config.py` currently constructs its database URL from `DB_HOST`,
   `DB_USER`, `DB_PASSWORD`, etc. It does not consume the integration's
   `DATABASE_URL` automatically. Add explicit support for a separate pipeline URL,
   including SSL options and correctly encoded credentials.
4. Rust and Python use different databases. A single shared `DATABASE_URL` from
   an integration is insufficient unless each service maps its intended database
   explicitly. Plan distinct app, pipeline and direct-migration secrets; never
   expose them via `VITE_*`.
5. The ETL contains reusable staging tables and transaction-scoped advisory locks.
   Keep their transaction boundaries intact and test them against the chosen
   connection type. Comments calling a pandas `to_sql` staging table temporary do
   not establish that it is a PostgreSQL session-temporary table.

Neon's Vercel-managed integration provides `DATABASE_URL` (pooled) and
`DATABASE_URL_UNPOOLED` (direct). Use pooled connections for compatible concurrent
API traffic and direct connections for migrations, dumps/restores and operations
requiring session state. Do not disable SQLx prepared statements indiscriminately;
test against Neon's documented supported protocol behavior and actual queries.

The integration can create database branches for Vercel preview deployments.
Preview schema changes must never target the production database. Region selection
should place database and API compute close together; it should follow measured
latency and supported regions, not the browser's geographic location alone.

Sources:
- https://neon.com/docs/guides/vercel-managed-integration
- https://neon.com/docs/connect/connection-pooling
- https://neon.com/docs/manage/databases
- https://neon.com/docs/extensions/uuid-ossp

## Evidence and next deployment step

`npm run build` from `frontend/` passed TypeScript checking and Vite production
bundling. Added standalone frontend `vercel.json` and `.vercelignore`; no API or
database code was changed for this assessment. No successful backend container
build, Neon connection or full-stack smoke test is claimed.

The Vercel CLI account check failed with a worker timeout and reported logged out.
No authenticated Vercel team/project or Neon account has been verified. Authentication
and a chosen target project are prerequisites for publishing, checking actual beta
availability and configuring the integration. Do not send database passwords in chat;
set secrets through the deployment platform's environment/secret settings.

Next: prepare the repository-root Services configuration, container build definitions,
database URL/pool/migration changes and an explicit durable worker/storage plan.
Validate against an isolated Neon database branch, then deploy a preview and smoke
test login, API routes, predictions, database writes and job recovery before moving
production data or domains.
