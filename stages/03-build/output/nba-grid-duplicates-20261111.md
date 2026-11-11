# NBA bookmaker grid duplicate protection

Date: 2026-11-11

The running Rust gateway's NBA intelligence endpoint returned 10 unique upcoming
games and 29 unique fixture/bookmaker h2h quotes. No duplicate games or quote keys
were present in the observed snapshot. Identical prices at separate bookmakers
remain separate evidence.

## Change

The API previously iterated saved fixture rows without deduplicating them. A
repeated or cross-provider row could therefore duplicate forecasts, quotes and
summary counts consumed by the NBA grid. Refresh-time merging did not protect
reads of an already saved snapshot.

`pipeline/api/betting_intel.py` now coalesces eligible NBA fixtures by canonical
reviewed team identity, home/away orientation, exact UTC kickoff and settlement
rule. All offers are retained for the existing latest-price, freshness and
same-time conflict checks. The latest valid forecast is retained. Inputs are not
mutated. Other sports retain their API behavior.

`pipeline/etl/betting_intel.py` imports the shared merger instead of maintaining
another implementation. Settlement rules are now part of refresh-time identity
too, preventing regulation and overtime evidence from being combined.

## Verification

- New regression suite: `pipeline/tests/test_nba_grid_duplicates.py` (8 tests).
- Tests cover repeated rows, cross-provider aliases and timezone equivalence,
  distinct rematches/orientation/settlement, valid forecast selection, latest
  prices, conflicting prices, input immutability and ineligible rows.
- FastAPI HTTP checks use a temporary duplicate snapshot and verify that the NBA
  endpoint and overview both report a single game and quote.
- Clean checkout with only this fix: `py -3 -m pytest
  tests/test_nba_grid_duplicates.py tests/test_betting_intel.py
  tests/test_nba_public_odds.py -q` from `pipeline/`: **45 passed**.
- Existing working tree: the same command reports **46 passed, 3 subtests passed**.
  The extra test belongs to pre-existing uncommitted work. Both runs reported two
  existing `datetime.utcnow()` deprecation warnings.
- Fallow before/after results unchanged: 98 existing dead-code findings,
  45 clone groups, 3.7% duplication and 195 functions above complexity threshold.
  Fallow warned that root node_modules is absent; it does not analyze Python.

No data migration, model refresh or deployment is required by this source change.
The running service must load the updated Python code before it uses the guard.
Unrelated uncommitted work is excluded from this commit.
