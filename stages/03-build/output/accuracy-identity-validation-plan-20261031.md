# Frozen identity-only retrospective validation

Development experiment: 51.4097% original versus 51.6573% reviewed identities,
with better log loss/Brier but accuracy gain confined to the latest fold. No
context features or gradient models are carried forward.

Freeze logistic C=.01, existing history-only columns, reviewed static aliases,
and sigmoid calibration. Fit on the original candidate's train+tune dates,
calibrate on its original calibration dates, and compare on the exact same test
fixtures with its saved history expert. No tuning, threshold selection or odds.
Fail rather than silently merging conflicting scores or changing membership.
Persist a research-only candidate only if accuracy, log loss and Brier all improve.

This final period has already been inspected for earlier models. It is an
out-of-training retrospective check, not a fresh untouched confirmation. No
production promotion follows; prospective evaluation is still required.
