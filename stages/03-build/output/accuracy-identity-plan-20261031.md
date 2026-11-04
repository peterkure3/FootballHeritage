# Accuracy experiment 2: reviewed identity consistency

Experiment 1 found no acceptable model improvement. Do not promote its context
features or retune against its evaluation labels.

Experiment 2 isolates a known data consistency question: apply only the existing
reviewed `league_data.identity_aliases` mapping to source team names, then rebuild
causal history. Compare the same logistic C=.01 with sigmoid calibration under
original versus reviewed identities. No new fuzzy matches or learned aliases.

Deduplicate actual fixture identities first for both arms, fail on conflicting
scores, align each arm by stable fixture IDs, and use the same three expanding
development folds and separate calibration periods. Exclude the saved latest
candidate's final test period entirely. Use identical scored games in both arms.
Report accuracy, log loss, Brier and fold consistency; do not promote without
fresh prospective evidence. Next-day availability remains an explicit assumption.
