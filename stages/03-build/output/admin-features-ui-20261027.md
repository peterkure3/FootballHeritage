# Admin Features UI update — 2026-10-27

Enhanced `/admin/features` with the existing green/ivory admin visual language:

- Responsive overview metrics for product features, global availability, emergency restrictions, and maintenance.
- Search/category toolbar with reset and empty results, plus a separate user-access panel.
- Feature cards with category labels, status badges, native checkbox switches, grouped role rules, and highlighted emergency restrictions.
- Audit panel with keyboard-scrollable records, empty state, and pagination; clearer confirmation dialog and feedback messages.
- Maintenance status follows the backend rule: enabled OR emergency_disabled means maintenance is active.

Validation: existing feature-management browser suite 4/4 passed (Chromium); new interaction/visual test 1/1 passed covering search, category filtering, cancel-without-write, emergency maintenance status and 390px overflow. Targeted ESLint and production build/typecheck passed. Desktop (1440px) and mobile (390px) screenshots were visually reviewed. Tests use intercepted API fixtures; live feature settings were not changed.

Artifacts: `admin-features-desktop-20261027.png`, `admin-features-mobile-20261027.png` in this directory. Fallow was unavailable in this session; used source/dependency searches and the existing test suite. No deployment or commit performed.

Follow-up: global and emergency switches now use fully rounded 36×20px tracks with 16px circular thumbs, a visible keyboard focus ring, and hidden native inputs covering the full control. Existing green/neutral/amber colours and confirmation behavior are preserved. Two targeted Chromium interaction/responsive tests and component ESLint passed.
