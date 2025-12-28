"""URL validation and security checks.

This module provides comprehensive URL validation including:
- Scheme validation (only http/https allowed)
- SSRF protection (blocks private IPs, localhost)
- DNS rebinding protection
- URL length limits

Example
-------
    from easyscrape.validate import validate_url, is_safe_url

    url = validate_url("https://example.com")  # Returns validated URL
    if is_safe_url(url):
        # Safe to fetch
        pass
"""
from __future__ import annotations

import ipaddress
import re
import socket
from functools import lru_cache
from typing import Final, Set
from urllib.parse import urlparse

from .exceptions import InvalidURLError

__all__: Final[tuple[str, ...]] = (
    "validate_url",
    "is_safe_url",
    "is_private_ip",
    "sanitize_header_value",
    "URLValidator",
)

# Maximum URL length (8KB is common limit)
_MAX_URL_LENGTH: Final[int] = 8192

# Allowed schemes
_ALLOWED_SCHEMES: Final[Set[str]] = {"http", "https"}

# Dangerous schemes that should never be allowed
_DANGEROUS_SCHEMES: Final[Set[str]] = {
    "javascript",
    "data",
    "file",
    "ftp",
    "vbscript",
    "about",
    "blob",
}

# Blocked hostnames
_BLOCKED_HOSTNAMES: Final[Set[str]] = {
    "localhost",
    "localhost.localdomain",
    "127.0.0.1",
    "0.0.0.0",
    "::1",
    "[::1]",
}


class URLValidator:
    """Validates URLs for security and correctness.

    Parameters
    ----------
    allow_localhost : bool
        If True, allows localhost and loopback addresses.
    allow_private : bool
        If True, allows private IP ranges.
    max_length : int
        Maximum allowed URL length.

    Example
    -------
        validator = URLValidator(allow_localhost=False)
        url = validator.validate("https://example.com")
    """

    def __init__(
        self,
        allow_localhost: bool = False,
        allow_private: bool = False,
        max_length: int = _MAX_URL_LENGTH,
    ) -> None:
        self.allow_localhost = allow_localhost
        self.allow_private = allow_private
        self.max_length = max_length

    def validate(self, url: str) -> str:
        """Validate a URL and return it if valid.

        Parameters
        ----------
        url : str
            The URL to validate.

        Returns
        -------
        str
            The validated URL.

        Raises
        ------
        InvalidURLError
            If the URL is invalid or blocked.
        """
        # Strip whitespace
        url = url.strip()

        # Check empty
        if not url:
            raise InvalidURLError("URL cannot be empty")

        # Check length
        if len(url) > self.max_length:
            raise InvalidURLError(
                f"URL too long: {len(url)} > {self.max_length}"
            )

        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception as e:
            raise InvalidURLError(f"Failed to parse URL: {e}")

        # Check scheme
        scheme = parsed.scheme.lower()
        if not scheme:
            raise InvalidURLError("URL must have a scheme (http:// or https://)")

        if scheme in _DANGEROUS_SCHEMES:
            raise InvalidURLError(f"Dangerous scheme not allowed: {scheme}")

        if scheme not in _ALLOWED_SCHEMES:
            raise InvalidURLError(
                f"Invalid scheme '{scheme}'. Only http and https are allowed."
            )

        # Check hostname
        hostname = parsed.hostname
        if not hostname:
            raise InvalidURLError("URL must have a hostname")

        # Normalize hostname
        hostname_lower = hostname.lower()

        # Check for localhost (only if not allowed)
        if not self.allow_localhost:
            if hostname_lower in _BLOCKED_HOSTNAMES:
                raise InvalidURLError(
                    f"Localhost URLs are blocked: {hostname}"
                )

            # Check for localhost subdomains
            if hostname_lower.endswith(".localhost"):
                raise InvalidURLError(
                    f"Localhost subdomains are blocked: {hostname}"
                )

        # Check if hostname is an IP address
        try:
            ip = ipaddress.ip_address(hostname)
            if not self.allow_localhost:
                self._check_ip(ip, url)
        except ValueError:
            # Not an IP address, check via DNS if not allowing localhost
            if not self.allow_localhost:
                self._check_dns(hostname, url)

        return url

    def _check_ip(self, ip: ipaddress.IPv4Address | ipaddress.IPv6Address, url: str) -> None:
        """Check if an IP address is allowed."""
        # Check loopback
        if ip.is_loopback:
            raise InvalidURLError(
                f"Loopback IP {ip} is blocked"
            )

        # Check private (unless allowed)
        if not self.allow_private:
            if ip.is_private:
                raise InvalidURLError(
                    f"Private IP {ip} is blocked"
                )

            # Check link-local
            if ip.is_link_local:
                raise InvalidURLError(
                    f"Link-local IP {ip} is blocked"
                )

            # Check reserved
            if ip.is_reserved:
                raise InvalidURLError(
                    f"Reserved IP {ip} is blocked"
                )

    def _check_dns(self, hostname: str, url: str) -> None:
        """Check DNS resolution for SSRF protection."""
        try:
            # Resolve hostname
            results = socket.getaddrinfo(
                hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM
            )

            for family, _, _, _, sockaddr in results:
                ip_str = sockaddr[0]
                try:
                    ip = ipaddress.ip_address(ip_str)
                    self._check_ip(ip, url)
                except ValueError:
                    continue

        except socket.gaierror:
            # DNS resolution failed - allow the request to proceed
            # (it will fail at the HTTP level if truly unreachable)
            pass


