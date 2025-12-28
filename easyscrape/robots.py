"""Robots.txt parsing and caching.

This module provides functionality for fetching, parsing, and caching
robots.txt files to respect website crawling rules.

Example
-------
    from easyscrape.robots import RobotsCache

    cache = RobotsCache()
    if cache.is_allowed("https://example.com/page"):
        # Safe to scrape
        pass
"""
from __future__ import annotations

import time
from threading import Lock
from typing import Final
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from .exceptions import RobotsBlocked

__all__: Final[tuple[str, ...]] = (
    "RobotsCache",
    "get_robots_cache",
)


class RobotsCache:
    """Cache for robots.txt parsers.

    Fetches and caches robots.txt files to avoid repeated requests.
    Thread-safe for concurrent access.

    Parameters
    ----------
    ttl : int
        Cache time-to-live in seconds.
    max_size : int
        Maximum number of cached parsers.
    user_agent : str
        User agent to use for robots.txt checks.
    """

    def __init__(
        self,
        ttl: int = 86400,
        max_size: int = 1000,
        user_agent: str = "EasyScrape",
    ) -> None:
        self._ttl = ttl
        self._max_size = max_size
        self._user_agent = user_agent
        self._cache: dict[str, tuple[RobotFileParser, float]] = {}
        self._lock = Lock()

    def _base_url(self, url: str) -> str:
        """Extract base URL (scheme + host)."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def _robots_url(self, url: str) -> str:
        """Construct robots.txt URL."""
        base = self._base_url(url)
        return f"{base}/robots.txt"

    def get_parser(self, url: str) -> RobotFileParser:
        """Get or create a robots.txt parser for a URL.

        Parameters
        ----------
        url : str
            URL to get parser for.

        Returns
        -------
        RobotFileParser
            The parser for the URL's domain.
        """
        base = self._base_url(url)
        now = time.time()

        with self._lock:
            if base in self._cache:
                parser, expires = self._cache[base]
                if now < expires:
                    return parser

        # Fetch robots.txt
        robots_url = self._robots_url(url)
        parser = RobotFileParser()
        parser.set_url(robots_url)

        try:
            response = httpx.get(robots_url, timeout=10.0, follow_redirects=True)
            if response.status_code == 200:
                parser.parse(response.text.splitlines())
            else:
                # No robots.txt or error - allow everything
                parser.parse([])
        except Exception:
            # Error fetching - allow everything
            parser.parse([])

        # Cache the parser
        with self._lock:
            # Evict if at capacity
            if len(self._cache) >= self._max_size:
                # Remove oldest entry
                oldest = min(self._cache.items(), key=lambda x: x[1][1])
                del self._cache[oldest[0]]
            self._cache[base] = (parser, now + self._ttl)

        return parser

    def is_allowed(self, url: str, user_agent: str | None = None) -> bool:
        """Check if a URL is allowed by robots.txt.

        Parameters
        ----------
        url : str
            URL to check.
        user_agent : str, optional
            User agent to check for. Defaults to instance user_agent.

        Returns
        -------
        bool
            True if allowed, False if disallowed.
        """
        parser = self.get_parser(url)
        ua = user_agent or self._user_agent
        return parser.can_fetch(ua, url)

    def check_or_raise(self, url: str, user_agent: str | None = None) -> None:
        """Check if URL is allowed, raise RobotsBlocked if not.

        Parameters
        ----------
        url : str
            URL to check.
        user_agent : str, optional
            User agent to check for.

        Raises
        ------
        RobotsBlocked
            If the URL is blocked by robots.txt.
        """
        if not self.is_allowed(url, user_agent):
            raise RobotsBlocked(f"URL blocked by robots.txt: {url}", url=url)

    def crawl_delay(self, url: str, user_agent: str | None = None) -> float | None:
        """Get the crawl delay for a URL.

        Parameters
        ----------
        url : str
            URL to check.
        user_agent : str, optional
            User agent to check for.

        Returns
        -------
        float or None
            Crawl delay in seconds, or None if not specified.
        """
        parser = self.get_parser(url)
        ua = user_agent or self._user_agent
        delay = parser.crawl_delay(ua)
        return float(delay) if delay is not None else None

    def clear(self) -> None:
        """Clear the cache."""
        with self._lock:
            self._cache.clear()


# Singleton instance
_default_cache: RobotsCache | None = None
_default_lock = Lock()


def get_robots_cache(ttl: int = 86400) -> RobotsCache:
    """Get the default robots cache singleton.

    Parameters
    ----------
    ttl : int
        Cache TTL (only used on first call).

    Returns
    -------
    RobotsCache
        The default cache instance.
    """
    global _default_cache
    with _default_lock:
        if _default_cache is None:
            _default_cache = RobotsCache(ttl=ttl)
        return _default_cache
