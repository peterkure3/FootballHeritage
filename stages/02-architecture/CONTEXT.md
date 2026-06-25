# Stage 02: Architecture

## Inputs
| Source | What to Load |
|--------|--------------|
| `01-discovery/output/discovery-dossier.md` | Findings, recommendations, data source details |
| `_config/tech-stack.md` | Language, framework, infrastructure decisions |
| `_config/conventions.md` | Code style, git workflow, CI/CD conventions |
| `backend/Cargo.toml` | Rust dependencies and crate structure |
| `frontend/package.json` | Frontend dependencies and build tooling |
| `pipeline/requirements.txt` | Python dependencies and framework choices |
| `chatbot/package.json` | Chatbot dependencies and Genkit configuration |

## Process
1. Define system architecture — component diagram showing backend, frontend, pipeline, chatbot, and external integrations
2. Define data architecture — database schema, data flow between pipeline → backend → frontend, caching strategy
3. Choose or validate tech stack decisions — Rust/Actix for API, React/Vite for UI, Python/FastAPI for pipeline, Node.js/Genkit for chatbot
4. Design integration contracts — REST/WebSocket API specs, message queue topics, shared data formats
5. Document architecture decisions as ADRs (Architecture Decision Records)
6. Define deployment architecture — containers, orchestration, CI/CD pipeline, monitoring

## Outputs
| File | Description |
|------|-------------|
| `output/adrs/` | Architecture Decision Records — one file per key decision |
| `output/system-diagram.md` | Component diagram and data flow (text-based or Mermaid) |
| `output/data-model.md` | Core database schema, data dictionaries, entity relationships |
| `output/_blockers.md` | Architecture risks, dependency constraints, capacity concerns |

## Gate
Architecture reviewed by engineering team. All ADRs signed off. Data model validated against discovery findings before build begins.
