"""
Constants and configuration values for EasyScrape.

All magic numbers and hardcoded values are centralised here for maintainability.
"""
from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

# HTTP Status Codes
HTTP_OK: Final[int] = 200
HTTP_CREATED: Final[int] = 201
HTTP_NO_CONTENT: Final[int] = 204
HTTP_MOVED_PERMANENTLY: Final[int] = 301
HTTP_FOUND: Final[int] = 302
HTTP_NOT_MODIFIED: Final[int] = 304
HTTP_BAD_REQUEST: Final[int] = 400
HTTP_UNAUTHORIZED: Final[int] = 401  # RFC 7235 spelling
HTTP_UNAUTHORISED: Final[int] = 401  # British alias (deprecated)
HTTP_FORBIDDEN: Final[int] = 403
HTTP_NOT_FOUND: Final[int] = 404
HTTP_METHOD_NOT_ALLOWED: Final[int] = 405
HTTP_TIMEOUT: Final[int] = 408
HTTP_CONFLICT: Final[int] = 409
HTTP_GONE: Final[int] = 410
HTTP_UNPROCESSABLE: Final[int] = 422
HTTP_TOO_MANY_REQUESTS: Final[int] = 429
HTTP_PROXY_AUTH_REQUIRED: Final[int] = 407
HTTP_INTERNAL_ERROR: Final[int] = 500
HTTP_BAD_GATEWAY: Final[int] = 502
HTTP_SERVICE_UNAVAILABLE: Final[int] = 503
HTTP_GATEWAY_TIMEOUT: Final[int] = 504

# Cloudflare-specific status codes
CF_WEB_SERVER_DOWN: Final[int] = 521
CF_CONNECTION_TIMED_OUT: Final[int] = 522
CF_ORIGIN_UNREACHABLE: Final[int] = 523
CF_TIMEOUT_OCCURRED: Final[int] = 524
CF_SSL_HANDSHAKE_FAILED: Final[int] = 525
CF_INVALID_SSL: Final[int] = 526

# Status code sets for retry logic
RETRYABLE_STATUS_CODES: Final[frozenset[int]] = frozenset({
    HTTP_TIMEOUT,
    HTTP_TOO_MANY_REQUESTS,
    HTTP_INTERNAL_ERROR,
    HTTP_BAD_GATEWAY,
    HTTP_SERVICE_UNAVAILABLE,
    HTTP_GATEWAY_TIMEOUT,
    CF_WEB_SERVER_DOWN,
    CF_CONNECTION_TIMED_OUT,
    CF_ORIGIN_UNREACHABLE,
    CF_TIMEOUT_OCCURRED,
})

NON_RETRYABLE_CLIENT_ERRORS: Final[frozenset[int]] = frozenset({
    HTTP_BAD_REQUEST,
    HTTP_UNAUTHORISED,
    HTTP_FORBIDDEN,
    HTTP_NOT_FOUND,
    HTTP_METHOD_NOT_ALLOWED,
    HTTP_GONE,
    HTTP_UNPROCESSABLE,
})

# Timeouts (seconds)
DEFAULT_TIMEOUT: Final[float] = 30.0
DEFAULT_CONNECT_TIMEOUT: Final[float] = 10.0
DEFAULT_READ_TIMEOUT: Final[float] = 30.0
DEFAULT_WRITE_TIMEOUT: Final[float] = 30.0
DEFAULT_POOL_TIMEOUT: Final[float] = 10.0
MIN_TIMEOUT: Final[float] = 1.0
MAX_TIMEOUT: Final[float] = 300.0

# Retry configuration
DEFAULT_MAX_RETRIES: Final[int] = 3
DEFAULT_RETRY_DELAY: Final[float] = 1.0
DEFAULT_BACKOFF_FACTOR: Final[float] = 2.0
MAX_RETRY_DELAY: Final[float] = 120.0
MIN_RETRY_DELAY: Final[float] = 0.1
MAX_RETRIES_LIMIT: Final[int] = 10

# Rate limiting
DEFAULT_RATE_LIMIT: Final[float] = 1.0
MIN_RATE_LIMIT: Final[float] = 0.0
MAX_RATE_LIMIT: Final[float] = 60.0
DEFAULT_JITTER_FACTOR: Final[float] = 0.2
ADAPTIVE_BACKOFF_MAX_MULTIPLIER: Final[int] = 64

