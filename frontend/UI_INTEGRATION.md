# FootballHeritage template integration

## Architecture and visual reference

The provided template remains separate in `../footballheritage-ai-picks/footballheritage/`.
Its green (`#147b4c` / `#177c4c`), charcoal (`#141b17`), white, and neutral (`#f0f2ef`)
palette, Georgia headings, Arial interface text, fh wordmark, scoreboard, sports header,
210px / flexible / 294px desktop grid, editorial cards, and responsive breakpoints guide
the implementation. The template's backend is **not** used as a replacement API.

`src/App.jsx` retains BrowserRouter, React Query, protected routes and administration.
Application navigation is mounted above the application routes so hover/focus state
survives transitions. The public root, login and registration use a shared landing
account navbar instead of the sports header and scoreboard. Auth-header links retain
the existing return URL/state; validation still belongs to the auth route guard.
Login/registration share typed `landing/AuthForms.tsx` controls and scoped `auth.css`
for landing-matched cream/green surfaces, serif headings and responsive form cards.
Existing auth hooks, schemas, field names/payloads and the 21+ modal are retained;
inline errors are linked to inputs and password visibility controls support keyboards.
The old placeholder legal-document links were not working routes; consent wording
remains, but actual Terms/Privacy pages are still a content/backend gap.
The old `components/Navbar.jsx` import is a no-op compatibility shim for legacy pages.
`src/heritage/` contains MainNavbar/ScoreboardStrip, AppShell/sidebars/footer, StoryCard,
HomePage/StoryPage, SportPage/MatchCard/TeamsPage, BestPicksPage/AiChatPage, data states,
native dialogs, account-scoped preferences, and runtime-checked API response adapters.
`heritage.css` owns shared tokens and template layout. Legacy pages/components use the
same surface, border, ink and muted Tailwind tokens at their source, rather than global
overrides of white button text. Photos copied from the template's Unsplash URLs are local
in `public/images/`; the source URLs are retained in `tests/template-reference.spec.js`.

React 19, TypeScript 7, Vite 7, Tailwind 4 and Lucide are used. New TS/TSX components have
strict/no-unused checking. Existing JSX remains JavaScript (`allowJs`, `checkJs: false`)
for incremental integration; this is not a claim that every legacy screen was converted
to TypeScript. The current typescript-eslint release rejects TypeScript 7 in its peer
range; it was not forced into the dependency tree. ESLint covers existing JS/JSX and
TypeScript compilation checks the new code. The npm lockfile includes compatible security
updates; no deployment or git commit is performed by this integration.

## Routes and data

| View | Frontend route | Data / behavior |
| --- | --- | --- |
| Landing | `/` | Landing template, separate Register/Login navbar; no sports header |
| General sports home | `/app` | Template editorial previews, explicitly labeled sample content; no sport subnav |
| Sport home | `/sport/{slug}` | Football, NBA, NFL, WNBA, NCAAB, college-football; selected sport subnav |
| Scores / schedule | `/sport/{slug}/scores`, `/schedule` | Football uses existing pipeline `GET /api/v1/matches`; other sports use authenticated Rust `GET /api/v1/betting/events` |
| Match details | `/sport/{slug}/scores?match={id}` | Returned fixture fields in a focus-managed dialog; IDs are not invented |
| Standings | `/sport/{slug}/standings` | Explicitly unavailable; there is no standings endpoint in this repository |
| Teams / insights | `/sport/{slug}/teams`, `/insights` | Labeled static directory; existing prediction/intelligence/college/player-prop routes linked |
| Editorial preview | `/stories/{id}` | Sample title/description only, not a fabricated full article |
| Saved / followed | `/saved`, `/followed-teams` | Authenticated user-ID-scoped device storage; no server synchronization claim |
| Best picks | `/ai-picks` | Existing Rust `GET /api/v1/ai-picks`, `POST /api/v1/ai-picks/generate` |
| Chat | `/ai-picks/chat?conversation={id}` | Existing Rust chat/list/history endpoints; text safely rendered, bounded context, cancellation and explicit retry |
| Accounts / betting / wallet / administration | Existing routes retained | Existing Zustand auth store, bearer-token API client and handlers preserved |

The scoreboard shows latest available records, **not** a claimed real-time feed. There
are loading, empty, error, retry, and unavailable states, without sample score/prediction
fallbacks. Sports navigation is a directory, not a model capability declaration.
AI result ordering is preserved from the API. Model and odds-implied probabilities are
fractions displayed as percentages; `edge_pct` is percentage points. `expected_value` in
the current pipeline is expected profit **at `recommended_stake`**, in stake units, not
per-unit EV or profit per 100 units. Missing model/evidence/timestamp fields are labeled.

## Local setup

Use Node compatible with Vite 7 (Node 20.19+ or 22.12+). From `frontend/`:

```powershell
npm ci
Copy-Item .env.example .env.local  # Only if no local environment file already exists
npm run dev
```

Configure public service URLs in `.env.local`:

