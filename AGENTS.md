# AGENTS.md — Layer 0: Workspace Identity & Routing

## Identity
You are operating in the **FootballHeritage** workspace. A comprehensive AI-powered sports betting platform with real-time odds, prediction analytics, responsible gambling features, and an end-to-end data pipeline for sports data ingestion, modeling, and API serving.

## Core Directories
| Path | Purpose |
|------|---------|
| `stages/` | ICM pipeline — numbered stage folders |
| `_config/` | Brand, conventions, tech-stack, glossary |
| `shared/` | Cross-stage reference material |
| `setup/` | Onboarding questionnaire |
| `backend/` | Rust + Actix-web API server, database migrations, business logic |
| `frontend/` | React + Vite web application, UI components |
| `pipeline/` | Python + FastAPI data pipeline — ETL, scraping, ML predictions |
| `chatbot/` | Node.js + Genkit AI chatbot for betting advice |
| `scripts/` | Utility scripts for devops and automation |

## Layer Loading
1. **L0** — AGENTS.md (this file): orientation & routing
2. **L1** — CONTEXT.md: workspace overview, stage index, load tables
3. **L2** — stages/{current}/CONTEXT.md: stage contract
4. **L3** — _config/*, stages/{current}/references/*: stable rules
5. **L4** — stages/{current}/output/*: working artifacts

## Stage Pipeline
| Stage | Job | Gate |
|-------|-----|------|
| 00-intake | Capture project scope, stakeholders, domain context, existing assets | Stakeholder sign-off on scope |
| 01-discovery | Explore domain, analyze competitors, identify data sources, validate assumptions | Discovery dossier approved |
| 02-architecture | Define system architecture, data models, integration points, tech decisions | Architecture Decision Records (ADRs) signed |
| 03-build | Implement features against the stage-level scope — backend, frontend, pipeline, chatbot | All acceptance criteria met in staging |
| 04-test | Run automated/manual tests, validate predictions accuracy, security audit, perf testing | Test pass ≥ 90%, no critical bugs |
| 05-deploy | Package, release, deploy to production, monitor, rollback plan | Deployment verified by smoke tests |

## Completion Protocol
When a stage finishes, update its output/ with the deliverable, then read the next stage's CONTEXT.md and proceed. If human review is needed, state what needs sign-off and wait.
