"""Session management for EasyScrape.

Provides persistent session handling with connection pooling,
cookie management, and proxy rotation.

Example
-------
    from easyscrape import Session

    with Session() as session:
        result = session.get("https://example.com")
        print(result.css("h1"))
"""
from __future__ import annotations

import random
import time
from typing import Any, Final, Literal
from urllib.parse import urlparse

import httpx

from .config import Config
from .core import ScrapeResult
from .exceptions import NetworkError, RequestTimeout
from .extractors import Extractor
from .validate import validate_url

__all__: Final[tuple[str, ...]] = (
    "Session",
    "AsyncSession",
    "ProxyPool",
)


class ProxyPool:
    """Pool of proxies with rotation strategies.

    Parameters
    ----------
    proxies : list[str]
        List of proxy URLs.
    strategy : str
        Rotation strategy: 'round-robin', 'random', or 'sticky'.

    Example
    -------
        pool = ProxyPool(["http://proxy1:8080", "http://proxy2:8080"])
        proxy = pool.get()
    """

    def __init__(
        self,
        proxies: list[str],
        strategy: Literal["round-robin", "random", "sticky"] = "round-robin",
    ) -> None:
        self._proxies = list(proxies)
        self._strategy = strategy
        self._index = 0
        self._bad_proxies: set[str] = set()
        # For sticky strategy, store the selected proxy
        self._sticky_proxy: str | None = None

    def get(self) -> str | None:
        """Get the next proxy based on strategy.

        Returns
        -------
        str or None
            Proxy URL, or None if no proxies available.
        """
        available = [p for p in self._proxies if p not in self._bad_proxies]
        if not available:
            # Fall back to all proxies if all marked bad
            available = self._proxies
        if not available:
            return None

        if self._strategy == "sticky":
            # Return the same proxy every time
            if self._sticky_proxy is None or self._sticky_proxy not in available:
                self._sticky_proxy = available[0]
            return self._sticky_proxy
        elif self._strategy == "random":
            return random.choice(available)
        else:  # round-robin
            # Ensure index is within bounds
            self._index = self._index % len(available)
            proxy = available[self._index]
            self._index = (self._index + 1) % len(available)
            return proxy

    def mark_bad(self, proxy: str) -> None:
        """Mark a proxy as bad/non-working."""
        self._bad_proxies.add(proxy)
        # If sticky proxy is marked bad, clear it
        if self._sticky_proxy == proxy:
            self._sticky_proxy = None

    def mark_good(self, proxy: str) -> None:
        """Mark a proxy as good/working."""
        self._bad_proxies.discard(proxy)


