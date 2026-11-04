# Admin workspace update — 2026-10-15

## Delivered

- Rebuilt the sidebar around operations, sportsbook odds, probabilities/EV, paper trials, platform management, and workspace tools. Existing routes, accessible collapsed links, mobile close/Escape controls, focus containment/restoration, responsive cleanup, and actual authenticated role labels.
- Updated every other admin page to match the overview. Shared layout, tables, metrics, loading/error/retry states, and timestamps replace demo panels.
- Users: authenticated backend list, server filters/pagination, confirmation before verification/status changes, failure feedback, and invalidation after successful updates. No real accounts were modified during verification.
- Events: retained create/edit forms/backend actions, added pagination and explicit errors, confirmed deletion and page-local search. Corrected datetime-local conversion so editing preserves the kickoff instant in Africa/Kampala.
- Statistics/revenue: backend current-day totals and explicit cohort/unit definitions. Removed invented trends and historic amounts. Fixed analytics column mismatch and settled net (subtract winning payouts only).
- Audit: recorded admin actions and pending fraud alerts; search over the latest 100 actions.
- Preferences: persisted assistant shortcut control and actual session details. Removed unsupported 2FA, alert and database-status claims.
- SportsGPT: existing authenticated Rust RAG endpoint, actual quick prompts, errors and idempotent retries. Floating shortcut opens this page; canned replies removed.
- Bets: simulated customer bets and settlement success messages removed. Backend admin bet routes remain disabled; the page reports this and links to platform statistics and the separate paper ledger.
- Backend user-list fixes: bound filter values, allowlisted sorting, valid limits, filtered pagination counts. Event list now parses query-string offsets/limits correctly.

## Verification

- 15 Chromium admin checks passed, including real pipeline/database-backed operations, drawer accessibility, filters, failed mutations, chat retries, and Kampala kickoff preservation. Browser user mutations/chat use explicit response fixtures.
- Three PostgreSQL admin integration checks passed using connection-local temporary tables only: quoted/injection-like searches, filtered counts/limits, net revenue, event pagination and event date/odds updates.
- 32 ordinary Rust checks passed. PostgreSQL checks were run explicitly.
- Production build/typecheck and targeted ESLint passed. Backend built/restarted locally; port 8888 health is healthy.
- Desktop/mobile previews inspected: `admin-pages-desktop.png`, `admin-sidebar-mobile.png`. Geometry assertions verify navigation stays beside content. Removed unnecessary content transitions that caused visual overlap.
- Fallow preserves existing unused script/export and clone group. New shared components introduce no dead files/exports. Existing EventFormModal/navigation complexity remains; new critical findings were split. See `admin-pages-fallow-20261015.txt`.

## Runtime scope

Local frontend: http://localhost:5173/admin/dashboard. No production deployment. Protected admin APIs require a valid signed-in administrator token. API failures never fall back to demo values. Admin bet settlement requires separate backend implementation before activation.
