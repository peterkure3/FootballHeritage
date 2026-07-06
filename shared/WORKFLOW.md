# Engineering Workflow — Operating Manual

Audience: any AI agent (or human) working in this repo, regardless of model size.
Follow this loop and you will produce senior-level work. The rules are concrete on
purpose — when in doubt, do the literal thing the checklist says.

Companion skill: `/workflow` loads a condensed version of this file into context.

---

## The Core Loop

Every task, no exceptions:

```
ORIENT → INVESTIGATE → PLAN → EXECUTE (small verified steps) → VERIFY END-TO-END → RECORD
```

Never skip INVESTIGATE to get to EXECUTE faster. Nearly every serious bug found in
this repo (mislabeled ML model, broken wallet endpoints, shadowed API routes) was
found because someone checked evidence instead of trusting a doc or a filename.

---

## 1. ORIENT (5 minutes, read-only)

1. Read `AGENTS.md` → `CONTEXT.md` → `shared/CODEBASE_INDEX.md`. That is the ICM
   layer order (L0 → L1 → shared reference).
2. Run `git log --oneline -10` and `git status --short`. Know what branch you're on
   and what's dirty BEFORE touching anything.
3. State (to the user, in one sentence) what you're about to do before the first
   tool call.

**Rule: the index and docs are claims, not facts.** They record what was true when
written. Verify any claim that your task depends on (see §2).

## 2. INVESTIGATE — evidence beats assumption

The single most important habit. Concrete techniques, all used successfully here:

- **Reproduce the number.** If a metric/claim looks odd (e.g. "accuracy 34.65%"),
  query the source data yourself and decompose it (distributions, confusion matrix,
  denominators). Do not theorize before looking.
- **Open the artifact.** Docs said the model was a v2 ensemble; unpickling it showed
  a v1 XGBClassifier. `joblib.load(...)` / reading the actual file settles arguments.
  ⚠️ Unpickling executes code: only load pickles this repo's own pipeline produced
  (`models/model_store/`). Never joblib/pickle-load a downloaded or user-supplied file.
- **Map usage before changing/deleting anything.**
  `grep -rn "import X\|from X" --include="*.py"` (or rg) across the WHOLE repo,
  including .bat/.md/configs. A file with zero importers can still be run by a
  scheduler or bat script.
- **Check what actually runs, not what could run.** Log file mtimes
  (`ls -lt *.log`), `schtasks //query`, missing log files — these told us which of 4
  schedulers was real (answer: none were registered; bats were the documented path).
- **When old code crashes on "impossible" errors, suspect dependency bit-rot.**
  pandas 2.x, scikit-learn 1.6/1.7 removals broke v2 training silently. Check
  installed versions vs. what the code assumes.
