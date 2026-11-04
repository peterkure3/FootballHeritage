# Accuracy goal: first research milestone

Goal remains active. No production models, registries or serving schemas changed.
Nothing staged or committed. Soccer is the first workstream; other sports have
not yet been optimized in this goal.

## Diagnosis

The latest global candidate's test period has 1,894 matches but only 52 with
recorded odds, so headline accuracy mainly measures its history expert. Existing
archive collectors also hard-code old seasons; recent historical price coverage
is incomplete. Historical price timestamps are not verified and must not be
relabeled as strict prematch evidence. Reviewed names contain 72 genuine cases
of feature-key fragmentation, beyond harmless display-name differences.

## Experiments executed

1. Fixed development-only context experiment over 7,271 expanding-fold forecasts:
   baseline 51.41%, context logistic 51.52%, context gradient 49.04%. Context
   logistic slightly worsened Brier score; neither candidate met the preregistered
   acceptance rule. Neither was promoted or saved as a production candidate.
2. Paired reviewed-identity-only development experiment: 51.41% to 51.66%, better
   log loss and Brier. The accuracy gain appears only in the latest fold.
3. Frozen retrospective comparison against the saved history expert, with the
   exact original train+tune/calibration/test date ranges and identical fixtures:

| Metric | Original history expert | Reviewed-identity candidate |
|---|---:|---:|
| Matches | 1,894 | 1,894 |
| Accuracy | 48.26% | 49.63% |
| Log loss | 1.02132 | 1.01781 |
| Brier score | 0.61200 | 0.60857 |

There are 26 additional correct forecasts, a 1.37 percentage-point increase.
Exploratory paired match-day bootstrap (2,000 draws, seed 42): accuracy change
95% interval +0.23 to +2.55 points; log-loss difference -0.01037 to +0.00331.
The probability-scoring improvement is not statistically established. These
intervals are conditional on this corpus; repeated evaluation and source
availability assumptions remain.

Artifact: `pipeline/models/model_store/research/accuracy_identity_20261031/`.
It contains an inactive history-only model, exact reviewed alias map, source
checksums, detailed metrics and paired prediction rows. Restored-artifact
probabilities reproduced the saved forecasts to 1e-12. Do not use it through the
existing active loader: its identity map is part of the input contract, and it
does not contain a market expert. No claim that it improves the complete active
2.0.0 serving path or other sports follows from this result.

## Checks

- Three new causal feature tests passed: current/future results cannot alter
  earlier features, same-day results remain unavailable, preprocessing is fitted
  only within estimators.
- Existing model-pipeline tests: 17 passed. Existing reviewed-identity tests:
  six passed. Python syntax checks and git diff --check passed.
- Paired fixtures and labels match between identity arms. Conflicting merged
  scores or changed fixture membership fail instead of silently altering results.
- Fallow remains unavailable; no successful Fallow analysis is claimed.

## Next work and limits

The retrospective test period had already been inspected for earlier models; it
is not a fresh confirmation set. Result availability uses the existing next-day
assumption, not verified historical receipt times. No profit or calibration claim
is made. Broadly higher accuracy is not yet achieved across the multisport app.

Next: freeze identity treatment and prospective evaluation policy, record fresh
inactive forecasts before kickoff, improve recent-season data completeness with
provenance, and compare additional candidates only on development folds. Any
future promotion requires fresh evidence and complete serving-input parity.
