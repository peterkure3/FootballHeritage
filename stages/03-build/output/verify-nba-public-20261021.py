"""Independently reproduce captured NBA prices and inspect the live API."""
from collections import Counter
from datetime import datetime,timezone
from decimal import Decimal
import hashlib,json,sys
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline'))
from etl.nba_public_parsers import bovada,cloudbet,betpawa,validate_fixtures

paths=sorted((ROOT/'pipeline/data/raw/nba_public').glob('*/manifest.json'),reverse=True)
path=next(p for p in paths if json.loads(p.read_text(encoding='utf-8')).get('schema_version')==1)
manifest=json.loads(path.read_text(encoding='utf-8'))
assert manifest['validated_moneylines']>0
fixtures=json.loads((path.parent/'validated_fixtures.json').read_text(encoding='utf-8'))
assert hashlib.sha256((path.parent/'validated_fixtures.json').read_bytes()).hexdigest()==manifest['fixtures_sha256']
games=[];parsed=[];failed={row['source'] for row in manifest['source_errors']}
for capture in manifest['captures']:
    raw=path.parent/capture['file']
    assert hashlib.sha256(raw.read_bytes()).hexdigest()==capture['sha256']
    if capture['name']=='balldontlie-games':games.extend(json.loads(raw.read_text())['data'])
    book=capture['name'].removesuffix('-feed')
    if capture['name'].endswith('-feed') and book not in failed:
        parser={'bovada':bovada,'cloudbet':cloudbet,'betpawa':betpawa}[book]
        parsed.extend(parser(json.loads(raw.read_text(encoding='utf-8')),capture['captured_at'],capture['file']))
replayed,rejected=validate_fixtures(parsed,games,datetime.fromisoformat(manifest['completed_at']))
assert replayed==fixtures and len(rejected)==manifest['quarantined_moneylines']

response=requests.get('http://127.0.0.1:5555/api/v1/betting-intel/nba',timeout=30);response.raise_for_status()
api=response.json()
assert not any(e.get('source')=='candidate_catalog' for e in api['source_errors'])
expected={}
for fixture in fixtures:
    for quote in fixture['offers']:
        expected[(fixture['home_team'],fixture['away_team'],fixture['kickoff'],quote['bookmaker'],quote['selection'])]=quote['decimal_odds']
seen={}
for row in api['devigged_odds']:
    assert row['settlement_rule']=='INCLUDING_OVERTIME'
    total=sum(Decimal(1)/Decimal(str(leg['decimal_odds'])) for leg in row['legs'].values())
    for selection,leg in row['legs'].items():
        key=(row['home_team'],row['away_team'],row['kickoff'],row['bookmaker'],selection)
        assert key in expected and abs(expected[key]-leg['decimal_odds'])<1e-12
        p=(Decimal(1)/Decimal(str(leg['decimal_odds'])))/total
        assert abs(float(p)-row['fair_probabilities'][selection])<1e-12
        seen[key]=leg['decimal_odds']
assert expected==seen,'Live prices differ from validated source evidence'
predictions={p['fixture_id']:p for p in api['predictions']}
for row in predictions.values():
    assert row['status']=='candidate_preview' and abs(sum(row['probabilities'].values())-1)<1e-6
    assert row.get('independent_validation') or any(f['home_team']==row['home_team'] and f['away_team']==row['away_team'] and f['kickoff']==row['kickoff'] for f in fixtures)
for row in api['ev_bets']:
    assert row['probability_basis']=='model'
    p=predictions[row['fixture_id']]['probabilities'][row['selection']]
    assert abs(p-row['probability'])<1e-12
    assert abs(p*row['decimal_odds']-1-row['ev_pct'])<1e-12
for arb in api['arbitrage']:
    assert not arb['execution_verified'] and abs(sum(leg['reference_stake'] for leg in arb['legs'])-100)<1e-8
summary={'captured_at':manifest['completed_at'],'capture_dir':str(path.parent),'bookmakers':manifest['bookmakers'],
         'complete_moneyline_pairs':len(fixtures),'independent_games_checked':len(games),
         'checks':'Raw checksums, parser replay, exact independent fixture matches, all live prices, decimal de-vig and model EV arithmetic passed',
         'live_summary':api['summary'],'source_errors':api['source_errors'],'execution_verified':False,
         'sample_prices':[{'home':f['home_team'],'away':f['away_team'],'kickoff':f['kickoff'],
                           'bookmaker':f['offers'][0]['bookmaker'],'prices':{q['selection']:q['decimal_odds'] for q in f['offers']}}
                          for f in fixtures[:2]]}
(ROOT/'stages/03-build/output/nba-public-verification-20261021.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
