# Fantasy Sports navigation

- Added Fantasy Sports to the shared desktop navbar and mobile accordion, with Fantasy Premier League linking to the existing protected `/fpl-advisor` page.
- Reused the existing dropdown interaction, route-change dismissal, outside-click dismissal and Escape focus restoration. The current FPL section is highlighted.
- Updated the FPL header, responsive wrapping, selected-tab contrast and pressed-state accessibility. Existing FPL data APIs and login requirements are unchanged.

## Verification

- `npm run build`: passed, including TypeScript checks.
- Targeted ESLint: FPLAdvisor.jsx passed; MainNavbar.tsx is ignored by the existing ESLint configuration and was checked by TypeScript during the build.
- Chromium navigation suite subset: 7 passed. Covers Fantasy Sports keyboard dismissal, navigation, active state, mobile menu closure, tab selection and no overflow at 1440/900/390px; also existing mobile navigation and homepage layout checks. API data was mocked for these browser checks.
- Fallow audit artifacts: `fantasy-nav-fallow-before.json` (repository scope) and `fantasy-nav-fallow-after.json` (frontend scope). The repository audit warned about missing root node_modules; these differing scopes are not a regression comparison.
- Existing unrelated working-tree edits were preserved. No commit or deployment performed.
