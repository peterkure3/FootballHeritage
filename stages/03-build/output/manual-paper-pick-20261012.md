# Manual Newcastle paper selection — 12 October 2026

User requested Newcastle to win away at Coventry. Recorded one paper unit at
AbaBet Uganda's captured decimal price **2.05**, at **18:50:24 UTC**, before the
fixture's **19:00 UTC** kickoff (22:00 EAT). The price was observed at
18:40:07 UTC and passed the 15-minute complete-market check.

Immutable manual trial:
`pipeline/data/processed/edge_trials/1a3c42053e55dc4ba5d57796926882eda1ece1414f25addc793181869a666f1a/trial.json`.
The API fixture snapshot and hash are retained in
`pipeline/data/raw/manual_paper_choices/`. Runtime artifacts remain gitignored.

The original frozen candidate forecast has **no selection**: Newcastle's 4.29%
stressed estimated EV at its original 2.20 quote missed the fixed 5% rule. Its
forecast and policy were preserved. The manual entry uses a different policy
and study identity and is excluded from the frozen study's formal assessment.
Its stored active-model probabilities are context, not the selection rule.

## Reusable workflow

From `pipeline/`:

```powershell
py -3 -m scripts.record_manual_paper_pick --match-id 560597 --selection away_win
```

The recorder accepts home_win, draw or away_win. It selects the highest actual
price among complete quotes observed within 15 minutes, rejects kickoff-passed
fixtures and stale model context, saves source evidence and imports an immutable
trial. Repeating the same choice returns the existing record; changing an
existing manual outcome is rejected. It records paper selections only.

**Predictions → Paper trials** labels the entry **Manual paper selection** and
shows its actual bookmaker. The existing scheduled result collector settles it
against the verified regulation-time final, separately from the frozen study.
Manual choices cannot suppress new frozen-trial fixture collection.

## Live verification

The normal :5555 API returns the manual away-win entry at 2.05 as pending.
The frozen study remains at six recorded/settled selections and zero pending;
the separate manual study has one recorded selection and one pending. No
real-money bet was placed.

## Validation

- Three manual-recording/settlement/isolation tests and nine frozen-study tests
  passed. Started fixtures and stale prices are rejected; manual wins settle
  using actual prices without sharing the frozen study's denominator.
- Four Chromium paper-trial checks passed, including manual labeling and the
  existing pending, collector-health and formal-assessment views. Initial browser
  failures exposed test/legacy records without policy metadata; the display now
  handles those records too.
- Frontend lint had zero errors and the existing AdminEvents hook warning.
  Type checking and production build passed. Python syntax compilation passed.
- Fallow 3.32 audit passed; missing root node_modules still limits dependency
  classification and Python is outside its coverage.
