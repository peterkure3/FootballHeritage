"""Live API smoke checks; save summaries without dumping fixtures or credentials."""
import json
from pathlib import Path
import requests

base='http://127.0.0.1:5567/api/v1'
response=requests.get(base+'/betting-intel',timeout=20)
response.raise_for_status()
overview=response.json()
assert len(overview['sports'])==6
results=[]
for entry in overview['sports']:
    response=requests.get(base+'/betting-intel/'+entry['sport'],timeout=20)
    response.raise_for_status()
    data=response.json()
    assert data['sport']==entry['sport']
    for prediction in data['predictions']:
        assert abs(sum(prediction['probabilities'].values())-1)<1e-6
        assert prediction['sport']==entry['sport']
    for arb in data['arbitrage']:
        assert not arb['execution_verified']
        assert abs(sum(leg['reference_stake'] for leg in arb['legs'])-100)<1e-8
    results.append({'sport':entry['sport'],'summary':data['summary'],'snapshot_status':data['snapshot_status']})
assert requests.get(base+'/betting-intel/not-a-sport',timeout=10).status_code==404
schema=requests.get('http://127.0.0.1:5567/openapi.json',timeout=20).json()
assert '/api/v1/betting-intel/{sport}' in schema['paths']
output={'snapshot_at':overview['snapshot_at'],'checks':'overview, six sport endpoints, probability sums, arbitrage allocation, 404 and OpenAPI passed','sports':results}
Path(__file__).with_name('betting-intel-live-20261020.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
print(json.dumps(output,indent=2))
