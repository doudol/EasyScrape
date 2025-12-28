"""EasyScrape - Fast, secure web scraping library.

Example
-------
    from easyscrape import scrape, Config

    result = scrape("https://example.com")
    print(result.css("h1"))
"""
from __future__ import annotations

from typing import Final

from .config import Config
from .core import (
    ScrapeResult,
    ScrapingResult,
    scrape,
    scrape_many,
    scrape_if_changed,
    post,
    download,
    download_many,
    async_scrape,
)
from .async_core import (
    async_scrape as async_scrape_core,
    async_scrape_many,
    async_post,
    async_download_many,
    AsyncScrapeResult,
)
from .extractors import Extractor, SelectorType
from .exceptions import (
    EasyScrapeError,
    NetworkError,
    HTTPError,
    InvalidURLError,
    ExtractionError,
    SelectorError,
    ConfigError,
    RateLimitHit,
    ProxyDead,
    CaptchaDetected,
    RobotsBlocked,
    RetryExhausted,
    BrowserError,
    CircuitBreakerOpen,
    ValidationError,
    RequestTimeout,
    ContentTooLarge,
    SSLCertificateError,
    SSLError,
    ConnectionFailed,
    DNSError,
    TooManyRedirects,
    ServerError,
    ClientError,
)
from .validate import validate_url, is_safe_url, URLValidator
from .session import Session, AsyncSession
from .export import to_json, to_csv, to_jsonl, Exporter

__version__: Final[str] = "0.1.0"
__all__: Final[tuple[str, ...]] = (
    # Core
    "scrape",
    "scrape_many",
    "scrape_if_changed",
    "post",
    "download",
    "download_many",
    "async_scrape",
    "async_scrape_many",
    "async_post",
    "async_download_many",
    # Results
    "ScrapeResult",
    "ScrapingResult",
    "AsyncScrapeResult",
    # Config
    "Config",
    # Extraction
    "Extractor",
    "SelectorType",
    # Validation
    "validate_url",
    "is_safe_url",
    "URLValidator",
    # Session
    "Session",
    "AsyncSession",
    # Export
    "to_json",
    "to_csv",
    "to_jsonl",
    "Exporter",
    # Exceptions
    "EasyScrapeError",
    "NetworkError",
    "HTTPError",
    "InvalidURLError",
    "ExtractionError",
    "SelectorError",
    "ConfigError",
    "RateLimitHit",
    "ProxyDead",
    "CaptchaDetected",
    "RobotsBlocked",
    "RetryExhausted",
    "BrowserError",
    "CircuitBreakerOpen",
    "ValidationError",
    "RequestTimeout",
    "ContentTooLarge",
    "SSLCertificateError",
    "SSLError",
    "ConnectionFailed",
    "DNSError",
    "TooManyRedirects",
    "ServerError",
    "ClientError",
)
