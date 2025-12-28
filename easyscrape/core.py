"""Core scraping functions for EasyScrape.

This module provides the main scraping interface.

Example
-------
    from easyscrape import scrape

    result = scrape("https://example.com")
    print(result.css("h1"))
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, Final, Sequence
from urllib.parse import urljoin, urlparse

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
    "scrape",
    "scrape_many",
    "scrape_if_changed",
    "post",
    "download",
    "download_many",
    "async_scrape",
    "ScrapeResult",
    "ScrapingResult",
)


class CaseInsensitiveDict(dict):
    """A dictionary that allows case-insensitive key access."""

    def __init__(self, data: dict[str, str] | None = None) -> None:
        super().__init__()
        self._keys_map: dict[str, str] = {}  # lowercase -> original
        if data:
            for key, value in data.items():
                self[key] = value

    def __setitem__(self, key: str, value: str) -> None:
        lower_key = key.lower()
        # If we already have this key (case-insensitive), use the original case
        if lower_key in self._keys_map:
            original_key = self._keys_map[lower_key]
            super().__setitem__(original_key, value)
        else:
            self._keys_map[lower_key] = key
            super().__setitem__(key, value)

    def __getitem__(self, key: str) -> str:
        lower_key = key.lower()
        if lower_key in self._keys_map:
            return super().__getitem__(self._keys_map[lower_key])
        raise KeyError(key)

    def __contains__(self, key: object) -> bool:
        if isinstance(key, str):
            return key.lower() in self._keys_map
        return False

    def get(self, key: str, default: str | None = None) -> str | None:
        try:
            return self[key]
        except KeyError:
            return default

    def __delitem__(self, key: str) -> None:
        lower_key = key.lower()
        if lower_key in self._keys_map:
            original_key = self._keys_map.pop(lower_key)
            super().__delitem__(original_key)
        else:
            raise KeyError(key)


class ScrapeResult:
    """Result from a scrape operation.

    Provides convenient methods for extracting data from the response.

    Parameters
    ----------
    text : str
        The response text/HTML.
    content : bytes
        The raw response content.
    status_code : int
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
        "_status_code",
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
        status_code: int,
        headers: dict[str, str],
        url: str,
        request_time: float,
        from_cache: bool = False,
    ) -> None:
        self._text = text
        self._content = content
        self._status_code = status_code
        self._headers = CaseInsensitiveDict(headers)
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
        return self._status_code

    @property
    def headers(self) -> CaseInsensitiveDict:
        """Response headers (case-insensitive access)."""
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
        return 200 <= self._status_code < 300

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

    def meta(self, name: str | None = None) -> str | dict[str, str]:
        """Extract meta tag(s).

        If name is provided, returns that meta tag's content.
        Otherwise returns a dict of common meta tags.
        """
        if name:
            return self.extractor.meta(name)
        # Return common meta tags as dict
        common_tags = ["description", "keywords", "author", "viewport"]
        return {tag: self.extractor.meta(tag) for tag in common_tags if self.extractor.meta(tag)}

    @property
    def cache_headers(self) -> dict[str, str]:
        """Return cache-related headers with original case preserved."""
        cache_keys = [
            "cache-control", "etag", "last-modified", "expires",
            "age", "vary", "pragma",
            "Cache-Control", "ETag", "Last-Modified", "Expires",
            "Age", "Vary", "Pragma",
        ]
        result = {}
        for key in cache_keys:
            if key in self._headers:
                # Use the requested case for the key in result
                result[key] = self._headers[key]
        return result

    @property
    def not_modified(self) -> bool:
        """True if response is 304 Not Modified."""
        return self._status_code == 304

    @property
    def etag(self) -> str | None:
        """Get ETag header value."""
        return self._headers.get("ETag") or self._headers.get("etag")

    @property
    def last_modified(self) -> str | None:
        """Get Last-Modified header value."""
        return self._headers.get("Last-Modified") or self._headers.get("last-modified")


# Alias for backwards compatibility
ScrapingResult = ScrapeResult


