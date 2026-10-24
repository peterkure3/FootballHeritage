"""Exercise interpreter fallback with stubs; never invoke database scripts."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class PythonLauncherTests(unittest.TestCase):
    def probe(self, available):
        helper = Path('scripts/find_python.bat').resolve()
        with tempfile.TemporaryDirectory(prefix='python launcher ') as directory:
            folder = Path(directory)
            for name, status in available.items():
                (folder / f'{name}.cmd').write_text(
                    f'@echo off\nexit /b {status}\n', encoding='ascii')
            runner = folder / 'probe.bat'
            runner.write_text(
                f'@echo off\ncall "{helper}"\n'
                'if errorlevel 1 exit /b 1\necho SELECTED=%FH_PYTHON%\n',
                encoding='ascii')
            environment = os.environ.copy()
            environment['PATH'] = directory
            environment['PATHEXT'] = '.COM;.EXE;.BAT;.CMD'
            return subprocess.run([os.environ['COMSPEC'], '/d', '/c', str(runner)],
                                  env=environment, text=True, capture_output=True)

    def test_prefers_py_launcher(self):
        result = self.probe({'py': 0, 'python': 0, 'python3': 0})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('SELECTED=py -3', result.stdout)

    def test_python_without_launcher(self):
        result = self.probe({'python': 0})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('SELECTED=python\n', result.stdout)

    def test_store_alias_failure_falls_back(self):
        result = self.probe({'py': 1, 'python': 9009, 'python3': 0})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('SELECTED=python3', result.stdout)

    def test_missing_interpreters(self):
        result = self.probe({})
        self.assertEqual(result.returncode, 1)
        self.assertIn('No working Python 3', result.stdout)
        self.assertNotIn('SELECTED=', result.stdout)

    def test_all_aliases_fail(self):
        result = self.probe({'py': 1, 'python': 9009, 'python3': 9009})
        self.assertEqual(result.returncode, 1)
        self.assertIn('App execution aliases', result.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
