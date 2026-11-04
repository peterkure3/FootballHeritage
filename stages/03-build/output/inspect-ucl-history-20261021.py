from pathlib import Path
from lxml import html
import json,re,collections
root=Path(__file__).resolve().parents[3]/'pipeline/data/raw'
t=html.fromstring((root/'ucl_history_20261021/espn_bayern_html.raw').read_bytes())
print('TABLE ROW',[(tr.text_content()[:400],tr.xpath('.//a/@href')) for tr in t.xpath('//tr')[:6]])
for s in t.xpath('//script'):
    txt=s.text or ''
    if '__espnfitt__' in txt:
        print('STATEPREFIX',txt[:100]);m=re.search(r'window\["__espnfitt__"\]\s*=\s*',txt)
        if not m:m=re.search(r"window\['__espnfitt__'\]\s*=\s*",txt)
        if m:
            obj,end=json.JSONDecoder().raw_decode(txt[m.end():]);print('STATEKEYS',list(obj));
            (root/'ucl_history_20261021/espn_bayern_state.json').write_text(json.dumps(obj),encoding='utf-8')
            def walk(o,path=''):
                if isinstance(o,dict):
                    if 'events' in o:print('EVENTPATH',path,type(o['events']).__name__,str(o['events'])[:1800])
                    for k,v in o.items():walk(v,path+'/'+k)
                elif isinstance(o,list):
                    for i,v in enumerate(o[:2]):walk(v,path+'/'+str(i))
            walk(obj)
v=html.fromstring((root/'ucl_history_20261021/viking_official.raw').read_bytes())
print('VIKINGFIRSTROWS',[(tr.attrib,tr.text_content()[:800],tr.xpath('.//td/@class')) for tr in v.xpath('//tr[td]')[:2]])
print('VIKING LINKS',v.xpath('//a[contains(@href,"resultater")]/@href'))
for path in (root/'ucl_today_20261021_form').glob('team*.raw'):
    t=html.fromstring(path.read_bytes());dates=t.xpath('//td[@class="date"]/text()');comps=t.xpath('//td[@class="abr"]/text()')
    print(path.name,len(dates),dates[-1] if dates else None,dict(collections.Counter(comps)))
