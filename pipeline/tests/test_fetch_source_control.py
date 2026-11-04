import unittest
from unittest.mock import patch

from etl import fetch_raw_data as fetch


class FetchSourceTests(unittest.TestCase):
    def test_football_only_does_not_call_paid_odds(self):
        with patch('sys.argv', ['fetch', '--source', 'football']), patch.object(fetch, 'fetch_football_data_org', return_value=True), patch.object(fetch, 'fetch_the_odds_api') as odds:
            fetch.main()
            odds.assert_not_called()

    def test_official_source_failure_exits_nonzero(self):
        with patch('sys.argv', ['fetch', '--source', 'football']), patch.object(fetch, 'fetch_football_data_org', return_value=False):
            with self.assertRaises(SystemExit) as error:
                fetch.main()
            self.assertEqual(error.exception.code, 1)

    def test_swallowed_provider_errors_are_counted(self):
        with patch.object(fetch, 'FootballDataOrgFetcher') as factory, patch.object(fetch, 'TRACKED_COMPETITIONS', ['PL']), patch.object(fetch, 'save_json'), patch.object(fetch.time, 'sleep'):
            factory.return_value.fetch_matches.side_effect = ValueError('offline fixture')
            self.assertFalse(fetch.fetch_football_data_org())


if __name__ == '__main__':
    unittest.main()
