"""Normalize verified domestic league scores from captured official club pages."""
import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin
import pandas as pd
from lxml import html

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / 'pipeline/data/raw/ucl_history_20261020'
sys.stdout.reconfigure(encoding='utf-8')


def slovan_results(content: bytes) -> list[dict]:
    tree = html.fromstring(content.decode('utf-8'))
    records = []
    for tr in tree.xpath('//tr[contains(@class,"zapasy")]'):
        link = tr.xpath('./td[contains(@class,"score")]//a/@href')
        if not link:
            continue
        season = re.search(r'league=NL-(\d{4})\d{2}', link[0])
        if not season:
            continue
        cells = tr.xpath('./td')
        dm = re.search(r'(\d{1,2})\.(\d{1,2})\.', cells[0].text_content())
        score = ' '.join(tr.xpath('./td[contains(@class,"score")]')[0].text_content().split())
        match = re.fullmatch(r'(\d+)\s*:\s*(\d+)', score)
        if not dm or not match:
            continue
        day, month = map(int, dm.groups())
        year = int(season[1]) + (month < 7)
        date = pd.Timestamp(year=year,month=month,day=day,tz='UTC')
        if not pd.Timestamp('2023-07-01',tz='UTC') <= date < pd.Timestamp('2026-10-20',tz='UTC'):
            continue
        def team(cls: str) -> str:
            name = ' '.join(tr.xpath('./td[contains(@class,"'+cls+'")]')[0].text_content().split())
            return 'Slovan Bratislava' if name == 'ŠK Slovan' else name
        records.append(dict(date=date.isoformat(),home_team=team('aright'),away_team=team('aleft'),
                            home_score=int(match[1]),away_score=int(match[2]),competition='SVK',
                            data_source='skslovan.com:official-league',status='FINISHED',
                            source_url=urljoin('https://www.skslovan.com/zapasy/',link[0]),score_basis='domestic_league_regulation'))
    return records


def glimt_results(content: bytes) -> list[dict]:
    tree = html.fromstring(content.decode('utf-8'))
    records = []
    for tr in tree.xpath('//tr[contains(@class,"schedule__match--played")]'):
        leagues = tr.xpath('.//td[contains(@class,"--league")]//img/@alt')
        if 'Eliteserien' not in leagues:
            continue
        dt = ' '.join(tr.xpath('.//td[contains(@class,"--date")]')[0].text_content().split())
        match_date = re.search(r'\d{2}\.\d{2}\.\d{4}',dt)
        if not match_date:
            continue
        date = pd.to_datetime(match_date[0],format='%d.%m.%Y',utc=True)
        score = ' '.join(tr.xpath('.//td[contains(@class,"--result")]')[0].text_content().split())
        m = re.fullmatch(r'(\d+)-(\d+)',score)
        if not m or date >= pd.Timestamp('2026-10-20',tz='UTC'):
            continue
        cell = tr.xpath('.//td[contains(@class,"--teams")]')[0]
        for unwanted in cell.xpath('.//span[contains(@class,"team-form") or contains(@class,"__score")]'):
            unwanted.drop_tree()
        names = ' '.join(cell.text_content().split()).split(' - ')
        if len(names) != 2:
            raise ValueError('Ambiguous official team orientation')
        records.append(dict(date=date.isoformat(),home_team=names[0],away_team=names[1],home_score=int(m[1]),away_score=int(m[2]),
                            competition='NOR',data_source='glimt.no:official-league',status='FINISHED',source_url='https://www.glimt.no/resultater',score_basis='domestic_league_regulation'))
    return records


if __name__ == '__main__':
    rows = []
    for path in sorted(RAW.glob('slovan_202*.html')):
        parsed = slovan_results(path.read_bytes())
        rows.extend(parsed)
        print(json.dumps({'source':path.name,'rows':len(parsed)}),flush=True)
    rows.extend(glimt_results((RAW/'probe/glimt.txt').read_bytes()))
    df = pd.DataFrame(rows).drop_duplicates(['date','home_team','away_team'])
    df.to_csv(RAW/'official_results.csv',index=False)
    print(json.dumps({'official_rows':len(df),'by_source':df.groupby('data_source').size().to_dict()}),flush=True)
