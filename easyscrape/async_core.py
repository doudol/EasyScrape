"""Async scraping functions for EasyScrape.

Provides async versions of core scraping functions for high-performance
concurrent scraping.

Example
-------
    import asyncio
    from easyscrape import async_scrape, async_scrape_many

    async def main():
        result = await async_scrape("https://example.com")
        print(result.css("h1"))

    asyncio.run(main())
"""
from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any, Callable, Final, Sequence
from urllib.parse import urlparse

import httpx

from .config import Config
from .exceptions import (
    HTTPError,
    InvalidURLError,
    NetworkError,
    RequestTimeout,
    RetryExhausted,
)
from .extractors import Extractor
from .validate import validate_url

__all__: Final[tuple[str, ...]] = (
    "async_scrape",
    "async_scrape_many",
    "async_post",
    "async_download_many",
    "AsyncScrapeResult",
)


class AsyncScrapeResult:
    """Result from an async scrape operation.

    Provides the same interface as ScrapeResult but for async operations.

    Parameters
    ----------
    text : str
        The response text/HTML.
    content : bytes
        The raw response content.
    status : int
        HTTP status code.
    headers : dict
        Response headers.
    url : str
        The final URL (after redirects).
    request_time : float
        Time taken for the request in seconds.
    from_cache : bool
        Whether the response was from cache.
    """

    __slots__ = (
        "_text",
        "_content",
        "_status",
        "_headers",
        "_url",
        "_request_time",
        "_from_cache",
        "_extractor",
    )

    def __init__(
        self,
        text: str,
        content: bytes,
        status: int,
        headers: dict[str, str],
        url: str,
        request_time: float,
        from_cache: bool = False,
    ) -> None:
        self._text = text
        self._content = content
        self._status = status
        self._headers = dict(headers)
        self._url = url
        self._request_time = request_time
        self._from_cache = from_cache
        self._extractor: Extractor | None = None

    @property
    def text(self) -> str:
        """Response text/HTML."""
        return self._text

    @property
    def content(self) -> bytes:
        """Raw response content."""
        return self._content

    @property
    def status_code(self) -> int:
        """HTTP status code."""
        return self._status

    @property
    def headers(self) -> dict[str, str]:
        """Response headers."""
        return self._headers

    @property
    def url(self) -> str:
        """Final URL after redirects."""
        return self._url

    @property
    def final_url(self) -> str:
        """Alias for url."""
        return self._url

    @property
    def request_time(self) -> float:
        """Request time in seconds."""
        return self._request_time

    @property
    def from_cache(self) -> bool:
        """Whether response was from cache."""
        return self._from_cache

    @property
    def ok(self) -> bool:
        """True if status code is 2xx."""
        return 200 <= self._status < 300

    @property
    def extractor(self) -> Extractor:
        """Get an Extractor for this response."""
        if self._extractor is None:
            self._extractor = Extractor(self._text, base_url=self._url)
        return self._extractor

    def css(self, selector: str, default: str = "") -> str:
        """Extract text using CSS selector."""
        return self.extractor.css(selector, default)

    def css_list(self, selector: str, attr: str | None = None) -> list[str]:
        """Extract list of texts using CSS selector."""
        return self.extractor.css_list(selector, attr)

    def links(self) -> list[str]:
        """Extract all links from the page."""
        return self.extractor.links()

    def safe_links(self) -> list[str]:
        """Extract safe (http/https) links."""
        return self.extractor.safe_links()

    def images(self) -> list[str]:
        """Extract all image URLs."""
        return self.extractor.images()

    def extract(self, schema: dict[str, str], stype: str = "css") -> dict[str, str]:
        """Extract data using a schema."""
        return self.extractor.extract(schema, stype)

    def extract_all(
        self, container: str, schema: dict[str, str], stype: str = "css"
    ) -> list[dict[str, str]]:
        """Extract multiple items using a container and schema."""
        return self.extractor.extract_all(container, schema, stype)

    def json(self) -> Any:
        """Parse response as JSON."""
        import json
        return json.loads(self._text)

    @property
    def plain_text(self) -> str:
        """Extract plain text from HTML."""
        return self.extractor.plain_text()

    @property
    def cache_headers(self) -> dict[str, str]:
        """Return cache-related headers."""
        cache_keys = {
            "cache-control", "etag", "last-modified", "expires",
            "age", "vary", "pragma",
            "Cache-Control", "ETag", "Last-Modified", "Expires",
            "Age", "Vary", "Pragma",
        }
        return {
            k: v for k, v in self._headers.items()
            if k.lower() in {ck.lower() for ck in cache_keys}
        }

    @property
    def not_modified(self) -> bool:
        """True if response is 304 Not Modified."""
        return self._status == 304


