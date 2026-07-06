---
name: handover
description: Load the departing consultant's handover — judgment heuristics, the project's institutional knowledge, case studies of past incidents (model swap, broken wallet column, shadowed routes), current risk ranking, and how to work with AI agents on this repo. Use when onboarding to FootballHeritage, asking "why is X like this", planning priorities, or before touching money paths (wallet/betting/settlement), the ML model, or the intelligence layer.
---

# FootballHeritage Handover Knowledge

Read `shared/HANDOVER.md` in full now — it is the judgment layer that complements
`shared/WORKFLOW.md` (process). Apply both. The distilled contract:

## Judgment heuristics

1. **Pull the thread** — a surprising number/error is a door, not noise. Decompose
   it (denominators, distributions, actual artifacts) before explaining it away.
2. **Distrust labels, verify referents** — filenames, version stamps, "applied",
   "disabled", and docs have all been false in this repo. Open the file, query the
   table, curl the endpoint.
3. **Find what actually runs** — log mtimes, `schtasks //query`, missing logs.
   Paper infrastructure ≠ real infrastructure.
4. **Fix the measurement before judging the system** (the accuracy metric was
   wrong before the model was).
5. **Bugs come in litters** — found one instance? Grep for the whole class.
6. **Baseline → scripted transform → diff → live smoke** makes big refactors safe.
7. **Correct your own record out loud**; update shared/CODEBASE_INDEX.md when
   reality changes.
8. **Everything is public once committed** — grep new files for
   password/hash/token/key before every `git add`.
9. **Evidence lives in commit messages** ("verified live: 422 → 200").
10. **Guardrails before features** — CI/lockfiles/gitignore found real bugs in
    minutes here.

## Project truths (as of 2026-07-06 — verify if stale)

- The product's edge is the devig/EV/arbitrage intelligence layer, not the match
  classifier (56.8% val is near the odds-implied ceiling for 3-class football).
- Odds math exists in THREE places (pipeline api/odds_math.py, backend
  intelligence.rs, frontend useParlayCalculator.js) — divergence there loses real
  money; cross-check when touching any of them.
- Nothing is scheduled: Task Scheduler entries for run_daily_fetch_with_sync.bat /
  run_weekly_retrain.bat must be registered or data goes stale.
- Admin bet-settlement routes are commented out in backend main.rs — bets can be
  placed but not settled via API.
- RoleSwitcher.jsx is cosmetic; real authz = backend is_admin/is_super_admin only.
- Chatbot RAG tables exist in no database (SQL preserved in chatbot/sql/).
- Open severity-1: rotate Admin123!, purge hash-bearing SQL from git history.
- sqlx 0.7.4 has future-incompat warnings; plan the 0.8 upgrade.

## Case studies to remember (details in HANDOVER.md Part 1)

- **Model swap**: "v2.0.0" pickle was actually v1 architecture — bit-rotted v2
  trainer + shared MODEL_VERSION constant + no CI. Check
  `models/model_store/model_v2.0.0.pkl` is CalibratedClassifierCV/38-features.
- **Wallet column**: code queried a column no migration created; fix sat unapplied
  at repo root while migrations were "temporarily" disabled.
- **Shadowed routes**: 7 endpoints dead-on-arrival from registration order —
  observe the running system, not just the code.
