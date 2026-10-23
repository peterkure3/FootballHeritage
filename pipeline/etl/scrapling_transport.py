"""Scrapling HTTP transport for the existing verified sportsbook parsers."""
import threading
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import requests

USER_AGENT = 'FootballHeritage public-odds collector/1.0'


class RobotsDisallowed(requests.RequestException):
    """The public source's crawl policy does not permit this request."""


class ScraplingTransport:
    """Keep response bytes and metadata while enforcing per-origin crawl policy."""

    def __init__(self) -> None:
        from scrapling.fetchers import Fetcher
        self.fetcher = Fetcher
        self._robots = {}
        self._origin_locks = {}
        self._lock = threading.Lock()

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        timeout = kwargs.pop('timeout', 20)
        if isinstance(timeout, tuple):
            timeout = sum(timeout)
        try:
            page = getattr(self.fetcher, method)(url, timeout=timeout, retries=1,
                follow_redirects='safe', impersonate='chrome', **kwargs)
        except Exception as exc:
            raise requests.ConnectionError(f'Scrapling request failed: {type(exc).__name__}') from exc
        response = requests.Response()
        response.status_code = page.status
        response._content = page.body
        response.url = page.url
        response.headers.update(page.headers)
        response.encoding = page.encoding or 'utf-8'
        return response

    def _check_robots(self, url: str) -> None:
        parsed = urlsplit(url)
        origin = f'{parsed.scheme}://{parsed.netloc}'
        with self._lock:
            origin_lock = self._origin_locks.setdefault(origin, threading.Lock())
        with origin_lock:
            if origin not in self._robots:
                response = self._request('get', origin + '/robots.txt',
                    headers={'User-Agent': USER_AGENT}, timeout=15)
                parser = RobotFileParser()
                if response.status_code == 200:
                    parser.parse(response.text.splitlines())
                elif response.status_code in {404, 410}:
                    parser.parse([])
                else:
                    # Preserve unknown or denied policy; don't assume permission.
                    raise RobotsDisallowed(f'Cannot verify robots policy for {origin}')
                self._robots[origin] = parser
            parser = self._robots[origin]
        if not parser.can_fetch(USER_AGENT, url):
            raise RobotsDisallowed(f'robots.txt disallows {url}')

    def get(self, url: str, **kwargs) -> requests.Response:
        self._check_robots(url)
        return self._request('get', url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        self._check_robots(url)
        return self._request('post', url, **kwargs)
