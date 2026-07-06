---
name: workflow
description: Load the FootballHeritage engineering operating manual — the investigate-verify-record loop, project commands, and known failure patterns. Use at the start of any nontrivial task in this repo (bug fix, refactor, cleanup, feature), or whenever unsure how to proceed, verify, or hand off.
---

# FootballHeritage Engineering Workflow

Read `shared/WORKFLOW.md` in full now — it is the authoritative playbook. The rules
below are the condensed contract you must follow while working.

## The loop

ORIENT → INVESTIGATE → PLAN → EXECUTE (small verified steps) → VERIFY END-TO-END → RECORD

## Non-negotiable rules

1. **Orient first.** Read AGENTS.md → CONTEXT.md → shared/CODEBASE_INDEX.md, then
   `git log --oneline -10` + `git status --short` before touching anything.
   Docs and the index are claims, not facts — verify anything your task depends on.

2. **Evidence before action.**
   - Odd metric? Query the source data and decompose it yourself.
   - Suspicious artifact? Open the actual file (pickles: only ones this repo produced —
     unpickling executes code, never load untrusted pickle/joblib files).
   - Before deleting or changing a module: grep the ENTIRE repo (py/bat/md/yml) for
     importers AND runners; check log mtimes / `schtasks` to learn what actually runs.
   - "Impossible" crash in old code → check installed dependency versions vs. code
     assumptions (pandas/sklearn removals have bitten this repo).

3. **Baseline before refactor.** Dump comparable state (route tables, schemas,
   metrics) to a file first; diff after; identical-or-explained is the pass bar.
   Prefer scripted line-range transforms over hand-retyping for big moves.

4. **Execute in small commits** — one logical unit, message states what + why +
   evidence. Before `git add`: inspect every new file for secrets (password, hash,
   argon2, token, key). Never commit .env/credentials/data dumps; DO keep
   backend/.sqlx committed.

5. **Verify end-to-end, not just compile.** Ladder: static check → unit/function
   call → baseline diff → boot the real service and curl real endpoints. Only claim
   "verified" if you actually did it. Kill test servers afterward. Report failures
   honestly with output.

6. **Record.** Update shared/CODEBASE_INDEX.md when reality changes (mark done items
   with date, fix falsified claims — including your own earlier statements). Leave
   `git status` clean. Final message: outcome first, then how it was verified, then
   what remains.

## Project facts (verify if stale)

- Backend Rust :8888 — `SQLX_OFFLINE=true cargo check` in backend/; migrations auto-run at boot.
- Frontend :5173 — `npm run lint` (0 errors enforced) + `npm run build` in frontend/.
- Pipeline: use `py -3` (not `python`), run from pipeline/; API routers in api/routers/.
- Model sanity: model_v2.0.0.pkl must be CalibratedClassifierCV with 38 features.
- Retrain: `py -3 -m models.train_model_v2`; batch predict: `py -3 -m models.predict_v2`.
- Scheduling: Task Scheduler + run_daily_fetch_with_sync.bat / run_weekly_retrain.bat only.
- Two DBs on localhost:5432: football_betting (pipeline), football_heritage (backend); creds in per-service .env.
- Known failure patterns: static routes after `/{param}` get shadowed; sync work in
  `async def` endpoints blocks the loop; SQL aggregates need CTE for ORDER BY/LIMIT;
  `_v2` filenames don't prove v2 content.