async def async_scrape(
    url: str,
    config: Config | None = None,
) -> AsyncScrapeResult:
    """Async version of scrape().

    Parameters
    ----------
    url : str
        URL to scrape.
    config : Config, optional
        Configuration options.

    Returns
    -------
    AsyncScrapeResult
        The scrape result.

    Raises
    ------
    InvalidURLError
        If URL is invalid or blocked.
    HTTPError
        If request fails with 4xx/5xx status.
    NetworkError
        If network error occurs.
    """
    if config is None:
        config = Config()

    # Validate URL with allow_localhost from config
    validated_url = validate_url(
        url,
        allow_localhost=config.allow_localhost,
    )

    start_time = time.perf_counter()
    max_retries = config.max_retries
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            async with httpx.AsyncClient(
                timeout=config.timeout,
                follow_redirects=True,
                verify=config.verify_ssl,
            ) as client:
                headers = dict(config.headers)
                if config.rotate_ua:
                    from .user_agents import random_ua
                    headers["User-Agent"] = random_ua()
                elif "User-Agent" not in headers:
                    headers["User-Agent"] = (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )

                response = await client.get(validated_url, headers=headers)

                # Check for retryable status codes
                if response.status_code in (429, 500, 502, 503, 504):
                    if attempt < max_retries:
                        retry_after = float(
                            response.headers.get("Retry-After", "1")
                        )
                        await asyncio.sleep(min(retry_after, 60))
                        continue

                # Raise for client errors (4xx except 429)
                if 400 <= response.status_code < 500 and response.status_code != 429:
                    raise HTTPError(
                        f"HTTP {response.status_code}",
                        status_code=response.status_code,
                        response_body=response.text,
                    )

                request_time = time.perf_counter() - start_time

                return AsyncScrapeResult(
                    text=response.text,
                    content=response.content,
                    status=response.status_code,
                    headers=dict(response.headers),
                    url=str(response.url),
                    request_time=request_time,
                )

        except httpx.TimeoutException as e:
            last_error = RequestTimeout(
                f"Request to {url} timed out",
                timeout=config.timeout,
                cause=e,
            )
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)
                continue
            raise last_error

        except httpx.ConnectError as e:
            last_error = NetworkError(f"Connection failed: {e}", cause=e)
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)
                continue
            raise last_error

        except HTTPError:
            raise

        except Exception as e:
            last_error = NetworkError(f"Request failed: {e}", cause=e)
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)
                continue
            raise last_error

    raise RetryExhausted(
        f"All {max_retries + 1} attempts failed",
        attempts=max_retries + 1,
        last_error=last_error,
    )


