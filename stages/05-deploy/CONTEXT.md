# Stage 05: Deploy

## Inputs
| Source | What to Load |
|--------|--------------|
| `04-test/output/test-report.md` | Test sign-off and known issues |
| `04-test/output/security-audit.md` | Security findings and any waivers |
| `04-test/output/perf-report.md` | Performance baselines and capacity estimates |
| `_config/brand.md` | Production messaging, domain, TLS certs |
| `_config/tech-stack.md` | Infrastructure details, hosting, monitoring |

## Process
1. Create release artifacts — build binaries, Docker images, migration scripts
2. Update configuration for production environment — secrets, env vars, feature flags
3. Run database migrations (with rollback script)
4. Deploy in order: pipeline data layer → backend API → frontend → chatbot
5. Run smoke tests against production endpoints
6. Configure monitoring dashboards, alerts, and logging
7. Document runbook for common operational procedures
8. Execute rollback test to verify recovery path

## Outputs
| File | Description |
|------|-------------|
| `output/release-notes.md` | Version, features, migration steps, known issues |
| `output/runbook.md` | Operational procedures, monitoring, incident response |
| `output/deployment-checklist.md` | Verified deployment steps with sign-offs |
| `output/_blockers.md` | Deployment issues, environment differences, rollback triggers |

## Gate
Smoke tests pass in production. Monitoring dashboards show healthy metrics. Rollback plan verified. Product owner signs off on release.
