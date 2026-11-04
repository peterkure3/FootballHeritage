"""Capture official match pages and public lineup responses without inferring XIs."""
import sys,json,hashlib
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
from lxml import html
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline'))
from etl.scrapling_transport import ScraplingTransport
sys.stdout.reconfigure(encoding='utf-8')
OUT=ROOT/'pipeline/data/raw'/('ucl_lineups_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
OUT.mkdir(parents=True)
fixtures=[(2049598,'bayern-munchen-vs-arsenal'),(2049599,'real-madrid-vs-leipzig'),(2049600,'inter-vs-shakhtar'),(2049601,'sporting-cp-vs-lask'),(2049602,'aston-villa-vs-viking'),(2049603,'club-brugge-vs-lens'),(2049604,'real-betis-vs-feyenoord')]
targets=[]
for match_id,slug in fixtures:
    targets.extend([(str(match_id)+'_page',f'https://www.uefa.com/uefachampionsleague/match/{match_id}--{slug}/lineups/'),(str(match_id)+'_api',f'https://match.uefa.com/v5/matches/{match_id}/lineups'),(str(match_id)+'_pdf',f'https://www.uefa.com/newsfiles/UCL/2027/{match_id}_LU.pdf')])
def fetch(target):
    key,url=target
    try:
        r=ScraplingTransport().get(url,timeout=15)
        row={'key':key,'url':url,'final_url':r.url,'status':r.status_code,'observed_at':datetime.now(timezone.utc).isoformat(),'headers':dict(r.headers),'sha256':hashlib.sha256(r.content).hexdigest(),'bytes':len(r.content)}
        suffix='.pdf' if r.content.startswith(b'%PDF') else '.json' if 'json' in r.headers.get('Content-Type','') else '.html'
        path=OUT/(key+suffix);path.write_bytes(r.content);row['file']=str(path)
        if suffix=='.html':
            tree=html.fromstring(r.content)
            text=' '.join(tree.text_content().split())
            row['text_tail']=text[-600:] if key.endswith('_page') else text[:200]
            row['starting_labels']={s:text.find(s) for s in ['Starting XI','Starting line-ups','Official squad list','lineupStatus','lineups']}
            (OUT/(key+'.txt')).write_text(text,encoding='utf-8')
        elif suffix=='.json':
            data=r.json();row['json_shape']=list(data)[:20] if isinstance(data,dict) else {'type':type(data).__name__,'length':len(data)}
            row['sample']=str(data)[:1800]
    except Exception as e:row={'key':key,'url':url,'error':type(e).__name__,'detail':str(e)[:200]}
    print(json.dumps({k:v for k,v in row.items() if k not in ['headers','text_tail']},ensure_ascii=False),flush=True)
    return row
rows=list(ThreadPoolExecutor(max_workers=5).map(fetch,targets))
(OUT/'audit.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding='utf-8')
(ROOT/'stages/03-build/output/ucl-lineups-inputs-20261021.json').write_text(json.dumps({'capture':str(OUT),'generated_at':datetime.now(timezone.utc).isoformat()},indent=2),encoding='utf-8')
print(json.dumps({'capture':str(OUT)}),flush=True)
