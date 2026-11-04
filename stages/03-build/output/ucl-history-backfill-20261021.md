# UCL history backfill — 21 October 2026

Collected 884 additional unique fixtures. The reconciled export contains **2,815 unique fixtures**, with **2,757 eligible regulation-time results** across all 18 clubs. Fixtures involving two target clubs count once in the combined export and once for each club in the team table.

Scope: 2023/24, 2024/25, 2025/26 and current 2026/27; Viking uses calendar seasons 2023–2026. Results stop before 21 October 2026 UTC, so tonight’s outcomes cannot leak into history. Senior competitive matches only; exhibitions are excluded.

**Remaining qualification:** 58 records are retained outside the training CSV, including awarded matches and extra-time/penalty results whose 90-minute score was not independently established. A shootout score is stored separately from match goals. Coverage matches all 2,810 dated completed fixtures parsed from the reviewed season inventories; this is not a claim that every provider is exhaustive.

| Team | Previous results in scope | Results now | Newly found | Eligible 90-minute results | Season counts, oldest first | Latest five |
|---|---:|---:|---:|---:|---|---|
| Como | 85 | 132 | 47 | 130 | 39 / 39 / 45 / 9 | WLDLW |
| Man United | 129 | 163 | 34 | 155 | 52 / 61 / 40 / 10 | LDDLD |
| Lille | 121 | 157 | 36 | 151 | 49 / 51 / 48 / 9 | WLWLD |
| Galatasaray | 136 | 174 | 38 | 172 | 56 / 55 / 53 / 10 | WLWLW |
| Aston Villa | 135 | 180 | 45 | 178 | 56 / 57 / 56 / 11 | WWDWW |
| Viking | 115 | 142 | 27 | 140 | 36 / 34 / 41 / 31 | WWWDW |
| Club Brugge | 24 | 192 | 168 | 191 | 63 / 59 / 58 / 12 | WWWWW |
| Lens | 117 | 130 | 13 | 126 | 43 / 37 / 40 / 10 | DLWLW |
| Bayern Munich | 150 | 170 | 20 | 170 | 49 / 55 / 56 / 10 | WWDDW |
| Arsenal | 162 | 185 | 23 | 182 | 53 / 58 / 63 / 11 | WLWWW |
| Inter | 156 | 175 | 19 | 173 | 49 / 63 / 54 / 9 | WDWLW |
| Shakhtar Donetsk | 16 | 148 | 132 | 143 | 42 / 42 / 52 / 12 | WWWWW |
| Real Madrid | 166 | 190 | 24 | 185 | 55 / 65 / 59 / 11 | WLWWW |
| RB Leipzig | 126 | 139 | 13 | 139 | 45 / 47 / 38 / 9 | WLWWL |
| Betis | 125 | 174 | 49 | 173 | 49 / 59 / 55 / 11 | WDWWL |
| Feyenoord | 131 | 154 | 23 | 152 | 48 / 50 / 45 / 11 | WWWWW |
| Sp Lisbon | 134 | 175 | 41 | 166 | 54 / 55 / 56 / 10 | WDDWW |
| LASK Linz | 2 | 145 | 143 | 139 | 44 / 48 / 38 / 15 | LDLLW |

## Corrections and validation

- Expanded Brugge, LASK and Shakhtar from sparse European-only records to domestic league and cup history. Retrieved Como’s Serie B season, European qualifiers, domestic cups and supercups where covered.
- Rejected wrong provider identities (Sporting/Santos and Brugge/Batang) before final export. All retained ESPN team identities and Transfermarkt page titles were checked against reviewed club aliases/native IDs.
- Galatasaray–Adana Demirspor on 9 February 2025 and Galatasaray–Fenerbahçe on 7 April 2024 were awarded results. They remain in the historical record with training disabled.
- Viking’s 1 October 2026 cup win at Madla and Brugge’s 17 October result are present. Villa’s available recent sequence is now WWDWW and Brugge’s is WWWWW; this supersedes the narrower sequences in the earlier betting review.
- 19 end-to-end checks passed: checksums, 18 club exports, all four seasons, score/status eligibility, duplicate removal, inventory reconciliation, causal cutoff and unchanged candidate model. No unresolved score conflicts remain.
- Additional football-data.co.uk CSV requests timed out; existing archived CSVs, ESPN, Transfermarkt and Terrikon supplied the usable histories. No denied ESPN API access was bypassed.

## Artifacts

- [All competitive results CSV](../../../pipeline/data/raw/ucl_history_20261021/all_results.csv)
- [Regulation history CSV](../../../pipeline/data/raw/ucl_history_20261021/regulation_history.csv)
- [Per-team CSV folder](../../../pipeline/data/raw/ucl_history_20261021/teams/)
- [Coverage and source manifest](../../../pipeline/data/raw/ucl_history_20261021/coverage.json)
- [Verification](ucl-history-verification-20261021.json)
- `all_results.json` retains the individual source observations supporting each accepted fixture.

No database or active-model writes were made. The earlier probabilities and EV estimates have not been recalculated on this expanded history and should not be represented as updated forecasts.

Sources: [ESPN public results](https://www.espn.com/soccer/team/results/_/id/132/season/2023/league/all), [Transfermarkt season schedules](https://www.transfermarkt.com/club-brugge-kv/spielplan/verein/2282/saison_id/2023), [Terrikon archives](https://terrikon.com/en/football/teams/1376/gamesarchive), [Viking official results](https://www.vikingfotball.no/resultater), [RSSSF Norway cup archive](https://www.rsssf.no/archive.html), [Galatasaray’s abandonment record](https://www.galatasaray.org/haber/futbol/galatasaray-adana-demirspor-maci-tatil-edildi/57198).
