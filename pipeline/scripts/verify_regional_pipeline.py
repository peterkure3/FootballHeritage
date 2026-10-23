"""Check real API quotes, pregame provenance and immutable trial evidence."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

import pandas as pd
import requests


def verify(base):
    day = datetime.now(timezone.utc).date().isoformat()
    with requests.Session() as client:
        response = client.get(base+'/api/v1/prediction-dashboard/fixtures', params={
            'competition':'Premier League','match_date':day,'page_size':50},timeout=30)
        assert response.status_code == 200, response.text
        feed = response.json()
        expected = {'bovada','betpawa:UG','fortebet:UG','ababet:UG','sportpesa:GLOBAL'}
        for fixture in feed['items']:
            assert fixture['prediction']['status'] == 'current'
            assert set(fixture['prediction']['probabilities']) == {'home_win','draw','away_win'}
            assert abs(sum(fixture['prediction']['probabilities'].values())-1) < 1e-6
            assert expected <= {quote['bookmaker'] for quote in fixture['market']['quotes']}
            assert pd.Timestamp(fixture['prediction']['generated_at']) < pd.Timestamp(fixture['kickoff'])
            assert all(pd.Timestamp(quote['observed_at']) < pd.Timestamp(fixture['kickoff'])
                       for quote in fixture['market']['quotes'] if quote['fresh'])
        response = client.get(base+'/api/v1/prediction-dashboard/paper-trials',timeout=30)
        assert response.status_code == 200, response.text
        paper = response.json()
        assert paper['profitable_edge_established'] is False
        for trial in paper['trials']:
            if trial['settled_selections'] == 0:
                assert trial['roi'] is None and trial['stressed_roi'] is None
    target = Path(__file__).resolve().parents[2]/'stages/03-build/output'/f'regional-pipeline-live-verification-{day.replace("-", "")}.json'
    target.write_text(json.dumps({'checked_at':datetime.now(timezone.utc).isoformat(),
        'fixtures':feed,'paper_trials':paper},indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps({'upcoming_epl':len(feed['items']),'books_per_fixture':len(expected),
        'trials':len(paper['trials']),'report':str(target)},indent=2))


def main():
    base = 'http://127.0.0.1:5565'
    process = subprocess.Popen([sys.executable,'-m','uvicorn','api.main:app',
        '--host','127.0.0.1','--port','5565'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            if process.poll() is not None:
                raise RuntimeError('Isolated verification API exited before startup')
            try:
                if requests.get(base+'/api/v1/prediction-dashboard/paper-trials',timeout=1).ok:
                    break
            except requests.RequestException:
                pass
            time.sleep(.5)
        else:
            raise RuntimeError('Verification API startup timed out')
        verify(base)
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == '__main__':
    main()