class Session:
    """HTTP session with connection pooling and cookie persistence.

    Parameters
    ----------
    config : Config, optional
        Configuration options.

    Example
    -------
        with Session() as session:
            r1 = session.get("https://example.com/page1")
            r2 = session.get("https://example.com/page2")
    """

    def __init__(self, config: Config | None = None) -> None:
        self._config = config or Config()
        self._client: httpx.Client | None = None
        self._request_count = 0
        self._proxy_pool: ProxyPool | None = None
        self._closed = False

        # Initialize proxy pool if proxies configured
        if self._config.proxies:
            self._proxy_pool = ProxyPool(self._config.proxies)

    def __enter__(self) -> Session:
        self._ensure_client()
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _ensure_client(self) -> None:
        """Ensure HTTP client is initialized."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=self._config.timeout,
                follow_redirects=True,
                verify=self._config.verify_ssl,
            )

    def _make_headers(self) -> dict[str, str]:
        """Build request headers."""
        headers = dict(self._config.headers)
        if "User-Agent" not in headers:
            if self._config.rotate_ua:
                from .user_agents import random_ua
                headers["User-Agent"] = random_ua()
            else:
                headers["User-Agent"] = (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
        return headers

    def _pick_proxy(self) -> str | None:
        """Pick a proxy from the pool.

        Returns
        -------
        str or None
            Proxy URL or None.
        """
        if self._proxy_pool is None:
            return None
        return self._proxy_pool.get()

    @property
    def request_count(self) -> int:
        """Number of requests made in this session."""
        return self._request_count

    def get(self, url: str, **kwargs: Any) -> ScrapeResult:
        """Send a GET request.

        Parameters
        ----------
        url : str
            URL to fetch.
        **kwargs
            Additional arguments passed to httpx.

        Returns
        -------
        ScrapeResult
            The response result.
        """
        self._ensure_client()
        assert self._client is not None

        # Validate URL
        validated_url = validate_url(
            url,
            allow_localhost=self._config.allow_localhost,
        )

        headers = self._make_headers()
        headers.update(kwargs.pop("headers", {}))

        start_time = time.perf_counter()

        try:
            response = self._client.get(validated_url, headers=headers, **kwargs)
            self._request_count += 1

            request_time = time.perf_counter() - start_time

            return ScrapeResult(
                text=response.text,
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                url=str(response.url),
                request_time=request_time,
            )

        except httpx.TimeoutException as e:
            raise RequestTimeout(
                f"Request to {url} timed out",
                timeout=self._config.timeout,
                cause=e,
            )
        except httpx.ConnectError as e:
            raise NetworkError(f"Connection failed: {e}", cause=e)

    def post(
        self,
        url: str,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> ScrapeResult:
        """Send a POST request.

        Parameters
        ----------
        url : str
            URL to post to.
        data : dict, optional
            Form data.
        json : dict, optional
            JSON data.
        **kwargs
            Additional arguments.

        Returns
        -------
        ScrapeResult
            The response result.
        """
        self._ensure_client()
        assert self._client is not None

        validated_url = validate_url(
            url,
            allow_localhost=self._config.allow_localhost,
        )

        headers = self._make_headers()
        headers.update(kwargs.pop("headers", {}))

        start_time = time.perf_counter()

        try:
            response = self._client.post(
                validated_url,
                headers=headers,
                data=data,
                json=json,
                **kwargs,
            )
            self._request_count += 1

            request_time = time.perf_counter() - start_time

            return ScrapeResult(
                text=response.text,
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                url=str(response.url),
                request_time=request_time,
            )

        except httpx.TimeoutException as e:
            raise RequestTimeout(
                f"Request to {url} timed out",
                timeout=self._config.timeout,
                cause=e,
            )
        except httpx.ConnectError as e:
            raise NetworkError(f"Connection failed: {e}", cause=e)

    def put(
        self,
        url: str,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> ScrapeResult:
        """Send a PUT request."""
        self._ensure_client()
        assert self._client is not None

        validated_url = validate_url(
            url,
            allow_localhost=self._config.allow_localhost,
        )

        headers = self._make_headers()
        headers.update(kwargs.pop("headers", {}))

        start_time = time.perf_counter()

        try:
            response = self._client.put(
                validated_url,
                headers=headers,
                data=data,
                json=json,
                **kwargs,
            )
            self._request_count += 1

            request_time = time.perf_counter() - start_time

            return ScrapeResult(
                text=response.text,
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                url=str(response.url),
                request_time=request_time,
            )

        except httpx.TimeoutException as e:
            raise RequestTimeout(
                f"Request to {url} timed out",
                timeout=self._config.timeout,
                cause=e,
            )
        except httpx.ConnectError as e:
            raise NetworkError(f"Connection failed: {e}", cause=e)

    def delete(self, url: str, **kwargs: Any) -> ScrapeResult:
        """Send a DELETE request."""
        self._ensure_client()
        assert self._client is not None

        validated_url = validate_url(
            url,
            allow_localhost=self._config.allow_localhost,
        )

        headers = self._make_headers()
        headers.update(kwargs.pop("headers", {}))

        start_time = time.perf_counter()

        try:
            response = self._client.delete(
                validated_url,
                headers=headers,
                **kwargs,
            )
            self._request_count += 1

            request_time = time.perf_counter() - start_time

            return ScrapeResult(
                text=response.text,
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                url=str(response.url),
                request_time=request_time,
            )

        except httpx.TimeoutException as e:
            raise RequestTimeout(
                f"Request to {url} timed out",
                timeout=self._config.timeout,
                cause=e,
            )
        except httpx.ConnectError as e:
            raise NetworkError(f"Connection failed: {e}", cause=e)

    def close(self) -> None:
        """Close the session and release resources."""
        if self._client is not None and not self._closed:
            self._client.close()
            self._closed = True


class AsyncSession:
    """Async HTTP session with connection pooling.

    Parameters
    ----------
    config : Config, optional
        Configuration options.

    Example
    -------
        async with AsyncSession() as session:
            result = await session.get("https://example.com")
    """

    def __init__(self, config: Config | None = None) -> None:
        self._config = config or Config()
        self._client: httpx.AsyncClient | None = None
        self._request_count = 0
        self._proxy_pool: ProxyPool | None = None
        self._closed = False

        if self._config.proxies:
            self._proxy_pool = ProxyPool(self._config.proxies)

    async def __aenter__(self) -> AsyncSession:
        await self._ensure_client()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def _ensure_client(self) -> None:
        """Ensure async HTTP client is initialized."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._config.timeout,
                follow_redirects=True,
                verify=self._config.verify_ssl,
            )

    def _make_headers(self) -> dict[str, str]:
        """Build request headers."""
        headers = dict(self._config.headers)
        if "User-Agent" not in headers:
            if self._config.rotate_ua:
                from .user_agents import random_ua
                headers["User-Agent"] = random_ua()
            else:
                headers["User-Agent"] = (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
        return headers

    @property
    def request_count(self) -> int:
        """Number of requests made in this session."""
        return self._request_count

    async def get(self, url: str, **kwargs: Any) -> ScrapeResult:
        """Send an async GET request.

        Parameters
        ----------
        url : str
            URL to fetch.
        **kwargs
            Additional arguments.

        Returns
        -------
        ScrapeResult
            The response result.
        """
        await self._ensure_client()
        assert self._client is not None

        validated_url = validate_url(
            url,
            allow_localhost=self._config.allow_localhost,
        )

        headers = self._make_headers()
        headers.update(kwargs.pop("headers", {}))

        start_time = time.perf_counter()

        try:
            response = await self._client.get(
                validated_url,
                headers=headers,
                **kwargs,
            )
            self._request_count += 1

            request_time = time.perf_counter() - start_time

            return ScrapeResult(
                text=response.text,
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                url=str(response.url),
                request_time=request_time,
            )

        except httpx.TimeoutException as e:
            raise RequestTimeout(
                f"Request to {url} timed out",
                timeout=self._config.timeout,
                cause=e,
            )
        except httpx.ConnectError as e:
            raise NetworkError(f"Connection failed: {e}", cause=e)

    async def post(
        self,
        url: str,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> ScrapeResult:
        """Send an async POST request."""
        await self._ensure_client()
        assert self._client is not None

        validated_url = validate_url(
            url,
            allow_localhost=self._config.allow_localhost,
        )

        headers = self._make_headers()
        headers.update(kwargs.pop("headers", {}))

        start_time = time.perf_counter()

        try:
            response = await self._client.post(
                validated_url,
                headers=headers,
                data=data,
                json=json,
                **kwargs,
            )
            self._request_count += 1

            request_time = time.perf_counter() - start_time

            return ScrapeResult(
                text=response.text,
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                url=str(response.url),
                request_time=request_time,
            )

        except httpx.TimeoutException as e:
            raise RequestTimeout(
                f"Request to {url} timed out",
                timeout=self._config.timeout,
                cause=e,
            )
        except httpx.ConnectError as e:
            raise NetworkError(f"Connection failed: {e}", cause=e)

    async def close(self) -> None:
        """Close the async session."""
        if self._client is not None and not self._closed:
            await self._client.aclose()
            self._closed = True
