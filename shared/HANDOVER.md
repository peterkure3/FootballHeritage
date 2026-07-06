# Handover — What I'd Leave Behind

Written 2026-07-06, at the end of the deep-cleanup engagement. `shared/WORKFLOW.md`
covers the *process*; this file is the judgment layer — the things that made the
process find what it found, plus the institutional knowledge that isn't written in
any code comment and will otherwise walk out the door.

Load via the `/handover` skill, or read alongside WORKFLOW.md when onboarding.

---

## Part 1 — Three stories, because stories teach judgment better than rules

### The model that wore a costume
Production served a model stamped "v2.0.0" at 39% accuracy while docs claimed 72%.
Every label said v2. The *pickle* said `XGBClassifier`, 12 features — the v1
architecture. Chain of causes: v2 training had silently bit-rotted under pandas and
scikit-learn upgrades → the retrain bat quietly still called v1 → v1 read
`MODEL_VERSION="2.0.0"` from shared config and saved its output under v2's filename,
overwriting the real ensemble. Four separate small carelessnesses, each harmless
alone, combined into a production model swap that no single log line recorded.

**Lessons:** a version in a filename is a claim, not a fact — open the artifact.
Code that isn't exercised by CI is broken until proven otherwise; it rots at the
speed of your dependency upgrades. And version constants shared between old and new
code are a loaded gun.

### The column that wasn't there
`wallet.rs` inserted and selected `transactions.status`. The column did not exist in
the database. The fix (`add_transaction_status.sql`) sat at the repo root, written
but never applied, for months — because migrations were disabled "since they were
already applied." Deposits and withdrawals were broken the whole time and nobody
noticed, because nothing exercised them end-to-end.

**Lessons:** a fix that isn't in the migration chain doesn't exist. "Temporarily
disabled" infrastructure becomes permanent the moment it stops hurting. The absence
of user complaints is not evidence of working software — it can be evidence nobody
is using the feature.

### The seven invisible endpoints
Seven `/predictions/*` routes returned 422 for every request since the day they were
written, because they were registered after `/predictions/{match_id}` and the router
matched in order. The code was correct; the *ordering* was the bug. Nobody noticed
because the endpoints were new and nothing depended on them yet.

**Lessons:** integration behavior (route tables, middleware order, migration order)
is invisible in code review — you must observe the running system. A baseline dump
of "what routes exist and answer" would have caught this on day one.

## Part 2 — Judgment heuristics (the actual skill)

1. **Pull the thread.** The engagement's biggest finds all started as small
   anomalies someone could have shrugged off: a weird accuracy number, a lint error,
   a `+` on line 192. When a number surprises you, decompose it (denominators,
   distributions, confusion matrices) before explaining it away. The anomaly is
   never the bug — it's the *door* to the bug.

2. **Distrust every label; verify the referent.** "v2" files, "applied" migrations,
   "disabled" configs, docs saying port 8080 — in this repo, roughly half the labels
   checked were false. The cheapest senior-engineer move that exists: `head` the
   file, query the table, unpickle the artifact, curl the endpoint.

3. **Find what actually runs.** Not what could run. Log mtimes, scheduler
   registries, missing log files. This repo had four scheduling systems on paper and
   zero in reality. Deleting code is only scary when you don't know what runs.

4. **Fix the measurement before judging the system.** The accuracy metric counted
   unsettled matches as wrong. Until the denominator was fixed, every conversation
   about "the model is bad" was about a number that meant nothing. Metric first,
   verdict second.

5. **When you find one bug, hunt its class.** One `ORDER BY`+aggregate SQL error →
   grep for the pattern everywhere. One hardcoded `python` → check all three bats.
   Bugs come in litters.

6. **Make refactors provable, not plausible.** Baseline → transform by script →
   diff → live smoke. "31 routes before, 31 identical routes after" ends the
   conversation. This converts the riskiest work (big moves) into the safest.

