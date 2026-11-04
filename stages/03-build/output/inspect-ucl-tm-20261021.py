from pathlib import Path
from lxml import html
import json
ROOT=Path(__file__).resolve().parents[3];RAW=ROOT/'pipeline/data/raw/ucl_history_20261021'
t=html.fromstring((RAW/'lask_transfermarkt_current.raw').read_bytes())
print('TITLE',t.xpath('//title/text()'));print('CANON',t.xpath('//link[@rel="canonical"]/@href'))
print('TABLES',[(x.attrib,len(x.xpath('.//tr'))) for x in t.xpath('//table')])
for row in [r for r in t.xpath('//tr[.//a[contains(@href,"spielbericht")]]') if len(r.xpath('./td')) in [9,10,11,12]][:2]:print('MATCHROW',html.tostring(row,encoding='unicode')[:9000])
for table in t.xpath('//table[contains(@class,"items")]'):
    print('HEADER',table.xpath('preceding::h2[1]//text()'));print('HEAD',table.xpath('.//thead//text()'))
    rows=table.xpath('.//tbody/tr[td]')
    for row in rows[:1]:print(html.tostring(row,encoding='unicode')[:7000])
for year in [2022,2023,2024,2025,2026]:
    tree=html.fromstring((RAW/f'norway_cup_{year}.raw').read_bytes())
    lines=tree.text_content().splitlines();print('NORCUP',year)
    for i,l in enumerate(lines):
        if 'Viking' in l:print(lines[max(0,i-2):i+1])
for path in RAW.glob('rsssf_*.raw'):
    t=html.fromstring(path.read_bytes());print('RSSSF',path.name,t.xpath('//title/text()'),len(t.text_content()))
