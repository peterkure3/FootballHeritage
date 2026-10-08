# Landing template integration — 2026-10-08

## Scope and architecture

The already-extracted reference is
`footballheritage-landing-template/footballheritage/src/{Landing.tsx,landing.css}`.
The original Rust backend and unrelated dirty-worktree changes were preserved. The
template's hash router, demo sessions, identity and small backend were not imported.

- `frontend/src/landing/Landing.tsx`: landing navbar, stadium hero, sports strip,
  platform features, AI introduction, registration CTA and footer. Reuses the existing
  local stadium photo, typed sports directory and Lucide icons; includes an accessible
  image-unavailable fallback and skip link. Bottom-page CTAs reset scroll to reveal the
  destination form. Modified/middle clicks keep normal browser behavior.
- `frontend/src/landing/landing.css`: scoped `.fh-landing` styles; original cream,
  dark-green and charcoal surfaces, serif headings, geometry and responsive breakpoints.
  Secondary text is darkened for contrast; application styles are not overwritten.
- `frontend/src/heritage/Brand.tsx`: shared existing fh wordmark for both separate navbars.
- `frontend/src/App.jsx`: public `/` landing, `/app` general sports homepage; application
  header omitted only on the landing. Existing sports, AI, protected and admin URLs stay.
- `frontend/src/utils/authRedirect.ts`: internal-only return-destination validation;
  default `/dashboard`, with protected-route state or `returnTo` preserved across account
  links. Rejects external, malformed, backslash, control and authentication-loop URLs.
- Existing Login/Register forms, Zod validation, 21+ gate, Zustand session handling,
  API client and Rust endpoints are reused. The route guard owns redirects. Auth-endpoint
  401 errors stay visible on the form; protected-request 401s still clear the token and
  return to login. No automatic financial replay or new financial routes.

## Routes

| Landing action | Destination |
| --- | --- |
| Header/footer logo | `/` |
| Register, Create your account, Join FootballHeritage | `/register` |
| Login | `/login` |
| Explore FootballHeritage / Explore the platform | `/app` |
| Successful authentication | `/dashboard` or validated internal return destination |

`POST /api/v1/auth/register`, `POST /api/v1/auth/login` and the existing profile/session
APIs remain the actual authentication contracts. No dependency additions were needed;
React 19, strict TypeScript 7 for new components, Vite and Tailwind compatibility remains.
Production hosting still needs an SPA fallback; no external deployment was performed.

## Verified live authentication

`frontend/scripts/smoke-live-auth.mjs` is opt-in (`LIVE_AUTH_WRITE=1`), local-host-only,
and uses the actual forms without mocks. Passwords are random and only held in memory.
Real local registration returned **201** and opened `/dashboard`. Logout and real login
returned **200**; validated `/profile` return and authenticated refresh succeeded.
No wagers, deposits, provider calls or model runs were submitted.

One isolated development account is retained for manual removal via approved
administration (do not delete any other users or reset a database):

- ID: `507a5b02-23da-467a-8e98-589a6fb46eac`
- Email: `landing-qa-1791421102869-c556e4a7@example.test`

## Validation

- Final complete Playwright run: **76 passed**, Chromium and Firefox, one worker, no
  retries or skipped cases. Includes all ten landing links, navbar isolation, keyboard
  focus, image fallback, contrast, 1440/900/390px layouts and overflow, direct routes,
  history/refresh, registration validation/loading/error/retry, login 401/retry, internal
  destinations and unsafe URL rejection. Existing sports/profile/AI menus, saved items,
  fixture adapters, dialogs and mocked betting/wallet handlers also passed.
- Earlier runs exposed cross-form readiness assertions and a combined ten-navigation
  Firefox time limit. Tests now wait for each rendered form and verify a login request;
  every CTA is independently exercised. Refresh/back/forward assertions remain. Bottom
  registration CTAs additionally assert that the first form field is in the viewport.
- Final strict TypeScript and production build: passed. ESLint: zero errors, one existing
  `AdminEvents.jsx` effect-dependency warning. `npm audit`: zero vulnerabilities.
  Dependency compatibility confirmed: React 19.2, TypeScript 7.0.2, Vite 7.3.7,
  Tailwind 4.1.14. `git diff --check`: passed.
- Desktop, tablet and mobile screenshots reviewed against the supplied source design;
  cream/green colors, serif headings and hero heights cross-checked with reference CSS.
  Secondary text is deliberately darkened for contrast. Not a pixel-identical-content
  claim: unsupported template promises were replaced with actual capability disclosures.
- API mocks are explicitly test-only and do not replace the live-auth check above.