async def async_scrape_many(
    urls: Sequence[str],
    config: Config | None = None,
    concurrency: int = 10,
    on_result: Callable[[str, AsyncScrapeResult], None] | None = None,
    on_error: Callable[[str, Exception], None] | None = None,
) -> tuple[list[AsyncScrapeResult], list[tuple[str, Exception]]]:
    """Scrape multiple URLs concurrently.

    Parameters
    ----------
    urls : Sequence[str]
        URLs to scrape.
    config : Config, optional
        Configuration options.
    concurrency : int
        Maximum concurrent requests.
    on_result : callable, optional
        Callback for each successful result.
    on_error : callable, optional
        Callback for each error.

    Returns
    -------
    tuple[list[AsyncScrapeResult], list[tuple[str, Exception]]]
        Tuple of (results, errors).
    """
    if not urls:
        return ([], [])

    results: list[AsyncScrapeResult] = []
    errors: list[tuple[str, Exception]] = []
    semaphore = asyncio.Semaphore(concurrency)

    async def fetch_one(url: str) -> None:
        async with semaphore:
            try:
                result = await async_scrape(url, config)
                results.append(result)
                if on_result:
                    on_result(url, result)
            except Exception as e:
                errors.append((url, e))
                if on_error:
                    on_error(url, e)

    await asyncio.gather(*[fetch_one(url) for url in urls])
    return (results, errors)


async def async_post(
    url: str,
    data: dict[str, Any] | None = None,
    json_data: dict[str, Any] | None = None,
    config: Config | None = None,
) -> AsyncScrapeResult:
    """Async POST request.

    Parameters
    ----------
    url : str
        URL to post to.
    data : dict, optional
        Form data to send.
    json_data : dict, optional
        JSON data to send.
    config : Config, optional
        Configuration options.

    Returns
    -------
    AsyncScrapeResult
        The response result.
    """
    if config is None:
        config = Config()

    # Validate URL with allow_localhost from config
    validated_url = validate_url(
        url,
        allow_localhost=config.allow_localhost,
    )

    start_time = time.perf_counter()

    async with httpx.AsyncClient(
        timeout=config.timeout,
        follow_redirects=True,
        verify=config.verify_ssl,
    ) as client:
        headers = dict(config.headers)
        if "User-Agent" not in headers:
            headers["User-Agent"] = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )

        response = await client.post(
            validated_url,
            headers=headers,
            data=data,
            json=json_data,
        )

        # Raise for client errors
        if 400 <= response.status_code < 500:
            raise HTTPError(
                f"HTTP {response.status_code}",
                status_code=response.status_code,
                response_body=response.text,
            )

        request_time = time.perf_counter() - start_time

        return AsyncScrapeResult(
            text=response.text,
            content=response.content,
            status=response.status_code,
            headers=dict(response.headers),
            url=str(response.url),
            request_time=request_time,
        )


async def async_download_many(
    urls: Sequence[str],
    output_dir: str,
    config: Config | None = None,
    concurrency: int = 5,
) -> list[Path]:
    """Download multiple files concurrently.

    Parameters
    ----------
    urls : Sequence[str]
        URLs to download.
    output_dir : str
        Directory to save files.
    config : Config, optional
        Configuration options.
    concurrency : int
        Maximum concurrent downloads.

    Returns
    -------
    list[Path]
        Paths to downloaded files.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if not urls:
        return []

    if config is None:
        config = Config()

    results: list[Path] = []
    semaphore = asyncio.Semaphore(concurrency)

    async def download_one(url: str) -> Path | None:
        async with semaphore:
            try:
                # Validate URL
                validated_url = validate_url(
                    url,
                    allow_localhost=config.allow_localhost,
                )

                # Get filename from URL
                parsed = urlparse(url)
                filename = Path(parsed.path).name or "download"
                file_path = output_path / filename

                async with httpx.AsyncClient(
                    timeout=config.timeout,
                    follow_redirects=True,
                ) as client:
                    response = await client.get(validated_url)
                    if response.status_code >= 400:
                        return None
                    file_path.write_bytes(response.content)
                    return file_path
            except Exception:
                return None

    tasks = [download_one(url) for url in urls]
    downloaded = await asyncio.gather(*tasks)
    results = [p for p in downloaded if p is not None]

    return results
