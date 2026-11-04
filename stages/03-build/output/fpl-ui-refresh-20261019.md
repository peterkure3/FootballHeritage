# FPL Advisor visual refresh

Updated the complete FPL page to the current Heritage design: shared page width, serif headings, white cards, muted green hero, shared buttons and footer. Added a responsive toolkit sidebar (horizontal navigation on phones), summary metrics, position-grouped formation, bench cards and native keyboard-accessible player disclosures. Preserved all five recommendation views and the existing API contracts. Missing teams and empty player lists now have explicit states; read failures offer a GET retry, while data refresh continues to use the existing POST endpoint.

## Verification

- Production build and TypeScript passed.
- Targeted ESLint passed after correcting dynamic icon usage for the existing lint configuration.
- Seven Chromium browser checks passed, using mocked API data: navigation and populated layouts at 1440/900/390px, every recommendation view, keyboard player expansion, show-more control, error retry, empty-state refresh and missing-team/list states.
- Desktop and mobile screenshots inspected; no horizontal page overflow. Screenshots are in `frontend/test-results/heritage-navigation-FPL-*/`.
- Fallow audit written to `fpl-ui-fallow-after.json`. The broader working-tree audit remains failing (3 dead-code issues and 42 complexity findings); it also flags three low-impact selector-complexity warnings in the new stylesheet. This is not a clean repository-wide audit claim.
- Existing unrelated edits preserved; no commit or deployment.
