"""Verify the stored backfill and render a coverage report from actual records."""
import json,hashlib,sys,collections
from pathlib import Path
from datetime import datetime,timezone
import pandas as pd
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent;RAW=ROOT/'pipeline/data/raw/ucl_history_20261021'
sys.stdout.reconfigure(encoding='utf-8')
report=json.loads((RAW/'coverage.json').read_text());rows=json.loads((RAW/'all_results.json').read_text());training=pd.read_csv(RAW/'regulation_history.csv')
checks={}
def check(label,condition):
    checks[label]=bool(condition)
    assert condition,label
check('18_clubs',len(report['coverage'])==18)
check('four_seasons_each',all(len(c['season_counts'])==4 for c in report['coverage']))
check('full_seasons_at_least_30_records',all(all(n>=30 for season,n in list(c['season_counts'].items())[:3]) for c in report['coverage']))
check('no_page_identity_errors',not [p for p in report['pages'] if 'error' in p])
check('all_known_inventory_matches_retained',not report['tm_inventory_missing'])
check('no_unresolved_score_conflicts',report['conflicted_fixtures']==0)
check('row_count',len(rows)==report['unique_results'])
check('training_count',len(training)==report['training_results'])
check('pre_match_cutoff',all(pd.Timestamp(r['date'])<pd.Timestamp('2026-10-21',tz='UTC') for r in rows))
def key(r):return r['date'][:10],r['target_teams'][0],r['home_team']==r['target_teams'][0]
check('no_duplicate_fixtures',len({key(r) for r in rows})==len(rows))
check('training_labels_verified',all(r['training_eligible'] and r['home_score'] is not None and 'unverified' not in r['score_basis'] and r['status']!='AWARDED' for r in rows if r['training_eligible']))
check('no_shootout_scores_as_goals',all(r['home_score'] is None and r['away_score'] is None for r in rows if r['score_basis']=='shootout_only_regulation_missing'))
check('awarded_games_excluded',len([r for r in rows if r['status']=='AWARDED'])>=2 and all(not r['training_eligible'] for r in rows if r['status']=='AWARDED'))
check('no_exhibitions',not any(any(x in str(r['competition']).lower() for x in ['friendly','friendlies','emirates cup','all-star']) for r in rows))
check('all_source_checksums',all(hashlib.sha256((ROOT/file).read_bytes()).hexdigest()==v['sha256'] for file,v in report['source_files'].items()))
check('18_team_exports',len(list((RAW/'teams').glob('*.csv')))==18)
check('viking_october_cup_retained',any(r['date'].startswith('2026-10-01') and r['away_team']=='Viking' and r['away_score']==3 and r['home_score']==0 for r in rows))
check('brugge_october17_result_retained',any(r['date'].startswith('2026-10-17') and 'Club Brugge' in r['target_teams'] for r in rows))
metrics=json.loads((ROOT/'pipeline/models/model_store/candidates/ucl_europe_reviewed_20261020/metrics_v2.1.0.json').read_text())
check('candidate_model_unchanged',hashlib.sha256((ROOT/'pipeline/models/model_store/candidates/ucl_europe_reviewed_20261020/model_v2.1.0.pkl').read_bytes()).hexdigest()==metrics['model_sha256'])
manifest={p.name:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in [RAW/'all_results.csv',RAW/'all_results.json',RAW/'regulation_history.csv',RAW/'coverage.json']}
verification={'verified_at':datetime.now(timezone.utc).isoformat(),'checks':checks,'checks_passed':sum(checks.values()),'artifacts':manifest}
(OUT/'ucl-history-verification-20261021.json').write_text(json.dumps(verification,indent=2),encoding='utf-8')
lines=['# UCL history backfill — 21 October 2026','',f"Collected {report['new_unique_fixtures']:,} additional unique fixtures. The reconciled export contains **{len(rows):,} unique fixtures**, with **{len(training):,} eligible regulation-time results** across all 18 clubs. Fixtures involving two target clubs count once in the combined export and once for each club in the team table.",'',
'Scope: 2023/24, 2024/25, 2025/26 and current 2026/27; Viking uses calendar seasons 2023–2026. Results stop before 21 October 2026 UTC, so tonight’s outcomes cannot leak into history. Senior competitive matches only; exhibitions are excluded.','',
f"**Remaining qualification:** {report['unresolved_regulation']} records are retained outside the training CSV, including awarded matches and extra-time/penalty results whose 90-minute score was not independently established. A shootout score is stored separately from match goals. Coverage matches all {report['tm_inventory_fixtures']:,} dated completed fixtures parsed from the reviewed season inventories; this is not a claim that every provider is exhaustive.",'',
'| Team | Previous results in scope | Results now | Newly found | Eligible 90-minute results | Season counts, oldest first | Latest five |','|---|---:|---:|---:|---:|---|---|']
for c in report['coverage']:
    lines.append(f"| {c['team']} | {c['baseline_results']} | {c['results']} | {c['new_results']} | {c['training_results']} | {' / '.join(map(str,c['season_counts'].values()))} | {c['last_five']} |")
