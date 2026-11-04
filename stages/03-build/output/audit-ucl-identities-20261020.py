import json
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[3]
duplicate_path=ROOT/'pipeline/data/raw/ucl_history_20261020/unresolved_identity_duplicates.csv'
if duplicate_path.exists():
    duplicates=pd.read_csv(duplicate_path,low_memory=False)
    groups=[]
    for _,g in duplicates.groupby('fixture_day'):
        groups.append({'home_names':sorted(set(g.home_team)),'away_names':sorted(set(g.away_team))})
    print(json.dumps(list({json.dumps(g,ensure_ascii=True):g for g in groups}.values()),ensure_ascii=True))
    sys_exit=True
    raise SystemExit(0)
df=pd.read_parquet(ROOT/'pipeline/data/raw/ucl_history_20261020/repaired_dataset.parquet')
targets={'barcelona','villarreal','ath madrid','roma','napoli','dortmund','stuttgart','paris sg','porto','psv','aek','liverpool','manchester city'}
pairs={}
for side,other in [('home','away'),('away','home')]:
    sub=df[df[side+'_key'].isin(targets)]
    for key,g in sub.groupby(['fixture_day',side+'_key']):
        if len(g)>1:
            names=tuple(sorted(set(g[other+'_team'])))
            if len(names)>1:
                pairs[names]=pairs.get(names,0)+1
print(json.dumps([{'names':n,'overlap_days':count} for n,count in sorted(pairs.items(),key=lambda kv:-kv[1])],ensure_ascii=True))
