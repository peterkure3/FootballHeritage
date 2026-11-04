import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import run_pipeline as runner


class AutomationTests(unittest.TestCase):
    def test_failed_dependency_blocks_consumer_but_not_independent_work(self):
        steps = [runner.Step('fetch', 'unused'),
                 runner.Step('load', 'unused', needs=('fetch',)),
                 runner.Step('settle', 'unused')]
        def execute(step, directory, python):
            return {'name': step.name, 'status': 'failed' if step.name == 'fetch' else 'succeeded'}
        with tempfile.TemporaryDirectory() as tmp, patch.object(runner, 'plan', return_value=steps), patch.object(runner, 'execute', side_effect=execute) as calls:
            self.assertEqual(runner.run('daily', Path(tmp), Path(sys.executable)), 1)
            report = json.loads((Path(tmp) / 'latest-daily.json').read_text())
            self.assertEqual([r['status'] for r in report['steps']], ['failed', 'blocked', 'succeeded'])
            self.assertEqual(calls.call_count, 2)

    def test_weekly_never_publishes_or_activates_candidates(self):
        steps = runner.plan('weekly', Path('unused'))
        self.assertTrue(all('--publish' not in step.args for step in steps))
        self.assertFalse(any('activate' in step.module for step in steps))

    def test_paid_odds_failure_does_not_block_official_transform(self):
        steps = {s.name: s for s in runner.plan('daily', Path('unused'))}
        self.assertNotIn('football_odds', steps['transform'].needs)
        self.assertIn('football_fetch', steps['transform'].needs)
        self.assertIn('predictions', steps['backend_sync'].needs)

    def test_public_only_excludes_paid_jobs(self):
        names = {s.name for s in runner.plan('daily', Path('unused'), public_only=True)}
        self.assertFalse(names & {'football_odds', 'nba_fetch', 'ncaab_fetch'})
        self.assertTrue({'football_fetch', 'form', 'regional', 'backend_sync'} <= names)

    def test_real_child_is_terminated_at_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            step = runner.Step('sleep', 'timeit', ('-n', '1', '-r', '1', '__import__("time").sleep(30)'), timeout=1)
            result = runner.execute(step, Path(tmp), Path(sys.executable))
            self.assertEqual(result['status'], 'timeout')
            self.assertLess(result['seconds'], 15)

    def test_lock_contends_and_releases(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'pipeline.lock'
            code = ('from pathlib import Path; from scripts.run_pipeline import pipeline_lock; '
                    f'lock=pipeline_lock(Path({str(path)!r})); lock.__enter__()')
            with runner.pipeline_lock(path):
                child = subprocess.run([sys.executable, '-c', code], cwd=runner.BASE, capture_output=True)
                self.assertNotEqual(child.returncode, 0)
            with runner.pipeline_lock(path):
                pass

    def test_child_timeout_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = unittest.mock.Mock()
            fake.wait.side_effect = [subprocess.TimeoutExpired('test', 1), 0]
            with patch.object(runner.subprocess, 'Popen', return_value=fake), patch.object(runner, 'stop_tree') as stop:
                result = runner.execute(runner.Step('timeout', 'unused', timeout=1), Path(tmp), Path(sys.executable))
            stop.assert_called_once_with(fake)
            self.assertEqual(result['status'], 'timeout')

    def test_actual_child_exit_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = runner.execute(runner.Step('missing', 'definitely_missing_fh_module'), Path(tmp), Path(sys.executable))
            self.assertEqual(result['status'], 'failed')
            self.assertNotEqual(result['exit_code'], 0)
            self.assertIn('No module named', (Path(tmp) / 'missing.log').read_text())

    def test_interruption_writes_failure_report(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(runner, 'execute', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                runner.run('report', Path(tmp), Path(sys.executable))
            report = json.loads((Path(tmp) / 'latest-report.json').read_text())
            self.assertEqual(report['status'], 'interrupted')


if __name__ == '__main__':
    unittest.main()
