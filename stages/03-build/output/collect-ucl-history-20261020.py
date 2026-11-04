"""Capture auditable senior results, preserving raw sources and exclusions."""
import hashlib
import io
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from lxml import html

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline'))
sys.stdout.reconfigure(encoding='utf-8')
from etl.scrapling_transport import ScraplingTransport

OUT = ROOT / 'pipeline/data/raw/ucl_history_20261020'
OUT.mkdir(parents=True, exist_ok=True)
START = pd.Timestamp('2023-01-01', tz='UTC')
CUTOFF = pd.Timestamp('2026-10-20', tz='UTC')
TEAMS = ['Fenerbahce', 'Slavia Praha', 'Sabah FC', 'Borussia D', 'AS Roma',
         'Slovan B', 'Porto', 'PSV Eindhoven', 'Liverpool', 'Villarreal',
         'Man City', 'AEK', 'PSG', 'Barcelona', 'Napoli', 'Bodø/Glimt',
         'VfB Stuttgart', 'Atletico']
transport = None
manifest = []


def capture(name: str, url: str) -> bytes | None:
    global transport
    path = OUT / (name + '.raw')
    try:
        if path.exists():
            content = path.read_bytes()
            status = 200
        else:
            if transport is None:
                transport = ScraplingTransport()
            response = transport.get(url, timeout=25)
            status, content = response.status_code, response.content
            if status == 200:
                path.write_bytes(content)
            time.sleep(1.2)
        entry = dict(name=name, url=url, status=status, bytes=len(content))
        if status == 200:
            entry.update(sha256=hashlib.sha256(content).hexdigest(),
                         captured_at=datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat())
        manifest.append(entry)
        return content if status == 200 else None
    except Exception as exc:
        manifest.append(dict(name=name, url=url, error=type(exc).__name__))
        return None
    finally:
        (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')


def parse_archive(content: bytes, url: str) -> tuple[list, list]:
    tree = html.fromstring(content)
    rows, excluded = [], []
    for tr in tree.xpath('//tr[td[contains(concat(" ",normalize-space(@class)," ")," leftteam ")]]'):
        def field(cls: str) -> str:
            cells = tr.xpath('./td[contains(concat(" ",normalize-space(@class)," ")," ' + cls + ' ")]')
            return ' '.join(cells[0].text_content().split()) if cells else ''
        d, home, away, score, comp = [field(c) for c in ['date', 'leftteam', 'rightteam', 'score', 'abr']]
        date = pd.to_datetime(d, format='%d.%m.%Y', utc=True, errors='coerce')
        if pd.isna(date) or not START <= date < CUTOFF:
            continue
        match = re.fullmatch(r'(\d+):(\d+)', score)
        if not match:
            if score and score != '-:-':
                excluded.append(dict(date=d, home=home, away=away, score=score, reason='non-simple score / possible extra-time or penalties'))
            continue
        link = tr.xpath('./td[contains(@class,"score")]//a/@href')
        rows.append(dict(date=date.isoformat(), home_team=home, away_team=away,
                         home_score=int(match[1]), away_score=int(match[2]),
                         competition=comp, data_source='terrikon:senior-archive',
                         source_url='https://terrikon.com' + link[0] if link else url,
                         archive_url=url, status='FINISHED',
                         score_basis='archive_simple_score_unverified_regulation'))
    return rows, excluded


def main() -> None:
    body = capture('terrikon_cl', 'https://terrikon.com/en/champions-league')
    if body is None:
        raise RuntimeError('Team identity source unavailable')
    tree = html.fromstring(body)
    identities = {}
    for a in tree.xpath('//a[@href]'):
        name = ' '.join(a.text_content().split())
        m = re.fullmatch(r'/en/football/teams/(\d+)', a.get('href'))
        if name in TEAMS and m:
            identities[name] = m[1]
    missing = set(TEAMS) - set(identities)
    if missing:
        raise ValueError('Unresolved team IDs: ' + repr(sorted(missing)))
    (OUT / 'team_ids.json').write_text(json.dumps(identities, indent=2, ensure_ascii=False), encoding='utf-8')
    archives, exclusions, coverage = [], [], []
    for name, tid in identities.items():
        url = f'https://terrikon.com/en/football/teams/{tid}/gamesarchive'
        content = capture('team_' + tid, url)
        if content:
            rows, skipped = parse_archive(content, url)
            archives.extend(rows)
            exclusions.extend(skipped)
            coverage.append(dict(team=name, provider_id=tid, rows=len(rows),
                                 earliest=min((r['date'] for r in rows), default=None),
                                 latest=max((r['date'] for r in rows), default=None)))
            print(json.dumps(coverage[-1], ensure_ascii=False), flush=True)
    pd.DataFrame(archives).drop_duplicates(['date', 'home_team', 'away_team']).to_csv(OUT / 'archives.csv', index=False)
    (OUT / 'archive_exclusions.json').write_text(json.dumps(exclusions, indent=2), encoding='utf-8')
    (OUT / 'coverage.json').write_text(json.dumps(coverage, indent=2, ensure_ascii=False), encoding='utf-8')
    frames = []
    for season in ['2324', '2425', '2526', '2627']:
        for league in ['E0', 'D1', 'I1', 'SP1', 'F1', 'P1', 'N1', 'T1', 'G1']:
            content = capture(f'fd_{season}_{league}', f'https://football-data.co.uk/mmz4281/{season}/{league}.csv')
            if not content:
                continue
            try:
                frame = pd.read_csv(io.BytesIO(content), encoding='utf-8-sig').copy()
                required = {'Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG'}
                if not required.issubset(frame):
                    raise ValueError('Missing result columns')
                frame['date'] = pd.to_datetime(frame['Date'], dayfirst=True, utc=True, errors='coerce')
                frame = frame[frame.date.ge(START) & frame.date.lt(CUTOFF)].copy()
                frame = frame[frame.FTHG.notna() & frame.FTAG.notna()].copy()
                frame['data_source'] = 'football-data.co.uk:verified-csv'
                frame['competition'] = league
                frame['source_url'] = f'https://www.football-data.co.uk/mmz4281/{season}/{league}.csv'
                frame['score_basis'] = 'domestic_league_regulation'
                frames.append(frame)
                print(json.dumps(dict(season=season, league=league, rows=len(frame))), flush=True)
            except (ValueError, pd.errors.ParserError) as exc:
                manifest[-1]['parse_error'] = str(exc)
    for country in ['NOR', 'CZE', 'SVK', 'AZE']:
        url = f'https://football-data.co.uk/new/{country}.csv'
        content = capture('fd_new_' + country, url)
        if not content:
            continue
        try:
            frame = pd.read_csv(io.BytesIO(content), encoding='utf-8-sig')
            frame = frame.rename(columns={'Home': 'HomeTeam', 'Away': 'AwayTeam', 'HG': 'FTHG', 'AG': 'FTAG', 'Res': 'FTR'})
            if not {'Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG'}.issubset(frame):
                raise ValueError('Missing result columns')
            frame['date'] = pd.to_datetime(frame.Date, dayfirst=True, utc=True, errors='coerce')
            frame = frame[frame.date.ge(START) & frame.date.lt(CUTOFF) & frame.FTHG.notna() & frame.FTAG.notna()].copy()
            frame['data_source'] = 'football-data.co.uk:verified-csv'
            frame['competition'] = country
            frame['source_url'] = url
            frame['score_basis'] = 'domestic_league_regulation'
            frames.append(frame)
            print(json.dumps(dict(country=country, rows=len(frame))), flush=True)
        except (ValueError, pd.errors.ParserError) as exc:
            manifest[-1]['parse_error'] = str(exc)
    if not frames:
        raise RuntimeError('No validated league results captured')
    combined = pd.concat(frames, ignore_index=True)
    combined.to_csv(OUT / 'league_results.csv', index=False)
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(dict(archive_rows=len(archives), league_rows=len(combined), teams=len(coverage), output=str(OUT))), flush=True)


if __name__ == '__main__':
    main()