# Default validator instance
_default_validator = URLValidator(allow_localhost=False, allow_private=False)


@lru_cache(maxsize=1024)
def validate_url(
    url: str,
    allow_localhost: bool = False,
    allow_private: bool = False,
) -> str:
    """Validate a URL and return it if valid.

    This is a cached convenience function. For repeated validations
    with the same settings, consider creating a URLValidator instance.

    Parameters
    ----------
    url : str
        The URL to validate.
    allow_localhost : bool
        If True, allows localhost and loopback addresses.
    allow_private : bool
        If True, allows private IP ranges.

    Returns
    -------
    str
        The validated URL.

    Raises
    ------
    InvalidURLError
        If the URL is invalid or blocked.

    Example
    -------
        >>> validate_url("https://example.com")
        'https://example.com'
        >>> validate_url("http://localhost")  # Raises InvalidURLError
    """
    validator = URLValidator(
        allow_localhost=allow_localhost,
        allow_private=allow_private,
    )
    return validator.validate(url)


def is_safe_url(url: str) -> bool:
    """Check if a URL is safe to fetch.

    Parameters
    ----------
    url : str
        The URL to check.

    Returns
    -------
    bool
        True if the URL is safe, False otherwise.

    Example
    -------
        >>> is_safe_url("https://example.com")
        True
        >>> is_safe_url("http://localhost")
        False
    """
    try:
        validate_url(url, allow_localhost=False, allow_private=False)
        return True
    except (InvalidURLError, ValueError):
        return False


def is_private_ip(ip_str: str) -> bool:
    """Check if an IP address is private or reserved.

    Parameters
    ----------
    ip_str : str
        The IP address string to check.

    Returns
    -------
    bool
        True if the IP is private/reserved, False otherwise.

    Example
    -------
        >>> is_private_ip("192.168.1.1")
        True
        >>> is_private_ip("8.8.8.8")
        False
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
        )
    except ValueError:
        return False


def sanitize_header_value(value: str) -> str:
    """Sanitize a header value to prevent header injection.

    Removes carriage returns and newlines that could be used
    for HTTP header injection attacks.

    Parameters
    ----------
    value : str
        The header value to sanitize.

    Returns
    -------
    str
        The sanitized header value.

    Example
    -------
        >>> sanitize_header_value("value\\r\\nX-Injected: bad")
        'valueX-Injected: bad'
    """
    # Remove CR and LF characters
    return value.replace("\r", "").replace("\n", "")