lines+=['','## Corrections and validation','',
'- Expanded Brugge, LASK and Shakhtar from sparse European-only records to domestic league and cup history. Retrieved Como’s Serie B season, European qualifiers, domestic cups and supercups where covered.',
'- Rejected wrong provider identities (Sporting/Santos and Brugge/Batang) before final export. All retained ESPN team identities and Transfermarkt page titles were checked against reviewed club aliases/native IDs.',
'- Galatasaray–Adana Demirspor on 9 February 2025 and Galatasaray–Fenerbahçe on 7 April 2024 were awarded results. They remain in the historical record with training disabled.',
'- Viking’s 1 October 2026 cup win at Madla and Brugge’s 17 October result are present. Villa’s available recent sequence is now WWDWW and Brugge’s is WWWWW; this supersedes the narrower sequences in the earlier betting review.',
f"- {len(checks)} end-to-end checks passed: checksums, 18 club exports, all four seasons, score/status eligibility, duplicate removal, inventory reconciliation, causal cutoff and unchanged candidate model. No unresolved score conflicts remain.",
'- Additional football-data.co.uk CSV requests timed out; existing archived CSVs, ESPN, Transfermarkt and Terrikon supplied the usable histories. No denied ESPN API access was bypassed.',
'',
'## Artifacts','',
'- [All competitive results CSV](../../../pipeline/data/raw/ucl_history_20261021/all_results.csv)',
'- [Regulation history CSV](../../../pipeline/data/raw/ucl_history_20261021/regulation_history.csv)',
'- [Per-team CSV folder](../../../pipeline/data/raw/ucl_history_20261021/teams/)',
'- [Coverage and source manifest](../../../pipeline/data/raw/ucl_history_20261021/coverage.json)',
'- [Verification](ucl-history-verification-20261021.json)',
'- `all_results.json` retains the individual source observations supporting each accepted fixture.',
'',
'No database or active-model writes were made. The earlier probabilities and EV estimates have not been recalculated on this expanded history and should not be represented as updated forecasts.','',
'Sources: [ESPN public results](https://www.espn.com/soccer/team/results/_/id/132/season/2023/league/all), [Transfermarkt season schedules](https://www.transfermarkt.com/club-brugge-kv/spielplan/verein/2282/saison_id/2023), [Terrikon archives](https://terrikon.com/en/football/teams/1376/gamesarchive), [Viking official results](https://www.vikingfotball.no/resultater), [RSSSF Norway cup archive](https://www.rsssf.no/archive.html), [Galatasaray’s abandonment record](https://www.galatasaray.org/haber/futbol/galatasaray-adana-demirspor-maci-tatil-edildi/57198).','']
(OUT/'ucl-history-backfill-20261021.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({'checks_passed':sum(checks.values()),'unique_fixtures':len(rows),'new_unique_fixtures':report['new_unique_fixtures'],'regulation_results':len(training),'withheld_from_training':report['unresolved_regulation'],'report':str(OUT/'ucl-history-backfill-20261021.md')}))