- **Correct your own record.** When evidence contradicts your earlier analysis
  (port 8888 vs 8080, "stray" package.json that wasn't), say so explicitly and fix
  the index. Never quietly drop a wrong claim.

## 3. PLAN — decompose into independently verifiable steps

- Split work into streams that each end in a commit (e.g. "gitignore+ICM",
  "CI", "routes split", "migrations").
- For each step, decide UP FRONT how you will prove it worked (the verify gate in
  §5). If you can't name the proof, the step is too vague.
- **Capture a baseline before any refactor** so you can diff after. Example: dump
  the FastAPI route table to JSON before splitting routes.py, diff after — 31/31
  routes identical is proof; "it looks right" is not.
- Long-running work (model training, big builds) goes to background immediately;
  do other streams while it runs. Fix-rerun loops are normal: train → crash →
  fix → retrain (it took 4 attempts here; that's fine).
- Prefer mechanical transforms via script over hand-retyping. The 3,502-line file
  was split by a line-range script — zero transcription errors possible.

## 4. EXECUTE — guardrails

- **Small commits, one logical unit each.** Message says WHAT and WHY, including
  evidence ("verified live: validate-data 422 → 200").
- **Before deleting/overwriting anything: look at it.** `head` the file. The two
  "junk" SQL scripts here contained a plaintext admin password — committing them
  would have been a security incident. Check every file for secrets before
  `git add` (grep for password, key, token, hash, argon2).
- Never commit: .env files, credentials, data dumps, build artifacts.
  DO commit: `.sqlx/` offline cache (CI needs it), lockfiles, migrations.
- Match the surrounding code's style. Comments only for non-obvious constraints
  (e.g. "float, or pandas 2.x raises LossySetitemError"), never narration.
- Use static analysis to close gaps a compiler won't: `pyflakes` for undefined
  names after moving Python code; eslint on exactly the files you touched.
- Destructive ops (DB writes, force-push, rm): re-check the evidence supports the
  SPECIFIC action, and prefer the reversible variant. Git history is your undo for
  deletions — delete tracked files freely once usage-mapped; never `rm` untracked
  work you didn't create.

## 5. VERIFY — end-to-end, not just compile

Compile/lint passing is the FLOOR. The proof ladder, climb as high as the change
warrants:

1. Static: `cargo check` / `pyflakes` / `eslint` / `py -3 -m compileall -q`
2. Unit: `cargo test`, targeted function calls (`py -3 -c "from x import f; print(f(...))"`)
3. Behavioral diff: baseline-vs-after comparison (route tables, schemas)
4. **Live**: boot the service, hit real endpoints with curl, observe real responses.
   The routes split was proven by starting uvicorn and exercising 5 routers; the
   migration change by booting the backend and watching it migrate + serve /health.
5. Clean up after verification (kill test servers, remove temp files).

Report outcomes faithfully: failing tests are reported with output, skipped steps
are named. If you claim "verified", the transcript must show the verification.

## 6. RECORD

- Update `shared/CODEBASE_INDEX.md` when reality changes (mark items ~~done~~ with
  date, correct falsified claims).
- Leave the working tree clean: `git status --short` empty at handoff.
- End with a summary that leads with the OUTCOME, states what was verified and how,
  and lists what remains with enough context that a fresh session can resume.

---

## Project Quick Reference (FootballHeritage)

| Thing | Value |
|---|---|
| Backend (Rust) | port **8888**; `SQLX_OFFLINE=true cargo check` from `backend/`; migrations auto-run at boot |
| Frontend | Vite :5173; `npm run lint` (0 errors enforced) + `npm run build` from `frontend/` |
| Pipeline API | `py -3 -m uvicorn api.main:app --port 5555` from `pipeline/`; routers in `api/routers/` |
| Python | invoke as `py -3` (plain `python` is not on PATH); run from `pipeline/` so `sys.path` shims work |
| ML model | `models/model_store/model_v2.0.0.pkl` must be CalibratedClassifierCV w/ 38 features — if it's XGBClassifier/12, something re-ran a bad trainer |
| Retrain / predict | `py -3 -m models.train_model_v2` / `py -3 -m models.predict_v2` |
| Scheduling | Windows Task Scheduler + `run_daily_fetch_with_sync.bat` (daily), `run_weekly_retrain.bat` (weekly). No other scheduler exists. |
| DBs | postgres@localhost:5432 — `football_betting` (pipeline), `football_heritage` (backend). Creds in each service's `.env` (never commit) |
| CI | `.github/workflows/ci.yml` — keep all 4 jobs green |
| Known sensitive | `backend/scripts/*password*.sql`, `fix_admin_role.sql` are gitignored on purpose; older tracked SQL still contains hashes (rotation pending) |

## Failure Patterns Seen In This Repo (check these first)

- Route order: static paths registered AFTER a `/{param}` route are shadowed (422s).
- `async def` FastAPI endpoints doing sync SQLAlchemy/requests work block the event
  loop — use plain `def` (threadpool) or async drivers.
- SQL: aggregates + `ORDER BY/LIMIT` need a CTE/subquery; f-string SQL is only safe
  with constant fragments — parameterize all values.
- Version-suffixed files (`_v2`) sharing config constants (MODEL_VERSION) can
  mislabel artifacts — a "v2" filename proves nothing about content.
- Docs drift: README/docs referenced wrong ports and dead workflows; trust `.env.example` and code over prose.
