"""Normalize and quarantine the Wyscout public archive; keep all raw events."""
import argparse
import gzip
import io
import json
import math
import zipfile
from collections import Counter
from itertools import groupby
from pathlib import Path
from typing import Iterator, TextIO

from etl.fetch_soccer_events import DEFAULT_ROOT, file_hash

SCHEMA_VERSION = 1
PERIODS = {'1H': 1, '2H': 2, 'E1': 3, 'E2': 4, 'P': 5}
SHOT_SUBTYPES = {'Free kick shot', 'Penalty'}


def iter_array(handle: TextIO) -> Iterator[dict]:
    """Stream a top-level JSON array without loading a league into memory."""
    decoder, buffer, ended = json.JSONDecoder(), '', False
    started, need_value, after_comma = False, True, False
    while True:
        chunk = handle.read(1024 * 1024)
        ended = not chunk
        buffer += chunk
        position = 0
        while True:
            while position < len(buffer) and buffer[position].isspace():
                position += 1
            if not started:
                if position == len(buffer):
                    break
                if buffer[position] != '[':
                    raise ValueError('Expected JSON array')
                position, started = position + 1, True
                continue
            if position == len(buffer):
                break
            if buffer[position] == ']':
                if after_comma:
                    raise ValueError('Trailing comma')
                if buffer[position + 1:].strip() or handle.read().strip():
                    raise ValueError('Trailing JSON content')
                return
            if not need_value:
                if buffer[position] != ',':
                    raise ValueError('Missing array separator')
                position, need_value, after_comma = position + 1, True, True
                continue
            try:
                item, offset = decoder.raw_decode(buffer, position)
            except json.JSONDecodeError:
                if ended:
                    raise ValueError('Truncated/invalid JSON array') from None
                break
            if not isinstance(item, dict):
                raise ValueError('Expected JSON objects')
            yield item
            position, need_value, after_comma = offset, False, False
        buffer = buffer[position:]
        if ended:
            raise ValueError('Unterminated JSON array')


def is_shot(event: dict) -> bool:
    return event['eventName'] == 'Shot' or event['subEventName'] in SHOT_SUBTYPES


def substitutions(formation: dict) -> list[dict]:
    value = formation.get('substitutions')
    if value is None or value == 'null':
        return []
    if not isinstance(value, list):
        raise ValueError('Unexpected substitution representation')
    return value


def normalize_match(match: dict, events: list[dict], roles: dict) -> dict:
    teams = {int(k): v for k, v in match['teamsData'].items()}
    side = {tid: data['side'] for tid, data in teams.items()}
    roster, starts, ends = {}, {}, {}
    for tid, data in teams.items():
        formation = data['formation']
        for player in formation.get('lineup', []):
            pid = player['playerId']
            roster[pid], starts[pid], ends[pid] = tid, 0, 140
        for player in formation.get('bench', []):
            pid = player['playerId']
            roster[pid], starts[pid], ends[pid] = tid, 140, 140
        for sub in substitutions(formation):
            starts[sub['playerIn']] = sub['minute']
            ends[sub['playerOut']] = sub['minute']
    diagnostics = Counter()
    seen = set()
    score, half_score = Counter(), Counter()
    rows = []
    ordered = sorted(enumerate(events), key=lambda pair: (
        PERIODS.get(pair[1]['matchPeriod'], 99), float(pair[1]['eventSec']), pair[0]))
    for source_order, event in ordered:
        tags = {tag['id'] for tag in event['tags']}
        tid, pid = event['teamId'], event['playerId']
        period, seconds = PERIODS.get(event['matchPeriod'], 99), float(event['eventSec'])
        if event['id'] in seen:
            diagnostics['duplicate_event_id'] += 1
        seen.add(event['id'])
        if tid not in teams:
            diagnostics['unknown_team'] += 1
        if not pid:
            diagnostics['missing_actor'] += 1
        elif roster.get(pid) != tid:
            diagnostics['actor_not_in_team_roster'] += 1
        minute = {1: 0, 2: 45, 3: 90, 4: 105, 5: 120}.get(period, 0) + seconds / 60
        if pid and (minute < starts.get(pid, 0) - 1 or minute > ends.get(pid, 140) + 1):
            diagnostics['actor_outside_interval_tolerance'] += 1
        if period == 99 or not math.isfinite(seconds) or seconds < 0:
            diagnostics['invalid_clock'] += 1
        if any(not math.isfinite(float(v)) or not 0 <= float(v) <= 100
               for point in event['positions'] for v in point.values()):
            diagnostics['invalid_coordinates'] += 1
        shot = is_shot(event)
        goal = shot and 101 in tags
        own_goal = 102 in tags
        scoring_team = (next((t for t in teams if t != tid), None) if own_goal else tid)
        row = dict(event_id=event['id'], source_order=source_order, period=period,
                   seconds=seconds, team_id=tid, player_id=pid, role=roles.get(pid, 'UNK'),
                   kind=event['eventName'], subtype=event['subEventName'],
                   tags=sorted(tags), positions=event['positions'], shot=shot,
                   goal=goal, own_goal=own_goal, accurate=1801 in tags,
                   home_goals_before=score['home'], away_goals_before=score['away'])
        rows.append(row)
        if period <= 2 and (goal or own_goal) and scoring_team in side:
            score[side[scoring_team]] += 1
            if period == 1:
                half_score[side[scoring_team]] += 1
    reasons = [k for k in ['duplicate_event_id', 'unknown_team', 'invalid_clock',
                           'invalid_coordinates', 'actor_not_in_team_roster'] if diagnostics[k]]
    for tid, team in teams.items():
        if score[side[tid]] != team['score']:
            reasons.append(f"{side[tid]}_regulation_score_mismatch")
        if half_score[side[tid]] != team['scoreHT']:
            reasons.append(f"{side[tid]}_halftime_score_mismatch")
    if not all(any(e['period'] == p and e['seconds'] >= 2600 for e in rows) for p in [1, 2]):
        reasons.append('incomplete_regulation_period')
    if match['status'] != 'Played':
        reasons.append('not_played')
    if not all(len(t['formation'].get('lineup', [])) == 11 for t in teams.values()):
        reasons.append('incomplete_starting_lineup')
    return dict(schema_version=SCHEMA_VERSION, match=match, events=rows,
                diagnostics=dict(diagnostics), quarantine=sorted(set(reasons)),
                regulation_score=[score['home'], score['away']])