The in-app browser runtime could not start because of Windows sandbox initialization;
repository Playwright is the fallback. Fallow analysis was run before/after integration
and continues to report repository-wide dead code/complexity/duplication findings in the
existing dirty tree; it is not represented as a clean architectural gate. Its reuse-first
guidance led to shared branding/router/auth instead of another session or client stack.

## Remaining limitations

No landing implementation blocker is currently identified. AI still requires connected
statistical/model and chat services; generation currently enables Football only. Missing
standings/newsroom feeds, device-only followed teams/bookmarks and incomplete AI evidence
are disclosed rather than promised as live features. No performance figures, testimonials,
fake statistics or guaranteed outcomes were added. Live provider/model inference, backend
tests and migrations were not exercised for this frontend-only task.

See `frontend/UI_INTEGRATION.md` and `frontend/README.md` for setup and wider API/data gaps.
This deliverable does not close the entire build stage or authorize external deployment.

## Auth-header follow-up

The user reported sports navigation and the scoreboard on login/registration.
Extracted `src/landing/LandingNavbar.tsx` for reuse on the landing and both auth
routes. `App.jsx` now selects this simple logo/Register/Login header for auth
pages, while preserving the application's sports header elsewhere. Header-only
scoping resets landing min-height and protects links from decorative overlays
without applying landing typography to the existing forms. Account links retain
the existing return URL/state; authentication, API clients and Rust are unchanged.

Added desktop/mobile browser regression cases for both forms: no scoreboard or
sports/subnav, visible form, compact header, no horizontal overflow, switching
forms with return URL, refresh, logo home and restoring sports navigation on `/app`.
Strict TypeScript and production build passed; lint has zero errors and the
existing `AdminEvents.jsx` hook warning. Fallow before/after summaries remain
unchanged (25 dead-code issues, 162 complexity findings, 54 clone groups); its
repository-wide gate still fails and is not claimed clean. Reuse-first guidance
informed the shared component instead of duplicated header/auth logic.
No new live accounts, financial mutations or external deployment were performed.

Follow-up verification: `npx playwright test tests/landing.spec.js
tests/heritage-navigation.spec.js tests/betting-flow.spec.js --workers=1
--reporter=line` passed **82 tests** across Chromium and Firefox (4.8 minutes).
This includes eight new auth-header cases and existing landing, authentication,
sports/AI navigation, betting and wallet regression checks. APIs in these browser
tests are explicitly mocked; real auth was not rerun for this header-only change.
CRLF-aware whitespace check passed on the modified tracked source/documentation.

## Login and registration form redesign

Replaced the old gradient/glow/emoji form presentation with landing-matched cream,
charcoal and deep-green styling, Georgia headings, restrained white cards, 16px
input text and responsive name fields. Typed `landing/AuthForms.tsx` centralizes
layout, labelled inputs, accessible password visibility buttons and loading submit
controls; `landing/auth.css` is scoped and leaves application pages untouched.
Legacy JSX auth pages retain their original validation/sanitization handlers, API
hooks, field names, age-confirmation modal and return URL/state. Forms use the
existing schema for inline validation, with error/hint IDs linked to each field.
Removed unsupported encryption assertions and nonfunctional `href="#"` legal
links; consent wording remains. Published Terms/Privacy documents remain a gap.
No backend contract, credentials, wallet logic or dependencies changed.

Screenshots at 1440px desktop and 390px mobile were visually inspected; automated
layout checks also cover 900px tablet. The in-app browser connection failed at
Windows sandbox initialization, so repository Playwright supplied screenshots
and behavioral checks. An initial test incorrectly expected keyboard focus styling
after mouse/programmatic focus; corrected it to use real Tab navigation.
TypeScript/production build passed. Lint has zero errors and one existing admin
hook warning. Fallow's repository-wide gate still fails on existing findings;
dead-code/complexity counts remain 25/162 and clone groups reduced from 53 to 46.
Its reuse-first guidance informed the shared field/layout controls. Live signup
was not repeated and no new real account or financial transaction was created.

Browser verification: the combined auth-form/landing/betting run completed with
64 passes and four focus-test failures. After correcting the test's keyboard
interaction (no application changes), reran all four failures in Chromium and
Firefox: **4 passed**. Thus all 68 distinct checks have passed across these runs;
this is not a claim that the initial combined run was green. Coverage includes
desktop/tablet/mobile layouts, password reveal/conceal, focus outlines, associated
inline errors, age confirmation, pending states, upstream failures, auth redirects,
landing CTAs and existing betting/wallet paths. API fixtures are test-only mocks.