# Cache configuration
DEFAULT_CACHE_TTL: Final[int] = 3600
DEFAULT_CACHE_DIR: Final[str] = ".escache"
MAX_MEMORY_CACHE_ENTRIES: Final[int] = 1000
CACHE_KEY_LENGTH: Final[int] = 32
MIN_CACHE_TTL: Final[int] = 0
SECONDS_PER_DAY: Final[int] = 86400
MAX_CACHE_TTL: Final[int] = 2592000  # 30 days

# Connection pool
DEFAULT_MAX_CONNECTIONS: Final[int] = 100
DEFAULT_MAX_KEEPALIVE_CONNECTIONS: Final[int] = 20
DEFAULT_KEEPALIVE_EXPIRY: Final[float] = 30.0

# Concurrency
DEFAULT_CONCURRENT_LIMIT: Final[int] = 10
MIN_CONCURRENT_LIMIT: Final[int] = 1
MAX_CONCURRENT_LIMIT: Final[int] = 100

# Circuit breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD: Final[int] = 5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT: Final[float] = 60.0
CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS: Final[int] = 3

# Content limits
MAX_RESPONSE_SIZE: Final[int] = 104_857_600  # 100 MiB
MAX_REDIRECT_COUNT: Final[int] = 20
DEFAULT_MAX_REDIRECTS: Final[int] = 10

# URL validation
ALLOWED_SCHEMES: Final[frozenset[str]] = frozenset({"http", "https"})
MAX_URL_LENGTH: Final[int] = 8192

# Proxy configuration
PROXY_FAILURE_THRESHOLD: Final[int] = 5
PROXY_RECOVERY_INTERVAL: Final[float] = 300.0
PROXY_LOG_TRUNCATE: Final[int] = 15  # chars to show in logs (hide credentials)
PROXY_BAD_STATUS_CODES: Final[frozenset[int]] = frozenset({
    HTTP_FORBIDDEN, HTTP_PROXY_AUTH_REQUIRED, HTTP_BAD_GATEWAY,
    HTTP_SERVICE_UNAVAILABLE, CF_WEB_SERVER_DOWN, CF_CONNECTION_TIMED_OUT,
    CF_ORIGIN_UNREACHABLE, CF_TIMEOUT_OCCURRED,
})

# Robots.txt
DEFAULT_ROBOTS_TTL: Final[int] = 86400
ROBOTS_MAX_SIZE: Final[int] = 524_288  # 512 KiB

# User agent
USER_AGENT_ROTATION_STRATEGIES: Final[frozenset[str]] = frozenset({
    "random",
    "round-robin",
    "weighted",
})

# Selector limits
MAX_CSS_SELECTOR_LENGTH: Final[int] = 1000
MAX_XPATH_LENGTH: Final[int] = 2000
MAX_REGEX_LENGTH: Final[int] = 1000

# Selector types
SELECTOR_TYPE_CSS: Final[str] = "css"
SELECTOR_TYPE_XPATH: Final[str] = "xpath"
SELECTOR_TYPE_REGEX: Final[str] = "regex"
SELECTOR_TYPE_JMESPATH: Final[str] = "jmespath"

# Export formats
EXPORT_FORMAT_JSON: Final[str] = "json"
EXPORT_FORMAT_CSV: Final[str] = "csv"
EXPORT_FORMAT_JSONL: Final[str] = "jsonl"
EXPORT_FORMAT_EXCEL: Final[str] = "xlsx"
EXPORT_FORMAT_PARQUET: Final[str] = "parquet"
EXPORT_FORMAT_SQLITE: Final[str] = "sqlite"

# Encoding
DEFAULT_ENCODING: Final[str] = "utf-8"
FALLBACK_ENCODINGS: Final[tuple[str, ...]] = ("utf-8", "latin-1", "cp1252", "iso-8859-1")

# File extensions for content types (immutable mapping)
CONTENT_TYPE_EXTENSIONS: Final[Mapping[str, str]] = MappingProxyType({
    "text/html": ".html",
    "text/plain": ".txt",
    "text/css": ".css",
    "text/xml": ".xml",
    "application/json": ".json",
    "application/xml": ".xml",
    "application/xhtml+xml": ".xhtml",
    "application/javascript": ".js",
    "application/pdf": ".pdf",
    "application/octet-stream": ".bin",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
})

# Logging
LOG_FORMAT: Final[str] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
