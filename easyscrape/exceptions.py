"""Custom exceptions for EasyScrape.

This module defines all exception types used by the library.
All exceptions inherit from EasyScrapeError for easy catching.

Example
-------
    from easyscrape.exceptions import EasyScrapeError, NetworkError

    try:
        result = scrape(url)
    except NetworkError as e:
        print(f"Network failed: {e}")
    except EasyScrapeError as e:
        print(f"Scraping failed: {e}")
"""
from __future__ import annotations

from typing import Final

__all__: Final[tuple[str, ...]] = (
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


class EasyScrapeError(Exception):
    """Base exception for all EasyScrape errors.

    All exceptions raised by EasyScrape inherit from this class,
    making it easy to catch any library error.

    Parameters
    ----------
    message : str
        Human-readable error description.
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class NetworkError(EasyScrapeError):
    """Raised when a network operation fails.

    This includes connection errors, DNS failures, and other
    transport-level issues.

    Parameters
    ----------
    message : str
        Error description.
    cause : Exception, optional
        The underlying exception that caused this error.
    """

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.cause = cause


class ConnectionFailed(NetworkError):
    """Raised when a connection cannot be established.

    This includes connection refused, connection reset, and other
    TCP-level connection failures.

    Parameters
    ----------
    message : str
        Error description.
    host : str, optional
        The host that failed to connect.
    port : int, optional
        The port that failed to connect.
    cause : Exception, optional
        The underlying exception.
    """

    def __init__(
        self,
        message: str,
        host: str | None = None,
        port: int | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message, cause)
        self.host = host
        self.port = port


class DNSError(NetworkError):
    """Raised when DNS resolution fails.

    Parameters
    ----------
    message : str
        Error description.
    hostname : str, optional
        The hostname that failed to resolve.
    cause : Exception, optional
        The underlying exception.
    """

    def __init__(
        self,
        message: str,
        hostname: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message, cause)
        self.hostname = hostname


class TooManyRedirects(NetworkError):
    """Raised when too many redirects are followed.

    Parameters
    ----------
    message : str
        Error description.
    max_redirects : int, optional
        The maximum number of redirects allowed.
    cause : Exception, optional
        The underlying exception.
    """

    def __init__(
        self,
        message: str,
        max_redirects: int | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message, cause)
        self.max_redirects = max_redirects


class HTTPError(EasyScrapeError):
    """Raised when an HTTP request returns an error status.

    Parameters
    ----------
    message : str
        Error description.
    status_code : int
        The HTTP status code.
    response_body : str, optional
        The response body, if available.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class ClientError(HTTPError):
    """Raised when an HTTP 4xx client error occurs.

    Parameters
    ----------
    message : str
        Error description.
    status_code : int
        The HTTP status code (4xx).
    response_body : str, optional
        The response body, if available.
    """

    pass


class ServerError(HTTPError):
    """Raised when an HTTP 5xx server error occurs.

    Parameters
    ----------
    message : str
        Error description.
    status_code : int
        The HTTP status code (5xx).
    response_body : str, optional
        The response body, if available.
    """

    pass


class InvalidURLError(EasyScrapeError):
    """Raised when a URL is invalid or blocked.

    This includes malformed URLs, blocked hosts (localhost, private IPs),
    and dangerous schemes (javascript:, data:, file:).

    Parameters
    ----------
    message : str
        Error description.
    url : str, optional
        The invalid URL.
    reason : str, optional
        The specific reason the URL was rejected.
    """

    def __init__(
        self,
        message: str,
        url: str | None = None,
        reason: str | None = None,
    ) -> None:
        super().__init__(message)
        self.url = url
        self.reason = reason if reason is not None else message


class ExtractionError(EasyScrapeError):
    """Raised when data extraction fails.

    This can happen when a selector doesn't match, or when
    the extracted data doesn't match the expected format.

    Parameters
    ----------
    message : str
        Error description.
    selector : str, optional
        The selector that failed.
    """

    def __init__(self, message: str, selector: str | None = None) -> None:
        super().__init__(message)
        self.selector = selector


class SelectorError(ExtractionError):
    """Raised when a CSS or XPath selector is invalid or fails.

    This is a more specific type of ExtractionError for selector issues.

    Parameters
    ----------
    message : str
        Error description.
    selector : str, optional
        The problematic selector.
    selector_type : str, optional
        The type of selector ('css' or 'xpath').
    """

    def __init__(
        self,
        message: str,
        selector: str | None = None,
        selector_type: str | None = None,
    ) -> None:
        super().__init__(message, selector)
        self.selector_type = selector_type


class ConfigError(EasyScrapeError):
    """Raised when configuration is invalid.

    Parameters
    ----------
    message : str
        Error description.
    param : str, optional
        The invalid configuration parameter.
    """

    def __init__(self, message: str, param: str | None = None) -> None:
        super().__init__(message)
        self.param = param


class RateLimitHit(EasyScrapeError):
    """Raised when a rate limit is hit.

    Parameters
    ----------
    message : str
        Error description.
    retry_after : float, optional
        Seconds to wait before retrying.
    """

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class ProxyDead(EasyScrapeError):
    """Raised when a proxy is not working.

    Parameters
    ----------
    message : str
        Error description.
    proxy : str, optional
        The dead proxy URL.
    """

    def __init__(self, message: str, proxy: str | None = None) -> None:
        super().__init__(message)
        self.proxy = proxy


class CaptchaDetected(EasyScrapeError):
    """Raised when a CAPTCHA is detected.

    Parameters
    ----------
    message : str
        Error description.
    captcha_type : str, optional
        The type of CAPTCHA detected.
    """

    def __init__(self, message: str, captcha_type: str | None = None) -> None:
        super().__init__(message)
        self.captcha_type = captcha_type


class RobotsBlocked(EasyScrapeError):
    """Raised when robots.txt blocks access.

    Parameters
    ----------
    message : str
        Error description.
    url : str, optional
        The blocked URL.
    """

    def __init__(self, message: str, url: str | None = None) -> None:
        super().__init__(message)
        self.url = url


class RetryExhausted(EasyScrapeError):
    """Raised when all retry attempts have failed.

    Parameters
    ----------
    message : str
        Error description.
    attempts : int, optional
        Number of attempts made.
    last_error : Exception, optional
        The last error that occurred.
    """

    def __init__(
        self,
        message: str,
        attempts: int | None = None,
        last_error: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.last_error = last_error


class BrowserError(EasyScrapeError):
    """Raised when browser automation fails.

    Parameters
    ----------
    message : str
        Error description.
    """

    pass


class CircuitBreakerOpen(EasyScrapeError):
    """Raised when a circuit breaker is open.

    Parameters
    ----------
    message : str
        Error description.
    domain : str, optional
        The domain whose circuit is open.
    """

    def __init__(self, message: str, domain: str | None = None) -> None:
        super().__init__(message)
        self.domain = domain


class ValidationError(EasyScrapeError):
    """Raised when input validation fails.

    Parameters
    ----------
    message : str
        Error description.
    field : str, optional
        The field that failed validation.
    value : Any, optional
        The value that failed validation.
    """

    def __init__(
        self,
        message: str,
        field: str | None = None,
        value: str | None = None,
    ) -> None:
        super().__init__(message)
        self.field = field
        self.value = value


class RequestTimeout(NetworkError):
    """Raised when a request times out.

    Parameters
    ----------
    message : str
        Error description.
    timeout : float, optional
        The timeout value that was exceeded.
    """

    def __init__(
        self,
        message: str,
        timeout: float | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message, cause)
        self.timeout = timeout


class ContentTooLarge(EasyScrapeError):
    """Raised when response content exceeds size limit.

    Parameters
    ----------
    message : str
        Error description.
    size : int, optional
        The actual content size.
    limit : int, optional
        The size limit that was exceeded.
    """

    def __init__(
        self,
        message: str,
        size: int | None = None,
        limit: int | None = None,
    ) -> None:
        super().__init__(message)
        self.size = size
        self.limit = limit


class SSLCertificateError(NetworkError):
    """Raised when SSL certificate validation fails.

    Parameters
    ----------
    message : str
        Error description.
    """

    pass


# Alias for backwards compatibility
SSLError = SSLCertificateError
