# ADR-005: Deployment Architecture

## Status
Accepted

## Context
The platform has 3 services (backend, frontend, pipeline) + 2 databases (PostgreSQL + Redis). The chatbot was moved into the frontend as an integrated feature, removing the separate Node.js/Express service.

## Decision
**Containerized deployment via docker-compose** (already scaffolded). All 3 services + 2 databases defined in a single `docker-compose.yml`.

### Service Configuration
| Service | Base Image | Port |
|---------|-----------|------|
| Backend | `rust:latest` (multi-stage build) | 8080 |
| Frontend | `node:18-alpine` (nginx for static serve) | 80 |
| Pipeline | `python:3.11-slim` | 5555 |
| PostgreSQL | `postgis/postgres:14` | 5432 |
| Redis | `redis:7-alpine` | 6379 |

### CI/CD
Use **GitHub Actions** for:
- Lint + test on every PR
- Docker image build + push on merge to `main`
- Optional: deploy via SSH to a VPS using a deploy script

### Monitoring
- Backend exposes `/metrics` endpoint (Prometheus format)
- Pipeline exposes `/api/v1/health`
- Chatbot exposes `/health`
- **Recommended:** Prometheus + Grafana stack (separate compose file)

### Production Considerations
- Reverse proxy (nginx/caddy) in front of all services
- HTTPS via Let's Encrypt
- Database backups daily (scripts already exist in `scripts/backup_databases.py`)
- Environment-specific `.env` files per deployment target

## Consequences
- (+) Single-command deployment via `docker-compose up`
- (+) Solo-developer friendly
- (+) All existing code is already Docker-ready
- (-) Not Kubernetes-native — scaling requires manual replica management
- (-) docker-compose is single-host — no high availability without additional tooling
