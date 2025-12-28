"""Connection Pool Management.

This module manages HTTP client connection pools for efficient connection
reuse across multiple requests.
"""
from __future__ import annotations

import contextlib
import time
from dataclasses import dataclass
from threading import Lock
from typing import Any, Final
from urllib.parse import urlparse

import httpx

from .constants import (
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_KEEPALIVE_EXPIRY,
    DEFAULT_MAX_CONNECTIONS,
    DEFAULT_MAX_KEEPALIVE_CONNECTIONS,
    DEFAULT_TIMEOUT,
)
from .log import get_logger

__all__: Final[tuple[str, ...]] = (
    "PoolConfig",
    "PoolStats",
    "DomainPool",
    "ConnectionPoolManager",
    "get_pool_manager",
    "close_all_pools",
)

_log = get_logger(__name__)


def _get_time() -> float:
    """Get current time using highest resolution timer available."""
    # Use perf_counter for highest resolution on all platforms
    return time.perf_counter()


@dataclass
class PoolConfig:
    """Configuration for connection pool behaviour."""

    max_connections: int = DEFAULT_MAX_CONNECTIONS
    max_keepalive_connections: int = DEFAULT_MAX_KEEPALIVE_CONNECTIONS
    keepalive_expiry: float = DEFAULT_KEEPALIVE_EXPIRY
    connect_timeout: float = DEFAULT_CONNECT_TIMEOUT
    read_timeout: float = DEFAULT_TIMEOUT
    retries: int = 0
    http2: bool = True

    def __post_init__(self) -> None:
        """Validate and clamp configuration values to safe ranges."""
        self.max_connections = max(1, min(1000, self.max_connections))
        self.max_keepalive_connections = max(
            0, min(self.max_connections, self.max_keepalive_connections)
        )
        self.keepalive_expiry = max(1.0, min(300.0, self.keepalive_expiry))


class PoolStats:
    """Thread-safe statistics tracker for connection pool usage."""

    __slots__ = (
        "_lock",
        "_connections_created",
        "_connections_reused",
        "_connections_closed",
        "_active_connections",
        "_peak_connections",
    )

    def __init__(self) -> None:
        """Initialise all counters to zero."""
        self._lock: Final[Lock] = Lock()
        self._connections_created = 0
        self._connections_reused = 0
        self._connections_closed = 0
        self._active_connections = 0
        self._peak_connections = 0

    def connection_created(self) -> None:
        """Record a new connection being created."""
        with self._lock:
            self._connections_created += 1
            self._active_connections += 1
            self._peak_connections = max(self._peak_connections, self._active_connections)

    def connection_reused(self) -> None:
        """Record an existing connection being reused."""
        with self._lock:
            self._connections_reused += 1

    def connection_closed(self) -> None:
        """Record a connection being closed."""
        with self._lock:
            self._connections_closed += 1
            self._active_connections = max(0, self._active_connections - 1)

    def get_stats(self) -> dict[str, int]:
        """Get current statistics as a dictionary."""
        with self._lock:
            return {
                "created": self._connections_created,
                "reused": self._connections_reused,
                "closed": self._connections_closed,
                "active": self._active_connections,
                "peak": self._peak_connections,
            }

    def reset(self) -> None:
        """Reset counters (keeps active/peak for accuracy)."""
        with self._lock:
            self._connections_created = 0
            self._connections_reused = 0
            self._connections_closed = 0


class DomainPool:
    """Manages HTTP client connections for a single domain."""

    __slots__ = (
        "_domain",
        "_config",
        "_client",
        "_async_client",
        "_lock",
        "_created_at",
        "_last_used",
        "_request_count",
    )

    def __init__(self, domain: str, config: PoolConfig) -> None:
        """Initialise pool for a domain with given configuration."""
        self._domain = domain
        self._config = config
        self._client: httpx.Client | None = None
        self._async_client: httpx.AsyncClient | None = None
        self._lock: Final[Lock] = Lock()
        # Use high-resolution timer for accurate idle time tracking
        self._created_at = _get_time()
        self._last_used = self._created_at
        self._request_count = 0

        _log.debug("domain pool created: %s", domain)

    @property
    def domain(self) -> str:
        """The domain this pool serves."""
        return self._domain

    @property
    def request_count(self) -> int:
        """Total requests made through this pool."""
        return self._request_count

    @property
    def idle_time(self) -> float:
        """Seconds since this pool was last used."""
        return _get_time() - self._last_used

    def _create_transport(self) -> httpx.HTTPTransport:
        """Create HTTP transport with configured retry and HTTP/2 settings."""
        return httpx.HTTPTransport(
            retries=self._config.retries,
            http2=self._config.http2,
        )

    def _create_limits(self) -> httpx.Limits:
        """Create connection limits from configuration."""
        return httpx.Limits(
            max_connections=self._config.max_connections,
            max_keepalive_connections=self._config.max_keepalive_connections,
            keepalive_expiry=self._config.keepalive_expiry,
        )

    def get_client(self) -> httpx.Client:
        """Get or create the synchronous HTTP client."""
        with self._lock:
            if self._client is None or self._client.is_closed:
                self._client = httpx.Client(
                    timeout=httpx.Timeout(
                        self._config.read_timeout,
                        connect=self._config.connect_timeout,
                    ),
                    limits=self._create_limits(),
                    transport=self._create_transport(),
                )
                _log.debug("client created for %s", self._domain)

            self._last_used = _get_time()
            self._request_count += 1
            return self._client

    async def get_async_client(self) -> httpx.AsyncClient:
        """Get or create the asynchronous HTTP client."""
        with self._lock:
            if self._async_client is None or self._async_client.is_closed:
                self._async_client = httpx.AsyncClient(
                    timeout=httpx.Timeout(
                        self._config.read_timeout,
                        connect=self._config.connect_timeout,
                    ),
                    limits=self._create_limits(),
                    http2=self._config.http2,
                )
                _log.debug("async client created for %s", self._domain)

            self._last_used = _get_time()
            self._request_count += 1
            return self._async_client

    def close(self) -> None:
        """Close all clients (sync method)."""
        with self._lock:
            if self._client is not None:
                with contextlib.suppress(Exception):
                    self._client.close()
                self._client = None

            if self._async_client is not None:
                try:
                    import asyncio
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(self._async_client.aclose())
                    except RuntimeError:
                        asyncio.run(self._async_client.aclose())
                except Exception:
                    pass
                self._async_client = None

            _log.debug("domain pool closed: %s", self._domain)

    async def aclose(self) -> None:
        """Close all clients (async method)."""
        with self._lock:
            if self._async_client is not None:
                with contextlib.suppress(Exception):
                    await self._async_client.aclose()
                self._async_client = None

            if self._client is not None:
                with contextlib.suppress(Exception):
                    self._client.close()
                self._client = None


