# Stage 03: Build

## Inputs
| Source | What to Load |
|--------|--------------|
| `02-architecture/output/adrs/` | Architecture decisions to implement |
| `02-architecture/output/data-model.md` | Schema and data contracts |
| `02-architecture/output/system-diagram.md` | Component boundaries and integration points |
| `_config/conventions.md` | Code style, git workflow, PR process |
| `_config/tech-stack.md` | Framework-specific guidance |

## Process
1. Implement backend features in `backend/` — API endpoints, business logic, database operations, auth
2. Implement frontend features in `frontend/` — pages, components, state management, API integration
3. Implement pipeline features in `pipeline/` — ETL jobs, scraper improvements, prediction model updates
4. Implement chatbot features in `chatbot/` — Genkit flows, prompt engineering, tool integrations
5. Write or update tests alongside code (unit, integration, end-to-end)
6. Document any changes to API contracts, configuration, or deployment requirements
7. Run local build and verify everything compiles and passes basic smoke tests

## Outputs
| File | Description |
|------|-------------|
| `output/changelog.md` | Feature list, changes made, migration notes |
| `output/build-artifacts.md` | Build outputs, configuration changes, env var updates |
| `output/_blockers.md` | Build issues, unimplemented features, tech debt |

## Gate
All acceptance criteria met in a staging environment. Feature-complete review with product owner. No critical or high-severity bugs.
