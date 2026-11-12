# NBA settled-performance latency fix

The reported frontend response was the Rust gateway's generic
`UPSTREAM_UNAVAILABLE` error. The development gateway allows 45 seconds for an
upstream request; the Python performance feed rebuilds completed-game evidence
on each request.

## Evidence and change

The endpoint succeeded during diagnosis, so the original intermittent error was
not directly reproduced. The shared result loader nevertheless performed 26,980
individual `pandas.to_datetime` calls in the recorded profile. Those calls took
18.4 seconds of a 23.7-second NBA result read, leaving little headroom when
requests compete for CPU.

`pipeline/models/sport_data.py` now parses historical event dates and availability
timestamps in batches. Each score capture reuses its parsed observation times.
Future games are still discarded before parsing their not-yet-recorded result
availability. Source scope, checksums, observed-result cutoff, conservative legacy
timestamps, conflict quarantine and canonical-game handling are retained.

No gateway timeout was increased, and no stale-response cache was added.

## Verification

- Saved the real pre-change response and forecast input under ignored `.release/`.
  After the change, all 9,343 result rows still produced 71 settled fixtures;
  the complete response and source-quality metadata matched the baseline at the
  same evaluation time.
- Result read and evaluation: 23.7 seconds before, 6.0 seconds after in separate
  cold diagnostic processes. Timing is machine/load dependent.
- Three concurrent real local gateway requests: HTTP 200 for pages 1–3 in
  9.65, 10.06 and 9.89 seconds, each reporting 71 eligible fixtures.
- Related loader, model, performance and historical-source suites: 47 passed,
  15 subtests passed. Adjacent gateway, intelligence, schedule and duplicate suites:
  46 passed, 3 subtests passed. Refined future-availability edge case: the focused
  12-test loader/performance selection passed again.
- Real local frontend loaded the performance table and the incorrect-result filter.
  Both requests returned 200; the 71-fixture summary denominator stayed unchanged;
  no JavaScript errors were recorded. Screenshot and JSON evidence are in ignored
  `.release/nba-performance-*` files.
- Fallow baseline retained 98 pre-existing findings; this analysis is focused on
  the JavaScript dependency graph and does not replace the Python regression checks.

The existing hosted publication task was stopped when checked. It was resumed so
new hosted computations can use the updated local loader. No data migration,
model training, promotion or account/financial operation was performed.

The real hosted frontend was verified too: its initial publication polling
completed with HTTP 200 for the full table and the incorrect-only view, 10 visible
history rows, unchanged 71-fixture summary, and no JavaScript errors. The two-view
cold/publication check took 61.4 seconds in total; this includes queue polling and
is not the per-request result-loader benchmark above.