def scrape(
    url: str,
    config: Config | None = None,
) -> ScrapeResult:
    """Scrape a URL and return the result.

    Parameters
    ----------
    url : str
        URL to scrape.
    config : Config, optional
        Configuration options.

    Returns
    -------
    ScrapeResult
        The scrape result with extraction methods.

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
            with httpx.Client(
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

                response = client.get(validated_url, headers=headers)

                # Check for retryable status codes
                if response.status_code in (429, 500, 502, 503, 504):
                    if attempt < max_retries:
                        retry_after = float(
                            response.headers.get("Retry-After", "1")
                        )
                        time.sleep(min(retry_after, 60))
                        continue

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
            last_error = RequestTimeout(
                f"Request to {url} timed out",
                timeout=config.timeout,
                cause=e,
            )
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                continue
            raise last_error

        except httpx.ConnectError as e:
            last_error = NetworkError(f"Connection failed: {e}", cause=e)
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                continue
            raise last_error

        except Exception as e:
            last_error = NetworkError(f"Request failed: {e}", cause=e)
            if attempt < max_retries:
                time.sleep(2 ** attempt)
                continue
            raise last_error

    raise RetryExhausted(
        f"All {max_retries + 1} attempts failed",
        attempts=max_retries + 1,
        last_error=last_error,
    )


def scrape_many(
    urls: Sequence[str],
    config: Config | None = None,
    on_result: Callable[[str, ScrapeResult], None] | None = None,
    on_error: Callable[[str, Exception], None] | None = None,
) -> tuple[list[ScrapeResult], list[tuple[str, Exception]]]:
    """Scrape multiple URLs sequentially.

    For concurrent scraping, use async_scrape_many instead.

    Parameters
    ----------
    urls : Sequence[str]
        URLs to scrape.
    config : Config, optional
        Configuration options.
    on_result : callable, optional
        Callback for each successful result.
    on_error : callable, optional
        Callback for each error.

    Returns
    -------
    tuple[list[ScrapeResult], list[tuple[str, Exception]]]
        Tuple of (results, errors).
    """
    results: list[ScrapeResult] = []
    errors: list[tuple[str, Exception]] = []

    for url in urls:
        try:
            result = scrape(url, config)
            results.append(result)
            if on_result:
                on_result(url, result)
        except Exception as e:
            errors.append((url, e))
            if on_error:
                on_error(url, e)

    return (results, errors)


def scrape_if_changed(
    url: str,
    etag: str | None = None,
    last_modified: str | None = None,
    config: Config | None = None,
) -> ScrapeResult | None:
    """Scrape a URL only if it has changed.

    Uses ETag and/or Last-Modified headers for conditional requests.

    Parameters
    ----------
    url : str
        URL to scrape.
    etag : str, optional
        Previous ETag value.
    last_modified : str, optional
        Previous Last-Modified value.
    config : Config, optional
        Configuration options.

    Returns
    -------
    ScrapeResult or None
        Result if changed, None if not modified.
    """
    if config is None:
        config = Config()

    # Add conditional headers
    headers = dict(config.headers)
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    new_config = Config(
        timeout=config.timeout,
        max_retries=config.max_retries,
        max_redirects=config.max_redirects,
        rate_limit=config.rate_limit,
        cache_enabled=config.cache_enabled,
        cache_ttl=config.cache_ttl,
        javascript=config.javascript,
        headers=headers,
        proxies=config.proxies,
        rotate_ua=config.rotate_ua,
        verify_ssl=config.verify_ssl,
        respect_robots=config.respect_robots,
        verbose=config.verbose,
        allow_localhost=config.allow_localhost,
        stealth_mode=config.stealth_mode,
    )

    result = scrape(url, new_config)

    if result.status_code == 304:
        return None

    return result


def post(
    url: str,
    data: dict[str, Any] | None = None,
    json_data: dict[str, Any] | None = None,
    config: Config | None = None,
) -> ScrapeResult:
    """Send a POST request.

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
    ScrapeResult
        The response result.
    """
    if config is None:
        config = Config()

    validated_url = validate_url(
        url,
        allow_localhost=config.allow_localhost,
    )
    start_time = time.perf_counter()

    with httpx.Client(
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

        response = client.post(
            validated_url,
            headers=headers,
            data=data,
            json=json_data,
        )

        request_time = time.perf_counter() - start_time

        return ScrapeResult(
            text=response.text,
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
            url=str(response.url),
            request_time=request_time,
        )


def download(
    url: str,
    output_path: str | Path,
    config: Config | None = None,
) -> Path:
    """Download a file.

    Parameters
    ----------
    url : str
        URL to download.
    output_path : str or Path
        Path to save the file.
    config : Config, optional
        Configuration options.

    Returns
    -------
    Path
        Path to the downloaded file.
    """
    if config is None:
        config = Config()

    validated_url = validate_url(
        url,
        allow_localhost=config.allow_localhost,
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with httpx.Client(
        timeout=config.timeout,
        follow_redirects=True,
    ) as client:
        response = client.get(validated_url)
        response.raise_for_status()
        output.write_bytes(response.content)

    return output


def download_many(
    urls: Sequence[str],
    output_dir: str | Path,
    config: Config | None = None,
) -> list[Path]:
    """Download multiple files.

    Parameters
    ----------
    urls : Sequence[str]
        URLs to download.
    output_dir : str or Path
        Directory to save files.
    config : Config, optional
        Configuration options.

    Returns
    -------
    list[Path]
        Paths to downloaded files.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    results = []
    for url in urls:
        try:
            parsed = urlparse(url)
            filename = Path(parsed.path).name or "download"
            file_path = output_path / filename
            download(url, file_path, config)
            results.append(file_path)
        except Exception:
            continue

    return results


# Async wrapper for convenience
async def async_scrape(
    url: str,
    config: Config | None = None,
) -> ScrapeResult:
    """Async version of scrape().

    This is a convenience wrapper. For full async functionality,
    use easyscrape.async_core.async_scrape directly.
    """
    from .async_core import async_scrape as _async_scrape
    result = await _async_scrape(url, config)
    # Convert AsyncScrapeResult to ScrapeResult for API compatibility
    return ScrapeResult(
        text=result.text,
        content=result.content,
        status_code=result.status_code,
        headers=result.headers,
        url=result.url,
        request_time=result.request_time,
        from_cache=result.from_cache,
    )
