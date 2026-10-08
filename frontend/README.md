# FootballHeritage frontend

The supplied FootballHeritage editorial template is integrated with the original
application using React 19, TypeScript 7 (strict new components), Vite 7, Tailwind CSS 4,
Lucide, BrowserRouter, React Query and the existing Zustand authentication state.

See [UI_INTEGRATION.md](UI_INTEGRATION.md) for architecture, routes/APIs, local setup,
validation commands and clearly identified backend/data gaps.

From this directory:

```powershell
npm ci
npm run dev
npm run typecheck
npm run lint
npm run build
npx playwright install chromium firefox
npm test -- --workers=1 --reporter=line
```

Set public service URLs using [.env.example](.env.example). Defaults are Rust
`http://localhost:8888/api/v1` and the statistical pipeline
`http://localhost:5555/api/v1`. Keep credentials server-side.

Authentication uses the existing backend bearer-token flow and sessionStorage.
This project does not claim encrypted browser token storage, universal CSRF tokens,
live editorial coverage, verified multi-sport AI models, or measured sub-100ms wagers.
The original account age gate, financial limits and protected/admin routes remain.
Production hosting requires a frontend SPA fallback for direct routes.

Template previews are labeled sample editorial. Scores and predictions never silently
fall back to invented data. Bookmarks and team follows are scoped to authenticated user
IDs on this device; there is no server sync endpoint yet. Existing JSX screens remain
JavaScript while the shared template shell and new pages are strict TypeScript.

Original backend capabilities were not replaced by the template starter.

The public landing is `/`; **Explore FootballHeritage** opens the general sports home
at `/app`. Account links use `/register` and `/login`. Successful authentication defaults
to `/dashboard`, or a validated internal `returnTo`/protected-route destination.
External, malformed and login/registration-loop return URLs are rejected.
See `src/landing/` for the scoped landing design and `tests/landing.spec.js` for coverage.

Supplied template directories are optional local visual references, not required
on a clean clone. Landing layout/color/contrast tests always run; extra source
cross-checks run when the supplied CSS is present. The separate template-build
comparison test explicitly skips when that local reference build is absent.
