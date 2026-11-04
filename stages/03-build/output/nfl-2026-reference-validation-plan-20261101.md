# Frozen reference comparison for 2026

Development selection retained the 16-feature history recipe. Before scoring any
2026 outcomes, add an operationally useful comparison to the existing frozen NFL
artifact `20261015T194812812329Z/nfl` (model SHA-256
`3a9e693fd51a61a4aa8f9e7410c578decec38a1d4cb519eebc8e2182689005c7`).
Do not change the new selection gates or fit another model based on this test.

Verify its original dataset/model hashes and replay its original 900 test metrics
to 1e-12. Preserve its 2000-onward historical state; do not feed it the new
candidate's 2014-start feature matrix. Overlapping native fixture IDs must agree
on exact teams, kickoff, scores and neutral-site policy. Only append newly known
games after its last saved game. Reject earlier missing IDs or disagreements
instead of silently backfilling/revising its historical state.

Evaluate the frozen reference and newly selected/refitted candidate on the exact
same 2026 non-tied targets. Report paired NFL-week bootstrap intervals, calibration,
artifact size and latency, plus fixed-model seven-day availability sensitivity.
Candidate parameters were selected on 2020–2025 development seasons. The new
recipe includes a more recent tuning/calibration period; this comparison does
not isolate dataset size from training/calibration freshness.

The main artifact's broad old report included some 2026 results. This remains
retrospective validation, not new prospective evidence. No automatic promotion,
production change, staging or commit is authorized by the comparison.