7. **Correct your own record out loud.** I was wrong about the port, the "stray"
   package.json, and the Playwright config — and said so each time and fixed the
   index. A map that silently keeps known errors trains everyone to ignore the map.

8. **Treat every file as public before committing.** The two most dangerous files
   this month were named like housekeeping (`reset_admin_password.sql`) and
   contained a plaintext credential. Grep for password/hash/token/key on everything
   new, every time. Thirty seconds; prevents the worst class of incident.

9. **Small commits with evidence in the message.** Future readers (including future
   AI sessions) reconstruct intent from `git log`. "verified live: 422 → 200" in a
   commit message is institutional memory that survives every context loss.

10. **Ship the boring guardrails first.** CI + lockfiles + .gitignore found real
    bugs within *minutes* of existing (syntax error, lockfile drift, missing
    Cargo.lock). Guardrails have the best ROI-per-line of anything you can write.

## Part 3 — What I know about THIS project that no file says

- **The betting edge is the intelligence layer, not the classifier.** 3-class
  football prediction plateaus near the odds-implied ~55-58%; the retrained ensemble
  (56.8% val) is already close to that ceiling. Devig/EV/arbitrage — extracting
  value from bookmaker disagreement — is where the product actually wins.
  Prioritize accordingly: the odds-math triplication (pipeline `odds_math.py`,
  backend `intelligence.rs`, frontend `useParlayCalculator.js`) is the most
  dangerous unfinished business, because a silent divergence there loses real money.
- **Nothing is scheduled right now.** The bats are fixed and interpreter-safe, but
  no Task Scheduler entries exist. Until someone registers them, data and
  predictions go stale (last real run: June 9).
- **Admin bet settlement routes are commented out in `main.rs`** ("temporarily
  disabled"). That means bets can be placed but not settled through the admin API.
  Either finish and re-enable, or the betting loop is open-ended.
- **`RoleSwitcher.jsx` is cosmetic** — it switches routes, not privileges. Real
  role comes from the backend (`is_admin`/`is_super_admin`); don't let UI role
  state drift into being trusted anywhere.
- **The chatbot's RAG tables exist nowhere.** The SQL is preserved in
  `chatbot/sql/`, but no database has the tables; the chatbot presumably runs in
  degraded/non-RAG mode. Decide whether RAG is a real feature or delete the path.
- **Rotate `Admin123!` and purge hash-bearing SQL from git history** before this
  repo gets any more public than it is. Highest-severity open item.
- **sqlx 0.7.4 emits future-incompatibility warnings** — plan the 0.8 upgrade
  before a Rust toolchain update forces it mid-crisis.

## Part 4 — Working with AI agents on this repo

- Start every session by letting the agent load `/workflow` (or point it to
  AGENTS.md — the ICM layer routes it there). The method is the moat, not the model.
- Demand evidence in the transcript: "verified" must be accompanied by the command
  and its output. An agent that can't show the curl didn't run the curl.
- Money paths (wallet, betting, settlement) get a second look every time — run
  `/code-review` on those diffs regardless of which model produced them.
- Give agents anomalies, not just tasks. "Accuracy looks weird, investigate" beat
  "split routes.py" in value by an order of magnitude this engagement.
- Knowledge system map: `AGENTS.md` (entry) → `CONTEXT.md` (workspace) →
  `shared/WORKFLOW.md` (method) → `shared/CODEBASE_INDEX.md` (facts) →
  `shared/HANDOVER.md` (judgment, this file) → agent memory (session continuity).
  Keep them true: update the index when reality changes, and mark done items with
  dates so staleness is visible.

## Part 5 — The one-sentence versions

- Open the artifact.
- Pull the thread.
- Find what actually runs.
- Fix the denominator first.
- Bugs come in litters.
- Baseline, then refactor.
- Say when you were wrong.
- Everything is public once committed.
- Evidence in the commit message.
- Guardrails before features.
