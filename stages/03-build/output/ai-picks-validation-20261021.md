# Live AI Picks validation — 21 October 2026

**Verdict: the calculations are correct for the supplied inputs, but the current picks cannot be certified as reliable or correct predictions.** The live app is using v2.0.0, whereas the separately reviewed forecasts in the conversation used the inactive v2.1.0 candidate and expanded history. Neither model establishes guaranteed wins.

Audit snapshot: 2026-10-21T17:05:50.738214+00:00. The live pipeline endpoints returned HTTP 200. The authenticated Rust endpoint correctly returned 401 without a session. The frontend on port 5173 was unavailable and the browser-control kernel failed; this audit verifies the live data API and stored runs rather than claiming a visual inspection of the user's browser.

## Current seven UCL selections

| App selection | Probability | Decimal price | Gross model EV | Validation result |
|---|---:|---:|---:|---|
| Aston Villa FC–Viking FK: Draw | 25.0% | 7.800 (betika:UG) | +94.8% | Arithmetic passes; outcome unsettled |
| Real Betis Balompié–Feyenoord Rotterdam: Feyenoord Rotterdam (Away Win) | 27.4% | 4.800 (betonlineag) | +31.5% | quote_older_than_30_minutes |
| Real Madrid CF–RB Leipzig: RB Leipzig (Away Win) | 14.6% | 12.000 (betonlineag) | +74.7% | Arithmetic passes; outcome unsettled |
| Sporting Clube de Portugal–LASK Linz: Sporting Clube de Portugal (Home Win) | 73.1% | 1.374 (1xbet) | +0.4% | Arithmetic passes; outcome unsettled |
| FC Bayern München–Arsenal FC: FC Bayern München (Home Win) | 59.3% | Unavailable | Unavailable | degenerate_probability_vector; no_quote_to_validate_value |
| Club Brugge KV–Racing Club de Lens: Racing Club de Lens (Away Win) | 58.3% | Unavailable | Unavailable | no_quote_to_validate_value |
| FC Internazionale Milano–FK Shakhtar Donetsk: FC Internazionale Milano (Home Win) | 51.1% | Unavailable | Unavailable | no_quote_to_validate_value |

All seven fixtures start at 19:00 UTC / 22:00 Kampala. Their future results cannot be labeled correct or incorrect yet. Como–Manchester United and Lille–Galatasaray have already kicked off and were correctly excluded from the current pre-match endpoint. Saved historical runs naturally retain past fixtures; that retention is not itself a stale-pick bug.

## Confirmed reliability failures

1. **The backfill is not used by the active inference path.** The 38-feature v2.0.0 artifact enters `_build_legacy_feature_vector`, which queries the database and ignores the newer history/cutoff argument. The expanded history was exported for reviewed research, not imported into this legacy database path. Exact production-name history counts were Brugge 10, Lens 12, Bayern 27, Inter 32 and Shakhtar 2. Those counts differ materially from the four-season backfill.
2. **Bayern’s stored vector assigns draw probability exactly 0%.** Home is 59.3254%, draw 0%, away 40.6746%. The active artifact is a CalibratedClassifierCV. A fresh diagnostic also produces a 0% draw probability because the draw isotonic calibrator maps its base response to zero. The diagnostic home probability differs from the saved run (60.3591% versus 59.3254%); exact original inputs were not frozen, so it is not claimed as exact full-run reproduction. This is evidence of calibration fragility, not proof of the match outcome. Classic Best Picks accepts this vector while Intelligence rejects zero-outcome probability vectors.
3. **The batch predictor has a verified timezone selection bug.** The match date column is `timestamp without time zone`, the database timezone is Africa/Nairobi, and `get_upcoming_matches` compares its UTC wall-clock values against `NOW()`. At audit time that query selected zero of tonight’s UCL fixtures, while `NOW() AT TIME ZONE 'UTC'` selected seven. This can stop prediction refreshes up to three hours before kickoff. The API selection query already uses the UTC form, so the bug was not observed as seven missing API picks.
4. **Price freshness and market evidence are weaker in classic AI Picks.** Feyenoord’s 4.80 BetOnline price was timestamped 08:40 UTC, over eight hours before the audit. The classic route permits 24-hour quotes; Intelligence uses 30 minutes. Three selections have no stored quote at all. Stored `updated_at` alone does not verify upstream cache age, market openness or acceptance at a bookmaker.
5. **The two models disagree substantially on the leading value bets.** This does not prove the candidate is correct. It shows these EV claims are model-sensitive, not independently verified edges. At the app’s displayed price:

| Outcome | Active v2.0 probability | Reviewed v2.1 probability | Active gross EV | Reviewed gross EV at same app price |
|---|---:|---:|---:|---:|
| Draw in Aston Villa FC–Viking FK | 25.0% | 11.8% | +94.8% | -8.3% |
| Feyenoord Rotterdam (Away Win) in Real Betis Balompié–Feyenoord Rotterdam | 27.4% | 17.1% | +31.5% | -18.1% |
| RB Leipzig (Away Win) in Real Madrid CF–RB Leipzig | 14.6% | 6.3% | +74.7% | -24.3% |

The v2.1 values above are the previously frozen review, not a new in-play forecast. Its holdout evaluation did not prove market superiority. The fresh public bookmaker capture at 17:08 UTC was retained separately in `pipeline/data/raw/ucl_revision_20261021T170833Z`; it does not independently establish execution of the app’s Betika, BetOnline or 1xbet prices.

## Latest completed saved run

Saved 2026-10-20 20:24:42.618327+03:00, requested date 2026-10-20: **2 wins from 7 selections (28.6%); 5 losses.** All selected predictions and the saved run preceded kickoff. Results are completed regulation-time scores from the archived football-data.org CL response captured before today’s matches.

| Fixture | Saved selection | Final score | Correct? |
|---|---|---|---|
| FC Porto – PSV | PSV (Away Win) | 0–1 | Yes |
| AS Roma – ŠK Slovan Bratislava | Draw | 4–0 | No |
| Manchester City FC – PAE AEK | Draw | 5–1 | No |
| Paris Saint-Germain FC – FC Barcelona | Paris Saint-Germain FC (Home Win) | 4–2 | Yes |
| SSC Napoli – FK Bodø/Glimt | FK Bodø/Glimt (Away Win) | 4–3 | No |
| Liverpool FC – Villarreal CF | Villarreal CF (Away Win) | 4–3 | No |
| VfB Stuttgart – Club Atlético de Madrid | VfB Stuttgart (Home Win) | 1–1 | No |

For the 6 selections with stored prices, a hypothetical one-unit stake per quoted pick gives net +2.67 units before tax/fees. One unpriced selection is excluded from that profit calculation. This is a paper calculation from saved prices, not verified placed bets or evidence of long-run profitability. Duplicate saved runs were not pooled.

## Checks and disposition

- Five existing AI Picks unit tests and 24 betting-intelligence tests passed. The initial module-style test invocation could not import the test modules; discovery-style invocation completed successfully.
- All seven current displayed EV and edge calculations were recomputed successfully. Probability sums were checked; the Bayern zero-draw issue was flagged even though its selected home probability is nonzero.
- Fallow reported preexisting repository issues (310 dead-code findings, 44 clone groups, 173 complexity findings); no production code was changed in this audit.
- No model promotion, prediction replacement, database write or bet was performed. Fix the legacy input integration, timezone cutoff, zero-probability handling and price freshness before treating current value labels as validated recommendations.

Artifacts: `ai-picks-live-audit-20261021.json`, `ai-picks-deep-audit-20261021.json`, `ai-picks-validation-20261021.json`.
