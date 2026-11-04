"""Inventory historical output scripts without importing or executing them."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def route(name: str) -> str:
    if name in {'export-market-refresh-20261103.py', 'generate-market-picks-20261031.py'}:
        return 'Recurring market report: scripts.export_market_report'
    if name.startswith(('collect-nba-', 'fetch-nba-archive', 'import-tomorrow-scrapling')):
        return 'Recurring verified collection: scripts.refresh_regional_pipeline; archive research remains opt-in'
    if name.startswith(('collect-missing-form', 'collect-ucl-form', 'collect-ucl-nextweek', 'collect-ucl-missing-history')):
        return 'Recurring supported official form: etl.fetch_football_form; dated source-specific supplements retained'
    if name.startswith(('train-nba', 'finalize-league-models', 'sync-league-fixtures')):
        return 'Candidate/forecast modules: models.train_sports, models.train_football_leagues, models.predict_football_leagues'
    if name.startswith(('simulate-weekend', 'render-soccer-simulation', 'report-ucl', 'predict-ucl', 'run-ucl-model')):
        return 'Opt-in current analysis: scripts.analyze_soccer_markets and scripts.report_soccer_markets; match-specific logic archived'
    if name.startswith(('refresh-outcomes', 'audit-paper')):
        return 'Recurring paper-result processing: scripts.refresh_regional_pipeline and scripts.assess_paper_trial'
    return 'Historical investigation/repair or source-specific experiment; retained, never scheduled automatically'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'pipeline/docs/OUTPUT_SCRIPT_INVENTORY.md')
    args = parser.parse_args()
    sources = sorted(path for path in (ROOT / 'stages').glob('*/output/*.py'))
    lines = ['# Output script inventory', '',
             'Generated without importing or running source files. Paths and hashes identify the historical evidence.',
             'Routing identifies a maintained replacement workflow or an explicit opt-in/archive disposition;',
             'it does not claim every bespoke analysis or external data adapter was copied into production.', '',
             f'{len(sources)} top-level output scripts inventoried. See UNATTENDED_PIPELINE.md for executable commands.', '',
             '| Source | SHA-256 | Disposition |', '|---|---|---|']
    for path in sources:
        lines.append(f'| `{path.relative_to(ROOT).as_posix()}` | `{hashlib.sha256(path.read_bytes()).hexdigest()}` | {route(path.name)} |')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'{len(sources)} scripts catalogued: {args.output}')


if __name__ == '__main__':
    main()
