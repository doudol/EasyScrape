"""Middleware and hooks for request/response processing.

This module provides a middleware system for intercepting and modifying
requests and responses during scraping.

Example
-------
    from easyscrape.hooks import MiddlewareChain, HeadersMiddleware

    chain = MiddlewareChain()
    chain.add(HeadersMiddleware({"X-Custom": "value"}))

    ctx = RequestContext(url="https://example.com")
    ctx = chain.process_request(ctx)
"""
from __future__ import annotations

import random
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Final
from urllib.parse import urlparse

__all__: Final[tuple[str, ...]] = (
    "RequestContext",
    "ResponseContext",
    "Middleware",
    "MiddlewareChain",
    "LoggingMiddleware",
    "HeadersMiddleware",
    "TimingMiddleware",
    "RetryCountMiddleware",
    "UserAgentRotationMiddleware",
    "ThrottleMiddleware",
    "CacheMiddleware",
    "FilterMiddleware",
)


class RequestContext:
    """Context for a request being processed.

    Parameters
    ----------
    url : str
        The request URL.
    method : str
        HTTP method.
    headers : dict, optional
        Request headers.
    """

    __slots__ = ("url", "method", "headers", "meta", "start_time")

    def __init__(
        self,
        url: str,
        method: str = "GET",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.url = url
        self.method = method
        self.headers = headers or {}
        self.meta: dict[str, Any] = {}
        self.start_time = time.monotonic()

    @property
    def domain(self) -> str:
        """Extract domain from URL."""
        try:
            return urlparse(self.url).netloc
        except Exception:
            return ""

    def set_header(self, name: str, value: str) -> None:
        """Set a request header."""
        self.headers[name] = value

    def get_meta(self, key: str, default: Any = None) -> Any:
        """Get metadata value."""
        return self.meta.get(key, default)

    def set_meta(self, key: str, value: Any) -> None:
        """Set metadata value."""
        self.meta[key] = value


class ResponseContext:
    """Context for a response being processed.

    Parameters
    ----------
    request : RequestContext
        The original request context.
    status_code : int
        HTTP status code.
    content : bytes
        Response body.
    headers : dict, optional
        Response headers.
    """

    __slots__ = ("request", "status_code", "content", "headers", "end_time")

    def __init__(
        self,
        request: RequestContext,
        status_code: int,
        content: bytes = b"",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.request = request
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}
        self.end_time = time.monotonic()

    @property
    def ok(self) -> bool:
        """Whether the response was successful."""
        return 200 <= self.status_code < 400

    @property
    def text(self) -> str:
        """Decode content as text."""
        return self.content.decode("utf-8", errors="replace")

    @property
    def duration_ms(self) -> float:
        """Request duration in milliseconds."""
        return (self.end_time - self.request.start_time) * 1000


class Middleware(ABC):
    """Base class for middleware.

    Subclass this to create custom middleware.
    """

    def process_request(self, ctx: RequestContext) -> RequestContext:
        """Process a request before it's sent.

        Parameters
        ----------
        ctx : RequestContext
            The request context.

        Returns
        -------
        RequestContext
            The (possibly modified) context.
        """
        return ctx

    def process_response(self, ctx: ResponseContext) -> ResponseContext:
        """Process a response after it's received.

        Parameters
        ----------
        ctx : ResponseContext
            The response context.

        Returns
        -------
        ResponseContext
            The (possibly modified) context.
        """
        return ctx

    def process_error(self, ctx: RequestContext, error: Exception) -> Exception | None:
        """Process an error.

        Parameters
        ----------
        ctx : RequestContext
            The request context.
        error : Exception
            The error that occurred.

        Returns
        -------
        Exception or None
            The error to raise, or None to suppress.
        """
        return error


class MiddlewareChain:
    """Chain of middleware to process requests and responses."""

    def __init__(self) -> None:
        self._middlewares: list[Middleware] = []

    def add(self, middleware: Middleware) -> MiddlewareChain:
        """Add middleware to the chain.

        Returns self for chaining.
        """
        self._middlewares.append(middleware)
        return self

    def remove(self, middleware: Middleware) -> None:
        """Remove middleware from the chain."""
        if middleware in self._middlewares:
            self._middlewares.remove(middleware)

    def clear(self) -> None:
        """Remove all middleware."""
        self._middlewares.clear()

    def __len__(self) -> int:
        return len(self._middlewares)

    def process_request(self, ctx: RequestContext) -> RequestContext:
        """Process request through all middleware."""
        for mw in self._middlewares:
            ctx = mw.process_request(ctx)
        return ctx

    def process_response(self, ctx: ResponseContext) -> ResponseContext:
        """Process response through all middleware (reverse order)."""
        for mw in reversed(self._middlewares):
            ctx = mw.process_response(ctx)
        return ctx

    def process_error(
        self,
        ctx: RequestContext,
        error: Exception,
    ) -> Exception | None:
        """Process error through all middleware."""
        for mw in reversed(self._middlewares):
            error = mw.process_error(ctx, error)
            if error is None:
                return None
        return error


class LoggingMiddleware(Middleware):
    """Middleware that logs requests and responses."""

    def process_request(self, ctx: RequestContext) -> RequestContext:
        return ctx

    def process_response(self, ctx: ResponseContext) -> ResponseContext:
        return ctx

    def process_error(self, ctx: RequestContext, error: Exception) -> Exception:
        return error


class HeadersMiddleware(Middleware):
    """Middleware that adds headers to requests.

    Parameters
    ----------
    headers : dict
        Headers to add.
    """

    def __init__(self, headers: dict[str, str]) -> None:
        self._headers = headers

    def process_request(self, ctx: RequestContext) -> RequestContext:
        for name, value in self._headers.items():
            ctx.set_header(name, value)
        return ctx


class TimingMiddleware(Middleware):
    """Middleware that tracks request timing."""

    def __init__(self) -> None:
        self._stats: dict[str, list[float]] = {}

    def process_response(self, ctx: ResponseContext) -> ResponseContext:
        domain = ctx.request.domain
        if domain not in self._stats:
            self._stats[domain] = []
        self._stats[domain].append(ctx.duration_ms)
        return ctx

    def get_stats(self, domain: str | None = None) -> dict[str, Any]:
        """Get timing statistics."""
        if domain:
            times = self._stats.get(domain, [])
            if not times:
                return {}
            return {
                "count": len(times),
                "avg_ms": sum(times) / len(times),
                "min_ms": min(times),
                "max_ms": max(times),
            }
        return dict(self._stats)


class RetryCountMiddleware(Middleware):
    """Middleware that tracks retry counts per domain."""

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    def process_request(self, ctx: RequestContext) -> RequestContext:
        domain = ctx.domain
        self._counts[domain] = self._counts.get(domain, 0) + 1
        return ctx

    def get_retry_counts(self) -> dict[str, int]:
        """Get retry counts by domain."""
        return dict(self._counts)


class UserAgentRotationMiddleware(Middleware):
    """Middleware that rotates User-Agent strings.

    Parameters
    ----------
    user_agents : list[str]
        List of User-Agent strings to rotate through.
    strategy : str
        Rotation strategy: "round-robin" or "random".
    """

    def __init__(
        self,
        user_agents: list[str],
        strategy: str = "round-robin",
    ) -> None:
        self._user_agents = user_agents
        self._strategy = strategy
        self._index = 0

    def process_request(self, ctx: RequestContext) -> RequestContext:
        if not self._user_agents:
            return ctx

        if self._strategy == "random":
            ua = random.choice(self._user_agents)
        else:  # round-robin
            ua = self._user_agents[self._index % len(self._user_agents)]
            self._index += 1

        ctx.set_header("User-Agent", ua)
        return ctx


class ThrottleMiddleware(Middleware):
    """Middleware that throttles requests per domain.

    Parameters
    ----------
    requests_per_second : float
        Maximum requests per second.
    """

    def __init__(self, requests_per_second: float) -> None:
        self._rps = requests_per_second
        self._last_request: dict[str, float] = {}

    def process_request(self, ctx: RequestContext) -> RequestContext:
        domain = ctx.domain
        now = time.monotonic()

        if domain in self._last_request:
            elapsed = now - self._last_request[domain]
            min_interval = 1.0 / self._rps
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)

        self._last_request[domain] = time.monotonic()
        return ctx


