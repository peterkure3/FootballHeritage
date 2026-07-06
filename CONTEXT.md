# CONTEXT.md — Layer 1: Workspace Overview

## Project
FootballHeritage — A comprehensive AI-powered sports betting platform with real-time odds, prediction analytics, responsible gambling features, and an end-to-end data pipeline for sports data ingestion, modeling, and API serving.

## Stage Index
| # | Stage | Input From | Output To |
|---|-------|------------|-----------|
| 00 | intake | — | scope document, stakeholder map |
| 01 | discovery | intake/output | discovery dossier, data source catalog |
| 02 | architecture | discovery/output | ADRs, system diagrams, data models |
| 03 | build | architecture/output | working code, deployment artifacts |
| 04 | test | build/output | test report, security audit, perf results |
| 05 | deploy | test/output | release notes, runbook, monitoring dashboards |

## Load Tables
| File | Stages | Why |
|------|--------|-----|
| `_config/tech-stack.md` | 02-architecture, 03-build, 04-test | Language, framework, infra decisions |
| `_config/conventions.md` | 03-build | Code style, git workflow, CI/CD |
| `_config/glossary.md` | 00-intake, 01-discovery, 02-architecture | Shared domain vocabulary |
| `_config/brand.md` | 03-build (frontend), 05-deploy | Visual identity, tone, messaging |
| `shared/domain-notes.md` | 01-discovery, 03-build | Domain knowledge, data source context |
| `backend/` (src, Cargo.toml) | 02-architecture, 03-build | API contracts, DB schema |
| `frontend/` (src, package.json) | 02-architecture, 03-build | UI component tree, routing |
| `pipeline/` (api/, etl/, models/) | 01-discovery, 02-architecture, 03-build | ETL logic, ML models, scraper config |
| `chatbot/` (src, package.json) | 02-architecture, 03-build | Genkit flows, prompt templates |

## Global Rules
- Every stage writes one primary deliverable to its output/ folder
- Do not modify files outside the current stage
- Document blockers in output/_blockers.md
- Respect existing code directories — ICM layers on top, does not restructure
