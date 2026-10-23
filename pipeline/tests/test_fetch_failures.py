"""Provider failures differ from successful empty responses and reach batch jobs."""
from unittest import TestCase, main
from unittest.mock import MagicMock, patch

import requests

from etl import fetch_raw_data as raw
from etl import fetch_nba_data_wrapper as nba
from etl import fetch_ncaab_odds as ncaab


class FetchFailureTests(TestCase):
    def test_unauthorized_provider_stops_remaining_sports_and_scores(self):
        response = requests.Response()
        response.status_code = 401
        error = requests.HTTPError('401 Unauthorized', response=response)
        with patch.object(raw, 'TheOddsApiFetcher') as fetcher, \
                patch.object(raw, 'ODDS_API_SPORTS', ['soccer_epl', 'basketball_nba']):
            fetcher.return_value.fetch_odds.side_effect = error
            self.assertFalse(raw.fetch_the_odds_api())
            self.assertEqual(fetcher.return_value.fetch_odds.call_count, 1)
            fetcher.return_value.fetch_scores.assert_not_called()

    def test_raw_main_exits_nonzero_on_provider_failure(self):
        with patch('sys.argv', ['fetch_raw_data']), \
                patch.object(raw, 'fetch_football_data_org'), \
                patch.object(raw, 'fetch_the_odds_api', return_value=False):
            with self.assertRaises(SystemExit) as result:
                raw.main()
            self.assertEqual(result.exception.code, 1)

    def test_nba_failure_and_empty_success_are_distinct(self):
        with patch.object(nba, 'THE_ODDS_API_KEY', 'test-key'), \
                patch.object(nba, 'NbaOddsFetcher') as fetcher:
            fetcher.return_value.fetch_nba_odds.return_value = None
            fetcher.return_value.fetch_nba_scores.return_value = []
            self.assertEqual(nba.main(), 1)
            fetcher.return_value.fetch_nba_odds.return_value = []
            self.assertEqual(nba.main(), 0)

    def test_ncaab_partial_failure_reaches_cli(self):
        with patch('sys.argv', ['fetch_ncaab_odds']), \
                patch.object(ncaab, 'THE_ODDS_API_KEY', 'test-key'), \
                patch.object(ncaab, 'NcaabOddsFetcher') as fetcher:
            fetcher.return_value.fetch_odds.return_value = None
            fetcher.return_value.fetch_scores.return_value = []
            fetcher.return_value.fetch_events.return_value = []
            with self.assertRaises(SystemExit) as result:
                ncaab.main()
            self.assertEqual(result.exception.code, 1)
            fetcher.return_value.fetch_odds.return_value = []
            ncaab.main()

    def test_ncaab_404_still_means_unavailable_not_failed(self):
        response = requests.Response()
        response.status_code = 404
        session = MagicMock()
        session.get.return_value.raise_for_status.side_effect = requests.HTTPError(response=response)
        with patch.object(ncaab, 'ensure_dir'):
            fetcher = ncaab.NcaabOddsFetcher()
        fetcher.session = session
        self.assertEqual(fetcher.fetch_odds(), [])
        response.status_code = 401
        self.assertIsNone(fetcher.fetch_odds())


if __name__ == '__main__':
    main()