class ConnectionPoolManager:
    """Manages connection pools across multiple domains."""

    __slots__ = (
        "_config",
        "_pools",
        "_lock",
        "_max_idle_time",
        "_stats",
        "_cleanup_interval",
        "_last_cleanup",
    )

    def __init__(
        self,
        config: PoolConfig | None = None,
        max_idle_time: float = 300.0,
    ) -> None:
        """Initialise the pool manager with configuration."""
        self._config = config or PoolConfig()
        self._pools: dict[str, DomainPool] = {}
        self._lock: Final[Lock] = Lock()
        self._max_idle_time = max_idle_time
        self._stats = PoolStats()
        self._cleanup_interval = 60.0
        self._last_cleanup = _get_time()

        _log.debug("connection pool manager initialised")

    @property
    def stats(self) -> PoolStats:
        """The statistics tracker for this manager."""
        return self._stats

    def _extract_domain(self, url: str) -> str:
        """Extract scheme://netloc from a URL for pool key."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else url

    def _maybe_cleanup(self) -> None:
        """Cleanup idle pools if enough time has passed."""
        now = _get_time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        self._last_cleanup = now

        to_remove = []
        for domain, pool in self._pools.items():
            if pool.idle_time > self._max_idle_time:
                to_remove.append(domain)

        for domain in to_remove:
            _log.debug("removing idle pool: %s", domain)
            pool = self._pools.pop(domain)
            pool.close()
            self._stats.connection_closed()

    def get_pool(self, url: str) -> DomainPool:
        """Get or create a pool for the URL's domain."""
        domain = self._extract_domain(url)

        with self._lock:
            self._maybe_cleanup()

            if domain not in self._pools:
                self._pools[domain] = DomainPool(domain, self._config)
                self._stats.connection_created()
            else:
                self._stats.connection_reused()

            return self._pools[domain]

    def get_client(self, url: str) -> httpx.Client:
        """Get a synchronous HTTP client for the URL's domain."""
        return self.get_pool(url).get_client()

    async def get_async_client(self, url: str) -> httpx.AsyncClient:
        """Get an asynchronous HTTP client for the URL's domain."""
        return await self.get_pool(url).get_async_client()

    def close_pool(self, url: str) -> None:
        """Close the pool for a specific domain."""
        domain = self._extract_domain(url)

        with self._lock:
            pool = self._pools.pop(domain, None)
            if pool:
                pool.close()
                self._stats.connection_closed()

    def close_all(self) -> None:
        """Close all connection pools."""
        with self._lock:
            for pool in self._pools.values():
                pool.close()
                self._stats.connection_closed()
            self._pools.clear()
            _log.debug("all pools closed")

    async def aclose_all(self) -> None:
        """Async close all connection pools."""
        with self._lock:
            for pool in self._pools.values():
                await pool.aclose()
                self._stats.connection_closed()
            self._pools.clear()

    def get_pool_stats(self) -> dict[str, Any]:
        """Get comprehensive statistics for all pools."""
        with self._lock:
            return {
                "pool_count": len(self._pools),
                "pools": {
                    domain: {
                        "request_count": pool.request_count,
                        "idle_seconds": round(pool.idle_time, 2),
                    }
                    for domain, pool in self._pools.items()
                },
                "connection_stats": self._stats.get_stats(),
            }

    def __enter__(self) -> ConnectionPoolManager:
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit - closes all pools."""
        self.close_all()

    async def __aenter__(self) -> ConnectionPoolManager:
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit - closes all pools."""
        await self.aclose_all()


# Global pool manager singleton
_pool_manager: ConnectionPoolManager | None = None
_pool_lock: Final[Lock] = Lock()


def get_pool_manager(config: PoolConfig | None = None) -> ConnectionPoolManager:
    """Get or create the global connection pool manager."""
    global _pool_manager

    with _pool_lock:
        if _pool_manager is None:
            _pool_manager = ConnectionPoolManager(config)
        return _pool_manager


def close_all_pools() -> None:
    """Close all global connection pools and reset the manager."""
    global _pool_manager

    with _pool_lock:
        if _pool_manager is not None:
            _pool_manager.close_all()
            _pool_manager = None
