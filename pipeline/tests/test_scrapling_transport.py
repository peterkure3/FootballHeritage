"""Transport changes preserve evidence and honor site crawl restrictions."""
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import requests

from etl.scrapling_transport import RobotsDisallowed, ScraplingTransport
from etl.scrape_sportsbooks import get_public_source


def page(body=b'{"data":[]}', status=200):
    return SimpleNamespace(body=body, status=status, url='https://example.org/events',
                           headers={'content-type': 'application/json'}, encoding='utf-8')


class ScraplingTransportTests(unittest.TestCase):
    def transport(self):
        client = ScraplingTransport.__new__(ScraplingTransport)
        client.fetcher = Mock()
        client._robots = {}
        client._origin_locks = {}
        client._lock = threading.Lock()
        return client

    def test_raw_bytes_status_headers_and_timeout_are_preserved(self):
        client = self.transport()
        client.fetcher.get.side_effect = [page(b'User-agent: *\nAllow: /'), page(b'[]', 206)]
        response = client.get('https://example.org/events', timeout=(5, 15))
        self.assertEqual(response.content, b'[]')
        self.assertEqual(response.status_code, 206)
        self.assertEqual(response.headers['Content-Type'], 'application/json')
        self.assertEqual(response.json(), [])
        self.assertEqual(client.fetcher.get.call_args.kwargs['timeout'], 20)
        self.assertEqual(client.fetcher.get.call_args.kwargs['retries'], 1)

    def test_disallowed_source_is_never_requested(self):
        client = self.transport()
        client.fetcher.get.return_value = page(b'User-agent: *\nDisallow: /events')
        with self.assertRaises(RobotsDisallowed):
            client.get('https://example.org/events')
        client.fetcher.get.assert_called_once()

    def test_unknown_policy_is_not_assumed_to_allow_scraping(self):
        client = self.transport()
        client.fetcher.get.return_value = page(b'', 503)
        with self.assertRaises(RobotsDisallowed):
            client.get('https://example.org/events')

    def test_missing_policy_allows_public_reads_and_is_cached_per_origin(self):
        client = self.transport()
        client.fetcher.get.side_effect = [page(b'', 404), page(), page()]
        client.get('https://example.org/events')
        client.get('https://example.org/other')
        self.assertEqual(client.fetcher.get.call_count, 3)

    def test_post_json_and_transport_errors(self):
        client = self.transport()
        client.fetcher.get.return_value = page(b'', 404)
        client.fetcher.post.return_value = page()
        client.post('https://example.org/events', json={'Sport': 'soccer'})
        self.assertEqual(client.fetcher.post.call_args.kwargs['json'], {'Sport': 'soccer'})
        client.fetcher.post.side_effect = RuntimeError('network failure')
        with self.assertRaises(requests.ConnectionError):
            client.post('https://example.org/events')

    def test_collector_records_robot_restriction(self):
        with TemporaryDirectory() as temporary:
            http = Mock()
            http.get.side_effect = RobotsDisallowed()
            report = get_public_source('bookmaker', 'https://example.org/events', Path(temporary), http=http)
        self.assertEqual(report['status'], 'robots_disallowed')
        self.assertEqual(report['snapshots'], 0)


if __name__ == '__main__':
    unittest.main()
