# User dashboard UI update - 2026-10-22

Implemented at `/dashboard` in `frontend/src/pages/Dashboard.jsx`, with isolated `Dashboard.css` styles. Uses the existing application navbar, protected route, authentication hooks, account endpoint, bet-history endpoint and session store.

## Delivered
- Heritage cream, charcoal and green layout with serif headings, wallet summary and account link.
- Total bets, settled win rate and open bet summary. Win rate excludes pending, cancelled and refunded bets; no settled results displays an em dash.
- Recent activity sorted newest first, with All bets/Pending/Settled filters and a link to full history. Shows five rows per filter.
- Canonical AI picks, predictions, saved picks and odds navigation.
- Session-limit progress responds to store updates and clearly describes the browser-session scope.
- Loading, empty, failed-fetch and retry states; unavailable metrics are not fabricated as zero. Numeric string balances are supported.
- Responsive desktop/tablet/mobile layout and keyboard accessible controls.

## Verification
- `npm run build`: passed (TypeScript and production Vite build).
- `eslint src/pages/Dashboard.jsx tests/dashboard.spec.js`: passed.
- `playwright test tests/dashboard.spec.js --project=chromium --project=firefox --reporter=line`: 12 passed.
- Browser coverage: 1440/900/390px layouts without horizontal overflow; sorted activity; status filters; settled-only win rate; numeric string balance; loading; empty history; failed history and successful retry. API responses in tests are explicit fixtures.
- Desktop and mobile screenshots reviewed: `frontend/test-results/dashboard-1440.png` and `dashboard-390.png` (generated ignored artifacts).
- Fallow before/after audit saved alongside this report. The repository gate remains failing: pre-existing unresolved imports and other findings; new dashboard functions also receive estimated-uncovered complexity findings. Browser coverage is not imported as measured coverage by Fallow. No new dead-code issues or duplication groups in the initial after comparison. This audit is not reported as passing.

## Scope and limits
No production deployment, backend changes, migrations or account transactions. Monetary values keep the existing USD contract. The activity summary uses the complete history returned by the existing endpoint; future API pagination would require server aggregate metrics. Browser session spending remains the existing in-memory store, not a persistent account-level responsible-play limit.
