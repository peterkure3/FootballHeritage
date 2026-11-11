# Sport match-centre implementation

## Design intent

Kind: existing sports analytics application. The user's compact schedule reference
sets the information density and date navigation; the existing FootballHeritage
design system sets the typography, colour, controls, cards and page shell.

Applied the requested Leonxlnx/taste-skill `design-taste-frontend` skill, installed
in `.agents/skills/design-taste-frontend`. Used its hierarchy, alignment, card,
interaction and browser-inspection guidance. Marketing-page recipes such as
full-screen heroes, shader effects and photographic feature sections do not fit
the explicitly requested compact, data-led schedule and bento layout.

The initial implementation introduced separate colours, rounded cards and sans
headings. The user's design-system check prompted an alignment pass:

- Existing Georgia display headings and Arial body typography.
- Existing emerald, charcoal, white, muted text and border colours.
- Shared 9px card and 5px control radii; extracted from existing styles into tokens
  without changing the previous rendered values.
- Existing shared card, button, feature-access, loading and dialog components.
- Bento gaps follow the existing intelligence grid; no new font dependency.
- Fixed a legacy summary-link selector that would otherwise override bento links.
- Shared dialogs explicitly centre with `inset: 0; margin: auto`; this fixes the
  reset overriding the browser's default dialog margins. Match dialogs have a
  readable, team-labelled score display and bounded viewport scrolling.
- The existing focus ring now uses the shared emerald token for stronger contrast.

## Functionality

All six sport schedule pages provide a seven-day date strip, previous/next week,
calendar input, team and competition filters, grouped daily rows and match dialogs.
Dates are explicitly UTC and filters persist in the URL. Final scores show away
then home, in the same order as the matchup. Missing player-high statistics are
omitted rather than invented. Small screens keep horizontal scrolling inside the
table; page navigation and filter controls remain in the viewport.

Sport home pages show a prediction spotlight, featured upcoming games and verified
results in a bento grid. Stale model snapshots do not display a current prediction
probability. Candidate forecasts retain their experimental label. General home,
saved stories and the existing AI generator's compact summary are preserved.

## Sources and access

`GET /sport-schedule/{sport}` combines retained upcoming fixtures with checksum-
verified recent finals for NBA, NCAAB, WNBA, NFL and College Football. Football
continues using its existing matches endpoint. The new Rust gateway contract is
read-only, uses the sports feature gate and is mirrored in the Python publication
manifest and prewarm list. Exact fixture identities coalesce provider duplicates;
contradictory final scores are excluded. Corrupt/missing sources produce partial
coverage notes or a 503 when neither source is usable.

Live check: NBA November 10–13 returned 24 games, including 14 verified finals.
The November 10 schedule matches the eight final-score rows in the supplied
reference. Existing source coverage limits remain; no forecasts, scores, player
statistics or team logos were fabricated.

## Verification

- Frontend lint, type checking and production build passed.
- Python schedule/gateway/final-score/intelligence regressions: 61 passed,
  8 subtests passed; two existing UTC deprecation warnings.
- Rust read-only route and sports feature-gate test passed.
- Browser checks cover all six sports, duplicate rows, URL filters, dialogs,
  source isolation/errors, stale forecasts and 320/390/768/1024/1440px layouts.
- Final new sports suite: 19 passed. Existing match-dialog and mobile-intelligence
  regressions each passed independently. The broader earlier run passed 57 tests;
  its sole browser-startup timeout passed on rerun with one worker.
- A regression checks computed typography and shared card/control token values.
- Desktop/mobile match-dialog regressions check viewport centring, score type size
  and Escape dismissal.
- Taste `shoot.mjs` captured the actual development server's home and schedule;
  screenshots are in this output directory. The live model snapshot was stale, so
  its correct unavailable state is visible; the existing scoreboard was unavailable.

## Taste checker limits

The automated Taste gate reported `GATE: FAIL 22`, with 18 warnings, on the full
existing application shell. Its report is `sport-centre-taste-check.txt`. It is not
a passing gate. Several checks require the skill's marketing-page scaffolding
(`.wrap`, one-screen hero, a separate animated moment and equal-height feature
rows), which conflicts with the requested existing application shell and bento.
Other findings concern the existing navigation/footer grid and muted text. New
heading-scale and focus issues found during the first pass were corrected. No
waivers or checker-file changes were used to hide findings. Browser interaction,
responsive layout and design-token regressions are verified independently.

Fallow retains existing repository findings. It estimates several new functions
as uncovered because it does not associate route-driven Playwright coverage with
component imports. The new component flows have explicit browser tests; this
estimated coverage result is not a claim that instrumentation coverage was measured.

No deployment, model refresh or data migration was performed.
