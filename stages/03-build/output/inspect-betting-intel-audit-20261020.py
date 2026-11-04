import json
from pathlib import Path
path=Path(__file__).with_name('betting-intel-fallow-20261020.json')
data=json.loads(path.read_text(encoding='utf-8-sig'))
print(json.dumps({'summary':data.get('summary'),'verdict':data.get('verdict'),'keys':list(data)}))
def walk(value):
    if isinstance(value,dict):
        path=str(value.get('path',value.get('file','')))
        if 'BettingIntel' in path or 'betting-intel' in path:
            print(json.dumps(value)[:2200])
        for child in value.values(): walk(child)
    elif isinstance(value,list):
        for child in value: walk(child)
walk(data)
