"""Inspect the final inputs before rendering the prediction report."""
import json
from pathlib import Path
import pandas as pd
from lxml import html

ROOT=Path(__file__).resolve().parents[3]
RAW=ROOT/'pipeline/data/raw/ucl_nextweek_20261030'
tree=html.fromstring((RAW/'domestic/slovan.html').read_text(encoding='utf-8'))
for tr in tree.xpath('//tr'):
    text=' '.join(tr.text_content().split())
    if 'Oct 28' in text and len(text)<1000:
        print('SLOVAN_ROW',json.dumps(html.tostring(tr,encoding='unicode')))
for encoding in [None,'utf-8']:
    p=RAW/'domestic/slovan.html'
    tree=html.fromstring(p.read_bytes() if encoding is None else p.read_text(encoding=encoding))
    rows=[]
    for tr in tree.xpath('//tr[contains(@class,"zapasy")]'):
        cells=tr.xpath('./td')
        left=tr.xpath('./td[contains(@class,"aright")]')
        right=tr.xpath('./td[contains(@class,"aleft")]')
        score=tr.xpath('.//div[@class="score"]')
        if left and right and score:
            rows.append([cells[0].text_content(),left[0].text_content(),right[0].text_content(),score[0].text_content()])
    print('ENCODING',encoding,json.dumps(rows[:8]))
d=pd.read_parquet(ROOT/'pipeline/models/model_store/candidates/ucl_nextweek_20261030_reviewed/dataset.parquet')
print('SLOVAN_NAMES',json.dumps(sorted(set(n for n in list(d.home_team)+list(d.away_team) if 'slovan' in n))))
report=json.loads(Path(__file__).with_name('ucl-nextweek-predictions-20261030.json').read_text())
for key in ['classifier_validation','goal_model_validation']:
    print(key,json.dumps({s:{z:y for z,y in report[key][s].items() if z in ['samples','accuracy','log_loss']} for s in ['test','champions_league_test','champions_league_prior','champions_league_baseline'] if s in report[key]}))
for row in report['matches']:
    print(json.dumps({'home':row['home'],'away':row['away'],'form':{t:{'sequence':f['sequence'],'last':f['matches'][-1] if f['matches'] else None} for t,f in row['form'].items()}}))
