# Architecture deliverable — publication refactor

Primary deliverable: [architecture-audit.md](../../../docs/architecture-audit.md).
Exact affected files, sequence and risks: [migration-plan.md](../../../docs/migration-plan.md).
Supporting contracts: [target architecture](../../../docs/target-architecture.md),
[ownership](../../../docs/database-ownership.md),
[sync design](../../../docs/neon-sync-design.md).

Preserve Actix/SQLx, Python ML, React 19/TypeScript 7, existing auth/financial
behavior and user work. Approved publication aggregates supplement normalized
application tables; the pipeline never overwrites Neon-owned user/financial data.
No completed production architecture or full endpoint migration is claimed.

User decision: existing Neon project stays staging; production project later.
Additive destination DDL was validated on an isolated child; parent staging
remains unchanged. Production release, credential changes and destructive
operations still require explicit approval. Build evidence and remaining work:
`stages/03-build/output/publication-foundation-20261026.md`.
