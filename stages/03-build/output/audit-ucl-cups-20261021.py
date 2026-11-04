from pathlib import Path
from lxml import html
import json,collections,re
RAW=Path(__file__).resolve().parents[3]/'pipeline/data/raw/ucl_history_20261021'
for tid in [228,239,141,413]:
    tree=html.fromstring((RAW/f'tm_{tid}_2023.raw').read_bytes());print('TEAM',tid,tree.xpath('//title/text()'))
    for table in tree.xpath('//table'):
        rs=table.xpath('.//tr[.//a[contains(@class,"ergebnis-link")]]')
        if not rs:continue
        heading=table.xpath('preceding::h2[1]');print('COMP',' '.join(heading[0].text_content().split()) if heading else '?','ROWS',len(rs))
        r=rs[0];print('EXAMPLE',[' '.join(td.text_content().split()) for td in r.xpath('./td')]);print('LINKS',r.xpath('.//a/@href')[-3:])
r=json.loads((RAW/'all_results.json').read_text());print('UNKNOWN',collections.Counter((x['data_source'],x.get('status_detail'),x['competition']) for x in r if not x['training_eligible']))
print('VIKINGFORM',next(x for x in json.loads((RAW/'coverage.json').read_text())['coverage'] if x['team']=='Viking')['last_five_matches'])
