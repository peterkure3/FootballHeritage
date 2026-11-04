# Follow-up NBA inactivity experiment

The first predeclared experiment rejected recency weighting and gradient boosting
on development folds. Before this follow-up runs, freeze one additional policy:
after at least 90 days without an available result for a team, clear its rolling
score history and regress its Elo halfway toward 1500. Use exactly the same
baseline logistic C=0.1, calibration, folds, purging, dataset and excluded test
boundary as `accuracy-nba-training-plan-20261101.md`. No parameter sweep.

Motivation: long gaps can make retained rolling form misleading. This policy
does not infer roster changes or distinguish source gaps from true inactivity.
Historical coverage is incomplete; any effect may reflect the source gaps.
It is one further development-selected experiment, with the same promising
criteria, not independent confirmation of the preceding comparison.

Do not change production feature construction. Freeze outputs separately under
`stages/04-test/output/accuracy-nba-inactivity-20261101/`. A promising development
result still requires further validation. No staged files or commits.