def build_dataset(raw: Path, output: Path) -> dict:
    manifest = json.loads((raw / 'manifest.json').read_text())
    for name, capture in manifest['captures'].items():
        if file_hash(raw / name) != capture['sha256']:
            raise ValueError(f'Source checksum mismatch: {name}')
    output.mkdir(parents=True, exist_ok=True)
    (output / '.gitignore').write_text('*\n!.gitignore\n', encoding='utf-8')
    players = json.loads((raw / 'players.json').read_text(encoding='utf-8'))
    roles = {p['wyId']: p['role']['code2'] for p in players}
    (output / 'players.json').write_text(json.dumps({p['wyId']: {
        'name': p['shortName'], 'role': p['role']['code2']} for p in players}), encoding='utf-8')
    index, seen_matches = [], set()
    with zipfile.ZipFile(raw / 'matches.zip') as matches_zip:
        matches = {m['wyId']: m for name in matches_zip.namelist()
                   if name.endswith('.json') for m in json.loads(matches_zip.read(name))}
    with zipfile.ZipFile(raw / 'events.zip') as archive:
        for member in archive.namelist():
            if not member.endswith('.json'):
                continue
            competition = Path(member).stem.removeprefix('events_')
            with archive.open(member) as handle:
                stream = iter_array(io.TextIOWrapper(handle, encoding='utf-8'))
                for mid, group in groupby(stream, key=lambda event: event['matchId']):
                    if mid in seen_matches or mid not in matches:
                        raise ValueError('Non-contiguous/duplicate or unknown match ID')
                    seen_matches.add(mid)
                    record = normalize_match(matches[mid], list(group), roles)
                    name = f'{mid}.json.gz'
                    # Serialize once: JSON's tiny streaming writes are expensive
                    # through gzip; each match easily fits in memory.
                    payload = json.dumps(record, separators=(',', ':')).encode('utf-8')
                    (output / name).write_bytes(gzip.compress(payload, compresslevel=1, mtime=0))
                    index.append(dict(match_id=mid, date=matches[mid]['dateutc'],
                                      competition=competition, file=name,
                                      events=len(record['events']),
                                      quarantine=record['quarantine'],
                                      diagnostics=record['diagnostics'],
                                      sha256=file_hash(output / name)))
            print(f'Normalized {competition}: {len(index)} matches so far', flush=True)
    summary = dict(schema_version=SCHEMA_VERSION, source_manifest_sha256=file_hash(raw / 'manifest.json'),
                   source=manifest['citation'], license='CC BY 4.0',
                   transformation='Provider IDs/coordinates retained; events ordered by period/clock/source order',
                   matches=index, missing_event_matches=sorted(matches.keys() - seen_matches),
                   total_events=sum(m['events'] for m in index),
                   competitions=dict(Counter(m['competition'] for m in index)),
                   accepted=sum(not m['quarantine'] for m in index),
                   quarantine_reasons=dict(Counter(r for m in index for r in m['quarantine'])))
    (output / 'index.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in summary.items() if k != 'matches'}, indent=2), flush=True)
    return summary


def load_match(root: Path, item: dict) -> dict:
    path = root / item['file']
    if file_hash(path) != item['sha256']:
        raise ValueError('Normalized match checksum mismatch')
    with gzip.open(path, 'rt', encoding='utf-8') as handle:
        return json.load(handle)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw-dir', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_ROOT / 'normalized')
    args = parser.parse_args()
    build_dataset(args.raw_dir, args.output_dir)


if __name__ == '__main__':
    main()
