"""Configuration for EasyScrape.

Provides the Config class for customizing scraping behavior.

Example
-------
    from easyscrape import Config, scrape

    config = Config(
        timeout=60.0,
        max_retries=5,
        rate_limit=1.0,
    )
    result = scrape(url, config=config)
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Final

__all__: Final[tuple[str, ...]] = (
    "Config",
    "ConfigBuilder",
    "StealthConfig",
    "DistributedConfig",
    "ComplianceConfig",
    "_safe_float",
    "_safe_int",
)


def _safe_float(env_var: str, default: str) -> float:
    """Safely parse float from environment variable."""
    try:
        return float(os.environ.get(env_var, default))
    except (ValueError, TypeError):
        return float(default)


def _safe_int(env_var: str, default: str) -> int:
    """Safely parse int from environment variable."""
    try:
        return int(os.environ.get(env_var, default))
    except (ValueError, TypeError):
        return int(default)


@dataclass
class Config:
    """Configuration options for scraping.

    Parameters
    ----------
    timeout : float
        Request timeout in seconds. Default 30.0.
    max_retries : int
        Maximum retry attempts. Default 3.
    max_redirects : int
        Maximum redirects to follow. Default 10.
    rate_limit : float
        Minimum seconds between requests to same domain. Default 0.0.
    cache_enabled : bool
        Enable response caching. Default True.
    cache_ttl : int
        Cache time-to-live in seconds. Default 3600.
    javascript : bool
        Enable JavaScript rendering. Default False.
    verify_ssl : bool
        Verify SSL certificates. Default True.
    headers : dict
        Default headers for all requests.
    proxies : list
        List of proxy URLs.
    proxy_mode : str
        Proxy selection mode: 'round-robin', 'random', 'sticky'. Default 'round-robin'.
    rotate_ua : bool
        Rotate User-Agent strings. Default False.
    respect_robots : bool
        Respect robots.txt rules. Default False.
    verbose : bool
        Enable verbose logging. Default False.
    allow_localhost : bool
        Allow requests to localhost/127.0.0.1. Default False.
    stealth_mode : bool
        Enable stealth mode for anti-bot evasion. Default False.
    use_stealth : bool
        Alias for stealth_mode. Default False.
    follow_redirects : bool
        Follow HTTP redirects. Default True.
    """

    timeout: float = 30.0
    max_retries: int = 3
    max_redirects: int = 10
    rate_limit: float = 0.0
    cache_enabled: bool = True
    cache_ttl: int = 3600
    javascript: bool = False
    verify_ssl: bool = True
    headers: dict[str, str] = field(default_factory=dict)
    proxies: list[str] = field(default_factory=list)
    proxy_mode: str = "round-robin"
    rotate_ua: bool = False
    respect_robots: bool = False
    verbose: bool = False
    allow_localhost: bool = False
    stealth_mode: bool = False
    use_stealth: bool = False
    follow_redirects: bool = True

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.timeout <= 0:
            self.timeout = 30.0
        if self.max_retries < 0:
            self.max_retries = 0
        if self.max_redirects < 0:
            self.max_redirects = 0
        if self.rate_limit < 0:
            self.rate_limit = 0.0
        if self.cache_ttl < 0:
            self.cache_ttl = 0
        # Sync stealth_mode and use_stealth
        if self.use_stealth and not self.stealth_mode:
            self.stealth_mode = True
        if self.stealth_mode and not self.use_stealth:
            self.use_stealth = True

    def with_timeout(self, timeout: float) -> Config:
        """Return new Config with updated timeout."""
        return Config(
            timeout=timeout,
            max_retries=self.max_retries,
            max_redirects=self.max_redirects,
            rate_limit=self.rate_limit,
            cache_enabled=self.cache_enabled,
            cache_ttl=self.cache_ttl,
            javascript=self.javascript,
            verify_ssl=self.verify_ssl,
            headers=dict(self.headers),
            proxies=list(self.proxies),
            proxy_mode=self.proxy_mode,
            rotate_ua=self.rotate_ua,
            respect_robots=self.respect_robots,
            verbose=self.verbose,
            allow_localhost=self.allow_localhost,
            stealth_mode=self.stealth_mode,
            use_stealth=self.use_stealth,
            follow_redirects=self.follow_redirects,
        )

    def with_retries(self, max_retries: int) -> Config:
        """Return new Config with updated max_retries."""
        return Config(
            timeout=self.timeout,
            max_retries=max_retries,
            max_redirects=self.max_redirects,
            rate_limit=self.rate_limit,
            cache_enabled=self.cache_enabled,
            cache_ttl=self.cache_ttl,
            javascript=self.javascript,
            verify_ssl=self.verify_ssl,
            headers=dict(self.headers),
            proxies=list(self.proxies),
            proxy_mode=self.proxy_mode,
            rotate_ua=self.rotate_ua,
            respect_robots=self.respect_robots,
            verbose=self.verbose,
            allow_localhost=self.allow_localhost,
            stealth_mode=self.stealth_mode,
            use_stealth=self.use_stealth,
            follow_redirects=self.follow_redirects,
        )

    def with_headers(self, headers: dict[str, str]) -> Config:
        """Return new Config with updated headers."""
        merged = {**self.headers, **headers}
        return Config(
            timeout=self.timeout,
            max_retries=self.max_retries,
            max_redirects=self.max_redirects,
            rate_limit=self.rate_limit,
            cache_enabled=self.cache_enabled,
            cache_ttl=self.cache_ttl,
            javascript=self.javascript,
            verify_ssl=self.verify_ssl,
            headers=merged,
            proxies=list(self.proxies),
            proxy_mode=self.proxy_mode,
            rotate_ua=self.rotate_ua,
            respect_robots=self.respect_robots,
            verbose=self.verbose,
            allow_localhost=self.allow_localhost,
            stealth_mode=self.stealth_mode,
            use_stealth=self.use_stealth,
            follow_redirects=self.follow_redirects,
        )

    def with_proxies(self, proxies: list[str]) -> Config:
        """Return new Config with updated proxies."""
        return Config(
            timeout=self.timeout,
            max_retries=self.max_retries,
            max_redirects=self.max_redirects,
            rate_limit=self.rate_limit,
            cache_enabled=self.cache_enabled,
            cache_ttl=self.cache_ttl,
            javascript=self.javascript,
            verify_ssl=self.verify_ssl,
            headers=dict(self.headers),
            proxies=list(proxies),
            proxy_mode=self.proxy_mode,
            rotate_ua=self.rotate_ua,
            respect_robots=self.respect_robots,
            verbose=self.verbose,
            allow_localhost=self.allow_localhost,
            stealth_mode=self.stealth_mode,
            use_stealth=self.use_stealth,
            follow_redirects=self.follow_redirects,
        )


@dataclass
class StealthConfig:
    """Configuration for stealth/anti-detection features.

    Parameters
    ----------
    use_stealth : bool
        Enable stealth mode. Default False.
    rotate_ua : bool
        Rotate User-Agent strings. Default True.
    random_delays : bool
        Add random delays between requests. Default False.
    delay_min : float
        Minimum delay in seconds. Default 0.5.
    delay_max : float
        Maximum delay in seconds. Default 2.0.
    fingerprint_evasion : bool
        Enable browser fingerprint evasion. Default False.
    """

    use_stealth: bool = False
    rotate_ua: bool = True
    random_delays: bool = False
    delay_min: float = 0.5
    delay_max: float = 2.0
    fingerprint_evasion: bool = False


@dataclass
class DistributedConfig:
    """Configuration for distributed scraping.

    Parameters
    ----------
    redis_url : str, optional
        Redis connection URL for distributed coordination.
    queue_name : str
        Name of the task queue. Default 'easyscrape'.
    worker_id : str, optional
        Unique identifier for this worker.
    max_workers : int
        Maximum number of concurrent workers. Default 4.
    """

    redis_url: str | None = None
    queue_name: str = "easyscrape"
    worker_id: str | None = None
    max_workers: int = 4


@dataclass
class ComplianceConfig:
    """Configuration for compliance and ethical scraping.

    Parameters
    ----------
    respect_robots : bool
        Respect robots.txt rules. Default False.
    max_requests_per_domain : int
        Maximum requests per domain per minute. Default 60.
    identify_as_bot : bool
        Identify as a bot in User-Agent. Default False.
    contact_email : str, optional
        Contact email for bot identification.
    """

    respect_robots: bool = False
    max_requests_per_domain: int = 60
    identify_as_bot: bool = False
    contact_email: str | None = None


class ConfigBuilder:
    """Fluent builder for Config objects.

    Example
    -------
        config = (
            ConfigBuilder()
            .timeout(60.0)
            .retries(5)
            .rate_limit(1.0)
            .build()
        )
    """

    def __init__(self) -> None:
        self._timeout: float = 30.0
        self._max_retries: int = 3
        self._max_redirects: int = 10
        self._rate_limit: float = 0.0
        self._cache_enabled: bool = True
        self._cache_ttl: int = 3600
        self._javascript: bool = False
        self._verify_ssl: bool = True
        self._headers: dict[str, str] = {}
        self._proxies: list[str] = []
        self._proxy_mode: str = "round-robin"
        self._rotate_ua: bool = False
        self._respect_robots: bool = False
        self._verbose: bool = False
        self._allow_localhost: bool = False
        self._stealth_mode: bool = False
        self._use_stealth: bool = False
        self._follow_redirects: bool = True

    def timeout(self, seconds: float) -> ConfigBuilder:
        """Set timeout."""
        self._timeout = seconds
        return self

    def retries(self, count: int) -> ConfigBuilder:
        """Set max retries."""
        self._max_retries = count
        return self

    def redirects(self, count: int) -> ConfigBuilder:
        """Set max redirects."""
        self._max_redirects = count
        return self

    def rate_limit(self, seconds: float) -> ConfigBuilder:
        """Set rate limit."""
        self._rate_limit = seconds
        return self

    def cache(self, enabled: bool = True, ttl: int = 3600) -> ConfigBuilder:
        """Configure caching."""
        self._cache_enabled = enabled
        self._cache_ttl = ttl
        return self

    def javascript(self, enabled: bool = True) -> ConfigBuilder:
        """Enable JavaScript rendering."""
        self._javascript = enabled
        return self

    def verify_ssl(self, enabled: bool = True) -> ConfigBuilder:
        """Set SSL verification."""
        self._verify_ssl = enabled
        return self

    def header(self, name: str, value: str) -> ConfigBuilder:
        """Add a header."""
        self._headers[name] = value
        return self

    def headers(self, headers: dict[str, str]) -> ConfigBuilder:
        """Add multiple headers."""
        self._headers.update(headers)
        return self

    def proxy(self, url: str) -> ConfigBuilder:
        """Add a proxy."""
        self._proxies.append(url)
        return self

    def proxies(self, urls: list[str]) -> ConfigBuilder:
        """Add multiple proxies."""
        self._proxies.extend(urls)
        return self

    def proxy_mode(self, mode: str) -> ConfigBuilder:
        """Set proxy selection mode."""
        self._proxy_mode = mode
        return self

    def rotate_user_agent(self, enabled: bool = True) -> ConfigBuilder:
        """Enable User-Agent rotation."""
        self._rotate_ua = enabled
        return self

    def respect_robots(self, enabled: bool = True) -> ConfigBuilder:
        """Enable robots.txt respect."""
        self._respect_robots = enabled
        return self

    def verbose(self, enabled: bool = True) -> ConfigBuilder:
        """Enable verbose logging."""
        self._verbose = enabled
        return self

    def allow_localhost(self, enabled: bool = True) -> ConfigBuilder:
        """Allow localhost requests."""
        self._allow_localhost = enabled
        return self

    def stealth_mode(self, enabled: bool = True) -> ConfigBuilder:
        """Enable stealth mode."""
        self._stealth_mode = enabled
        self._use_stealth = enabled
        return self

    def follow_redirects(self, enabled: bool = True) -> ConfigBuilder:
        """Enable redirect following."""
        self._follow_redirects = enabled
        return self

    def build(self) -> Config:
        """Build the Config object."""
        return Config(
            timeout=self._timeout,
            max_retries=self._max_retries,
            max_redirects=self._max_redirects,
            rate_limit=self._rate_limit,
            cache_enabled=self._cache_enabled,
            cache_ttl=self._cache_ttl,
            javascript=self._javascript,
            verify_ssl=self._verify_ssl,
            headers=dict(self._headers),
            proxies=list(self._proxies),
            proxy_mode=self._proxy_mode,
            rotate_ua=self._rotate_ua,
            respect_robots=self._respect_robots,
            verbose=self._verbose,
            allow_localhost=self._allow_localhost,
            stealth_mode=self._stealth_mode,
            use_stealth=self._use_stealth,
            follow_redirects=self._follow_redirects,
        )
