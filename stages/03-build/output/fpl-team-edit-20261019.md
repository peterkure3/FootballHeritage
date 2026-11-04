# FPL team editor

## Existing logic

The advisor generated an optimal squad but had no editing or user-team persistence endpoint. `/fpl/players` already provided the catalog. The optimizer defines the £100m budget, 15-player composition (2 GKP/5 DEF/5 MID/3 FWD), three-per-club limit, seven supported formations, 11 starters and double captain points.

## Changes

- Added Edit team beside the suggestion, with searchable same-position replacements, starter checkboxes, captain and vice-captain controls, Save and Cancel.
- Added `POST /api/v1/fpl/team/evaluate` accepting `squad_ids`, `starter_ids`, `captain_id`, `vice_captain_id`. Returns the existing FPLTeamResponse shape; invalid squads return 422 with an actionable explanation. Uses current cached players and existing optimizer constants; no client-supplied prices or scores are trusted.
- Saved drafts are browser-local and scoped by signed-in account and gameweek. Reset returns to the latest suggestion. Storage failures are surfaced and preserve the open draft. Data refresh does not silently overwrite the saved team; its saved timestamp and projection refresh instructions remain visible.
- Changes do not submit transfers to the official FPL service. No database migration or external account integration added.

## Verification

- Three Python tests passed, including thirteen invalid-draft subcases and captain bonus, exact budget, bench and alternate-formation calculations.
- Isolated HTTP server exercised real cached FPL data: valid team 200 (£77.3m, 73.3 expected points), invalid captain pairing 422. Temporary server stopped afterward. TestClient was unavailable because optional httpx is not installed; verification used uvicorn and standard-library HTTP instead.
- The running pipeline API on port 5555 exposes the new route in OpenAPI.
- Frontend production build and TypeScript passed. Targeted ESLint passed.
- Browser coverage includes desktop/mobile replacements, captain controls, saving, reloading, cancelling, resetting, catalog retry, validation errors and Escape focus restoration. Existing FPL navigation and layout checks also passed.
- Fallow audit recorded in `fpl-edit-fallow.json`; repository-wide audit still reports findings across the pre-existing working tree.
- No commit or deployment performed; unrelated changes preserved.