```dotenv
VITE_API_URL=http://localhost:8888/api/v1
VITE_PIPELINE_API_URL=http://localhost:5555/api/v1
VITE_SESSION_TIMEOUT=15
```

Credentials and provider keys belong in backend/chatbot/pipeline environments, never
`VITE_*` variables. Existing login/registration endpoints are used; no demo identity or
session flag is imported. Bearer tokens and user state use the existing sessionStorage
flow, not encrypted storage or cookie-based CSRF claims. The existing account age gate
is retained. Native wallet and bet dialogs trap focus, support Escape and restore focus;
money-moving requests are not automatically replayed by React Query.

The separate landing design is scoped under `.fh-landing` in `src/landing/`; its
reference is `../footballheritage-landing-template/footballheritage/src/Landing.tsx`
and `landing.css`. The shared `heritage/Brand.tsx` is reused by both navbars. The local
stadium asset has an accessible unavailable fallback. Template claims about league
tables, news, AI evidence and multi-sport generation are replaced with current coverage
disclosures; no template demo authentication is used.

The account route guard owns both registration and login redirects. The existing
`/dashboard` default is retained; protected-route state or `?returnTo=...` may specify
a validated internal destination. External URLs, encoded protocol-relative paths,
backslashes, controls and authentication loops are rejected. Account cross-links
preserve the destination. Authentication endpoint 401s stay on the form to show an error;
protected-request 401s still clear the token and navigate to login.

API credentials and SQLx/database/service setup remain governed by the existing backend
and pipeline instructions. The AI Rust handlers currently require their existing server
configuration; frontend availability states do not manufacture a replacement provider.
Production hosting must serve `index.html` for non-asset frontend routes (SPA fallback)
while keeping `/api` requests routed to the backend. Vite supports direct routes locally.

## Verification

```powershell
npm run typecheck
npm run lint
npm run build
npx playwright install chromium firefox
npm test -- --workers=1 --reporter=line
npm audit
```

For an unmocked, read-only check with the Rust and pipeline services already running:

```powershell
npm run preview -- --host localhost --port 3000 --strictPort
# In another terminal:
node scripts/smoke-live-ui.mjs
```

The pipeline's default CORS policy permits `http://localhost:5173` and
`http://localhost:3000`, not arbitrary loopback hostnames or ports. If using a different
origin, configure the existing server-side `API_ALLOWED_ORIGINS` explicitly and restart
the pipeline yourself. `LIVE_UI_ORIGIN` and `LIVE_RUST_API` can override the smoke-check
URLs. This check requires available football fixtures; it does not create accounts,
generate predictions, contact a provider, or move money.

Opt-in real registration/login verification is separate from mocks:

```powershell
$env:LIVE_AUTH_WRITE='1'
node scripts/smoke-live-auth.mjs
```

This is restricted to local hosts and creates **one** isolated development account
through the actual forms, including the existing 21+ age gate. A random password exists
only in memory. The script checks the default dashboard redirect, validated profile
return and authenticated refresh; no bets, deposits or model requests are submitted.
The isolated account is retained and its ID/email are reported for manual removal by
approved administration. Do not run this write-enabled check against production.

Browser tests use a fresh server on `127.0.0.1:5187` to avoid colliding with a user's
development server. API mocks are explicitly test-only. The supplied template comparison
serves its existing `dist/` locally on an ephemeral loopback port, captures both layouts,
and cross-checks navbar/surface colors, serif headings, heading size and grid spacing.
That comparison is skipped with a reason if the supplied reference build is absent.
Screenshots for desktop (1440px), tablet (900px), and mobile (390px) are in test-results.
The in-app browser connection could not start in this environment; repository Playwright
tests are the fallback. Authenticated upstream/provider behavior is not proven by mocks.

## Remaining backend/data gaps and unrelated defects

- No newsroom, live team-profile, standings, bookmark or followed-team APIs are present.
  Editorial/directory previews and device-only preferences are visibly labeled.
- AI generation currently accepts only Football. The handler ignores competition/date
  filters before upstream ranking; this UI filters the returned set and discloses that
  it cannot obtain a complete filtered ranking. The upstream can substitute missing odds.
  Bookmaker provenance, odds freshness, evidence/calibration and feature versions are
  incomplete. These are not verified betting recommendations.
- Chat depends on provider configuration and a compatible service response. Existing
  conversation persistence resubmits context, can duplicate history, and its ownership
  upsert requires backend review. Numerical grounding is not guaranteed by this frontend.
- The original parlay sidebar posts to `/parlay/place`, which is not registered in the
  current Rust routes. Calculation/save/history remain available. Its mixed American/
  decimal odds and synthesized fixture-ID behavior need a separate financial review.
  No new financial routes or automatic bets were enabled. Existing settlement/void routes
  remain untouched. Configurable API URLs replace the legacy hardcoded port 8080 URLs.
- Legacy admin screens retain their behavior and share the visual tokens; not every admin
  mutation/modal has been manually verified. The existing AdminEvents effect-dependency
  lint warning remains separate from this UI integration.

Final check outcomes are recorded in `../stages/03-build/output/frontend-template-integration.md`.
