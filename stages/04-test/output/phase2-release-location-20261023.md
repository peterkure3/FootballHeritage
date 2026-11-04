# Phase 2 review location

Release work is on local branch `release/staging-20261023` in:

`D:\Github\FootballHeritage\.release\staging`

The original dirty checkout was preserved. Required pre-existing runtime source was captured separately in `bd4ef43`, security fixes in `1ba3020`, and staging configuration in `6767f2d`. Follow-up evidence commits are recorded on that branch. No branch was pushed or production deployed.

Read the review worktree's `docs/LOCAL_STAGING.md`, `docs/PRODUCTION_CHECKLIST.md`, and `stages/04-test/output/phase2-staging-verification-20261023.md`. It includes a detached clean-checkout CI report, 42 passing synthetic API smoke checks, real admin/user browser acceptance and explicit Docker/legacy-Node release blockers.

The active chatbot is Rust RAG. Node is legacy, excluded by default, and has five critical production-dependency audit findings. The Rust Docker image remains unverified because the local build worker fails to produce compiler output/artifacts. Native checks are not production approval.

The original checkout received only staging ignore rules, smaller Rust development/test artifact settings and this handover/integrity output. Its regenerable `backend/target/debug/incremental` cache was removed to reclaim 7.47 GiB; source and existing binaries were preserved. Windows successfully loaded the exact reported Actix proc-macro DLL afterward. Stale IDE diagnostics may require restarting rust-analyzer.
