"""Assess eligible frozen studies once; persist the cohort before computing intervals."""
import json
from models.paper_trial import TRIAL_ROOT, settle
from models.trial_study import studies, assess_once, eligible_cohort
from models.paper_trial import result_key
from pathlib import Path
import hashlib


def verify_result_sources(entries: list[dict]) -> None:
    captures = {}
    for entry in entries:
        source = entry['settlement']['result_source']
        path = Path(source['raw_capture_ref'])
        if str(path) not in captures:
            payload = path.read_bytes()
            if hashlib.sha256(payload).hexdigest() != source['source_sha256']:
                raise ValueError('Official result capture checksum mismatch')
            captures[str(path)] = json.loads(payload)
        matches = [m for m in captures[str(path)]['matches'] if str(m['id']) == str(source['provider_event_id'])]
        if len(matches) != 1:
            raise ValueError('Official result ID is absent or ambiguous')
        match = matches[0]
        score = match['score']['fullTime']
        if (match['status'] != 'FINISHED' or match['score']['duration'] != 'REGULAR'
                or score['home'] != source['home_score'] or score['away'] != source['away_score']
                or result_key(match['homeTeam']['name'], match['awayTeam']['name'], match['utcDate']) != tuple(entry['fixture_key'])):
            raise ValueError('Settlement disagrees with captured official result')


def run(root: Path = TRIAL_ROOT) -> list[dict]:
    batches = []
    for path in root.glob('*/trial.json'):
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != path.parent.name:
            raise ValueError('Trial checksum mismatch')
        trial = json.loads(payload)
        receipts = sorted(path.parent.glob('settlement_*.json'))
        results = []
        if receipts:
            receipt = json.loads(receipts[-1].read_text(encoding='utf-8'))
            if receipt.get('trial_sha256') != path.parent.name:
                raise ValueError('Settlement belongs to another trial')
            results = [r['result_source'] for r in receipt['fixtures'] if r.get('result_source')]
        batches.append({'trial': trial, 'receipt': settle(trial, results), 'trial_sha256': path.parent.name})
    output = []
    for study in studies(batches):
        if study['assessment_ready']:
            verify_result_sources(eligible_cohort([e for e in study['entries'] if e['forecast'].get('selected_outcome')]))
        assessment = assess_once(study, root)
        output.append({'study_id': study['study_id'], 'settled_selections': study['settled_selections'],
            'fixture_days': study['fixture_days'], 'assessment': assessment,
            'assessment_status': assessment['status'] if assessment else study['assessment_status']})
    return output


if __name__ == '__main__':
    print(json.dumps(run(), indent=2, allow_nan=False))
