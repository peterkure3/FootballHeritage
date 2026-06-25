# Conventions — FootballHeritage

## Code Style
- **Rust:** Follow rustfmt defaults and clippy lints. Use `Result<T, E>` over panics.
- **TypeScript/React:** Prefer functional components with hooks. Use strict TypeScript.
- **Python:** Follow PEP 8. Type hints required for all function signatures.
- **Node.js:** Use ES modules. Prefer async/await over callbacks.

## Git Workflow
- **Branching:** `main` (production) → `staging` (pre-prod) → `feature/<name>` (development)
- **Commits:** Conventional commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`)
- **PRs:** At least one reviewer. All CI checks must pass before merge.
- **No direct pushes to main or staging.**

## Documentation
- All API endpoints documented via OpenAPI/Swagger
- Architecture decisions recorded as ADRs in stages/02-architecture/output/adrs/
- README updated with any setup, config, or deployment changes

## Review Gates
- **Stage boundaries:** Human sign-off required before moving to next stage
- **PR review:** Every PR needs approval from at least one teammate
- **Security scan:** Run on every PR and before production deploy
- **Test gate:** CI must pass full test suite before merge to main
