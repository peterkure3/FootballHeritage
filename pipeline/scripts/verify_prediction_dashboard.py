"""Exercise the real dashboard API and independent sport previews, then stop it."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

import requests


def main():
    root = Path(__file__).resolve().parents[1]
    process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'api.main:app', '--host', '127.0.0.1', '--port', '5563'], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = 'http://127.0.0.1:5563/api/v1'
    report = {'verified_at': datetime.now(timezone.utc).isoformat(), 'responses': {}}
    try:
        for _ in range(60):
            if process.poll() is not None:
                raise RuntimeError('Isolated API failed to start')
            try:
                if requests.get(base + '/sport-models', timeout=1).status_code == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(.5)
        else:
            raise RuntimeError('API startup timed out')
        endpoints = ['/prediction-dashboard/fixtures', '/prediction-dashboard/fixtures?page=2',
            '/prediction-dashboard/fixtures?competition=NotARealLeague', '/predictions/accuracy-data?days=30',
            '/predictions/history-data?page_size=5&result_filter=correct', '/predictions/versions',
            '/predictions/accuracy-data?start_date=2026-09-10&end_date=2026-09-20&league=Premier%20League',
            '/predictions/history-data?page_size=5&start_date=2026-09-10&end_date=2026-09-20&league=Premier%20League']
        for endpoint in endpoints:
            response = requests.get(base + endpoint, timeout=30)
            assert response.status_code == 200, (endpoint, response.status_code, response.text)
            report['responses'][endpoint] = response.json()
        feed = report['responses'][endpoints[0]]
        assert len(feed['items']) <= 6 and feed['total_count'] >= len(feed['items'])
        assert all(item['kickoff'].endswith('+00:00') for item in feed['items'])
        assert [item['kickoff'] for item in feed['items']] == sorted(item['kickoff'] for item in feed['items'])
        assert not set(item['match_id'] for item in feed['items']) & set(item['match_id'] for item in report['responses'][endpoints[1]]['items'])
        assert report['responses'][endpoints[2]]['total_count'] == 0
        history = report['responses'][endpoints[4]]
        assert history['total_count'] == history['correct_count'] and all(row['is_correct'] for row in history['predictions'])
        assert report['responses'][endpoints[6]]['total_predictions'] == report['responses'][endpoints[7]]['total_count']
        runs = requests.get(base + '/sport-models', timeout=10).json()['runs']
        cases = [('basketball', 'basketball_nba', 'Boston Celtics', 'Los Angeles Lakers'),
            ('wnba', 'basketball_wnba', 'New York Liberty', 'Las Vegas Aces'),
            ('ncaab', 'basketball_ncaab', 'Duke Blue Devils', 'North Carolina Tar Heels'),
            ('ncaabw', 'basketball_wncaab', 'South Carolina Gamecocks', 'Iowa Hawkeyes'),
            ('nfl', 'americanfootball_nfl', 'Kansas City Chiefs', 'Buffalo Bills'),
            ('ncaaf', 'americanfootball_ncaaf', 'Alabama', 'Georgia'), ('football', None, 'Arsenal', 'Chelsea')]
        for sport, league, home, away in cases:
            candidate = next(run['candidate_id'] for run in runs if run['sports'].get(sport, {}).get('status') == 'candidate')
            response = requests.post(base + '/sport-models/preview', json={'candidate_id': candidate, 'sport': sport, 'league': league, 'home_team': home, 'away_team': away, 'kickoff': (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()}, timeout=45)
            assert response.status_code == 200, (sport, response.status_code, response.text)
            result = response.json()
            assert not result['active'] and abs(sum(result['probabilities'].values()) - 1) < .00001
            report['responses'][f'preview:{sport}'] = result
        target = root.parent / 'stages/03-build/output/predictions-ui-live-verification-20261009.json'
        target.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps({'report': str(target), 'checks': len(report['responses']), 'upcoming': feed['total_count'], 'metrics': report['responses'][endpoints[3]]['overall_accuracy'], 'eligible': report['responses'][endpoints[3]]['total_predictions']}), flush=True)
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == '__main__':
    main()
