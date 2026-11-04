# Settled performance competition dropdown

Replaced the free-text competition filter with a native labeled select and
an All competitions option. Options come from the existing unfiltered settled
accuracy summary and remain available when a league/date/model filter changes.
The selected league still applies to both the performance summary and history,
and changing it resets pagination.

Validation: targeted ESLint, git diff --check, and the Chromium settled-filter
test passed. The browser test selects a competition, verifies the league query
parameter and selected value, and clears the selection before the existing date
and correctness checks.
