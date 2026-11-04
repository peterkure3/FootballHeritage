# AbaBet restored — 2026-10-14

The user explicitly requested restoring AbaBet with verified live prices after
its earlier removal. It is back in the canonical inventory and regional refresh
targets as `ababet:UG`; catalog count is now 46. The other nine removed sources
remain excluded.

The live anonymous page at `https://ababet.ug/` selected 2026-10-14 and displayed
nine UEFA Champions League Match Result markets. LASK–Liverpool is 19:45
Africa/Kampala (16:45 UTC), rather than the pasted 9:45. Its verified decimal
prices are 9.5 / 5.5 / 1.3. Como Calcio is explicitly mapped to Como 1907 within
Champions League matching. The adapter now accepts exact EPL and UEFA Champions
League labels and continues rejecting other competitions, live prices and
nonstandard periods.

Capture `pipeline/data/raw/sportsbooks/20261014T050448040369Z`: nine validated
snapshots, nine exact fixture matches, nine inserted and zero on repeat. The
live API verifies all nine AbaBet quotes and correct LASK kickoff and prices.
Ten sources now supply nine fresh quotes each across the nine fixtures.

Verification: 17 regional checks including PostgreSQL timezone regression and
Champions League parser coverage, two catalog/matching checks, two Chromium
catalog/live-pipeline checks, targeted ESLint and Python compilation passed.
API and import evidence is in `ababet-restored-20261014.json`.

User preference for future website navigation and network discovery: Browserbase.
No Browserbase tools are exposed in this session. The preference is recorded in
`shared/WORKFLOW.md`; existing verified public-feed collectors remain direct reads.
