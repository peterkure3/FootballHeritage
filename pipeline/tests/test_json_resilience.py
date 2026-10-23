"""Corrupt telemetry must not stop settlement; training evidence stays strict."""
import io
import json
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import requests

from etl.utils import load_json, load_status_json, save_json, setup_logger
from models import paper_trial
from models.import_sportsbook_odds import load_imported_odds
from scripts import run_trial_collection as job


class JsonResilienceTests(unittest.TestCase):
    def test_raw_feed_arrays_remain_supported(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / 'feed.json'
            save_json([{'id': 1}], path)
            self.assertEqual(load_json(path), [{'id': 1}])

    def test_failed_serialization_preserves_previous_file_and_cleans_temp(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / 'state.json'
            save_json({'outcome': 'success'}, path)
            original = path.read_bytes()
            with self.assertRaises(TypeError):
                save_json({'unsupported': object()}, path)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(path.parent.iterdir()), [path])

    def test_failed_publication_preserves_previous_file(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / 'state.json'
            save_json({'outcome': 'success'}, path)
            with patch('etl.utils.os.replace', side_effect=OSError('disk error')):
                with self.assertRaises(OSError):
                    save_json({'outcome': 'running'}, path)
            self.assertEqual(json.loads(path.read_bytes()), {'outcome': 'success'})
            self.assertEqual(list(path.parent.iterdir()), [path])

    def test_missing_bom_and_corrupt_status(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / 'state.json'
            self.assertIsNone(load_status_json(path))
            path.write_text('{"outcome": "success"}', encoding='utf-8-sig')
            self.assertEqual(load_status_json(path)['outcome'], 'success')
            for payload in [b'', b'\x00' * 260, b'{', b'[]', b'null', b'\xff']:
                with self.subTest(payload=payload):
                    path.write_bytes(payload)
                    status = load_status_json(path)
                    self.assertEqual(status['outcome'], 'unavailable')
                    self.assertNotIn('last_success_at', status)
                    self.assertEqual(path.read_bytes(), payload)

    def test_dashboard_keeps_serving_trials_with_corrupt_optional_health(self):
        with TemporaryDirectory() as temporary:
            base = Path(temporary)
            (base / 'logs').mkdir()
            (base / 'logs/edge_trial_status.json').write_bytes(b'\x00' * 260)
            with patch.object(paper_trial, 'BASE_DIR', base):
                report = paper_trial.dashboard(base / 'trials')
            self.assertEqual(report['trials'], [])
            self.assertEqual(report['collector']['outcome'], 'unavailable')
            self.assertFalse(report['profitable_edge_established'])

    def test_collector_recovers_corrupt_health_without_skipping_work(self):
        with TemporaryDirectory() as temporary, patch.object(job, 'LOGS', Path(temporary)), \
                patch.object(job, 'execute', return_value=True) as execute:
            path = Path(temporary) / 'edge_trial_status.json'
            path.write_bytes(b'\x00' * 260)
            self.assertEqual(job.main(), 0)
            self.assertEqual(execute.call_count, 3)
            self.assertEqual(json.loads(path.read_bytes())['outcome'], 'success')

    def test_training_never_silently_skips_corrupt_import_manifest(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / 'damaged-import'
            directory.mkdir()
            manifest = directory / 'manifest.json'
            manifest.write_bytes(b'\x00' * 892)
            with self.assertRaisesRegex(ValueError, 'damaged-import.*manifest.json'):
                load_imported_odds(Path(temporary))

    def test_request_credentials_redacted_from_message_and_traceback(self):
        logger = setup_logger('json-resilience-redaction-test')
        output = io.StringIO()
        handler = logging.StreamHandler(output)
        handler.setFormatter(logger.handlers[0].formatter)
        logger.addHandler(handler)
        try:
            try:
                raise requests.HTTPError('401 Unauthorized: https://example.test?apiKey=test-secret&regions=eu')
            except requests.HTTPError as exc:
                logger.error('Fetch failed: %s', exc, exc_info=True)
            record = json.loads(output.getvalue())
            self.assertIn('401 Unauthorized', record['message'])
            self.assertNotIn('test-secret', output.getvalue())
            self.assertIn('[REDACTED]', record['exception'])
        finally:
            logger.removeHandler(handler)


if __name__ == '__main__':
    unittest.main()