class CacheMiddleware(Middleware):
    """Middleware that caches responses."""

    def __init__(self, ttl: int = 3600) -> None:
        self._cache: dict[str, tuple[ResponseContext, float]] = {}
        self._ttl = ttl

    def _cache_key(self, ctx: RequestContext) -> str:
        """Generate cache key."""
        return f"{ctx.method}:{ctx.url}"

    def process_request(self, ctx: RequestContext) -> RequestContext:
        return ctx

    def process_response(self, ctx: ResponseContext) -> ResponseContext:
        key = self._cache_key(ctx.request)
        self._cache[key] = (ctx, time.monotonic() + self._ttl)
        return ctx


class FilterMiddleware(Middleware):
    """Middleware that filters requests by domain.

    Parameters
    ----------
    allow_domains : list[str], optional
        Only allow these domains.
    block_domains : list[str], optional
        Block these domains.
    url_filter : callable, optional
        Custom filter function.
    """

    def __init__(
        self,
        allow_domains: list[str] | None = None,
        block_domains: list[str] | None = None,
        url_filter: Callable[[str], bool] | None = None,
    ) -> None:
        self._allow = set(allow_domains) if allow_domains else None
        self._block = set(block_domains) if block_domains else set()
        self._filter = url_filter

    def process_request(self, ctx: RequestContext) -> RequestContext:
        domain = ctx.domain

        # Check block list
        if domain in self._block:
            ctx.set_meta("blocked", True)
            return ctx

        # Check allow list
        if self._allow is not None and domain not in self._allow:
            ctx.set_meta("blocked", True)
            return ctx

        # Check custom filter
        if self._filter and not self._filter(ctx.url):
            ctx.set_meta("blocked", True)
            return ctx

        return ctx
