"""Metrics and statistics collection for EasyScrape.

This module provides tools for collecting and analyzing scraping metrics,
including request timing, success rates, and error tracking.

Example
-------
    from easyscrape.stats import Collector, get_metrics_collector

    collector = get_metrics_collector()
    metrics = collector.start("https://example.com", "GET")
    # ... perform request ...
    metrics.complete(200, 1024)
    collector.finish(metrics)

    print(collector.summary())
"""
from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock
from typing import Any, Callable, Final
from urllib.parse import urlparse

__all__: Final[tuple[str, ...]] = (
    "RequestMetrics",
    "DomainStats",
    "StatsHook",
    "LogHook",
    "CallbackHook",
    "Collector",
    "get_metrics_collector",
)


class RequestMetrics:
    """Metrics for a single request.

    Parameters
    ----------
    url : str
        The request URL.
    method : str
        HTTP method.
    start_time : float
        Request start time (monotonic).
    """

    __slots__ = (
        "url", "method", "start_time", "end_time",
        "status_code", "bytes_received", "error", "cached",
    )

    def __init__(
        self,
        url: str,
        method: str,
        start_time: float,
        error: str | None = None,
    ) -> None:
        self.url = url
        self.method = method
        self.start_time = start_time
        self.end_time: float | None = None
        self.status_code: int | None = None
        self.bytes_received: int = 0
        self.error = error
        self.cached = False

    def complete(
        self,
        status_code: int,
        bytes_received: int = 0,
        cached: bool = False,
    ) -> None:
        """Mark request as complete.

        Parameters
        ----------
        status_code : int
            HTTP status code.
        bytes_received : int
            Response size in bytes.
        cached : bool
            Whether response was from cache.
        """
        self.end_time = time.monotonic()
        self.status_code = status_code
        self.bytes_received = bytes_received
        self.cached = cached

    def fail(self, error: str) -> None:
        """Mark request as failed.

        Parameters
        ----------
        error : str
            Error message.
        """
        self.end_time = time.monotonic()
        self.error = error

    @property
    def success(self) -> bool:
        """Whether the request was successful."""
        return self.error is None and self.status_code is not None and self.status_code < 400

    @property
    def duration_ms(self) -> float:
        """Request duration in milliseconds."""
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time) * 1000


class DomainStats:
    """Aggregated statistics for a domain."""

    __slots__ = (
        "total_requests", "ok", "failed", "total_bytes",
        "total_ms", "cache_hits",
    )

    def __init__(self) -> None:
        self.total_requests = 0
        self.ok = 0
        self.failed = 0
        self.total_bytes = 0
        self.total_ms = 0.0
        self.cache_hits = 0

    def record(self, metrics: RequestMetrics) -> None:
        """Record metrics for a request.

        Parameters
        ----------
        metrics : RequestMetrics
            The request metrics to record.
        """
        self.total_requests += 1
        self.total_ms += metrics.duration_ms
        self.total_bytes += metrics.bytes_received

        if metrics.cached:
            self.cache_hits += 1

        if metrics.success:
            self.ok += 1
        else:
            self.failed += 1

    @property
    def avg_ms(self) -> float:
        """Average request duration in milliseconds."""
        if self.total_requests == 0:
            return 0.0
        return self.total_ms / self.total_requests

    @property
    def success_rate(self) -> float:
        """Success rate as a fraction (0.0 to 1.0)."""
        if self.total_requests == 0:
            return 0.0
        return self.ok / self.total_requests


class StatsHook:
    """Base class for statistics hooks.

    Subclass this to receive notifications about requests.
    """

    def on_start(self, url: str, method: str) -> None:
        """Called when a request starts."""
        pass

    def on_complete(self, metrics: RequestMetrics) -> None:
        """Called when a request completes successfully."""
        pass

    def on_error(self, metrics: RequestMetrics) -> None:
        """Called when a request fails."""
        pass


class LogHook(StatsHook):
    """Hook that logs request metrics."""

    def on_start(self, url: str, method: str) -> None:
        """Log request start."""
        pass  # Could add logging here

    def on_complete(self, metrics: RequestMetrics) -> None:
        """Log request completion."""
        pass  # Could add logging here

    def on_error(self, metrics: RequestMetrics) -> None:
        """Log request error."""
        pass  # Could add logging here


class CallbackHook(StatsHook):
    """Hook that calls user-provided callbacks.

    Parameters
    ----------
    on_start : callable, optional
        Called with (url, method) when request starts.
    on_complete : callable, optional
        Called with (metrics) when request completes.
    on_error : callable, optional
        Called with (metrics) when request fails.
    """

    def __init__(
        self,
        on_start: Callable[[str, str], None] | None = None,
        on_complete: Callable[[RequestMetrics], None] | None = None,
        on_error: Callable[[RequestMetrics], None] | None = None,
    ) -> None:
        self._on_start = on_start
        self._on_complete = on_complete
        self._on_error = on_error

    def on_start(self, url: str, method: str) -> None:
        if self._on_start:
            try:
                self._on_start(url, method)
            except Exception:
                pass

    def on_complete(self, metrics: RequestMetrics) -> None:
        if self._on_complete:
            try:
                self._on_complete(metrics)
            except Exception:
                pass

    def on_error(self, metrics: RequestMetrics) -> None:
        if self._on_error:
            try:
                self._on_error(metrics)
            except Exception:
                pass


class Collector:
    """Collects and aggregates request metrics.

    Thread-safe collector for tracking request statistics.
    """

    def __init__(self, max_recent: int = 100) -> None:
        self._domain_stats: dict[str, DomainStats] = defaultdict(DomainStats)
        self._recent: list[dict[str, Any]] = []
        self._max_recent = max_recent
        self._hooks: list[StatsHook] = []
        self._lock = Lock()
        self._start_time = time.monotonic()

    def add_hook(self, hook: StatsHook) -> None:
        """Add a statistics hook."""
        self._hooks.append(hook)

    def remove_hook(self, hook: StatsHook) -> None:
        """Remove a statistics hook."""
        if hook in self._hooks:
            self._hooks.remove(hook)

    def start(self, url: str, method: str) -> RequestMetrics:
        """Start tracking a request.

        Parameters
        ----------
        url : str
            Request URL.
        method : str
            HTTP method.

        Returns
        -------
        RequestMetrics
            Metrics object to track the request.
        """
        metrics = RequestMetrics(url, method, time.monotonic())
        for hook in self._hooks:
            try:
                hook.on_start(url, method)
            except Exception:
                pass
        return metrics

    def finish(self, metrics: RequestMetrics) -> None:
        """Finish tracking a request.

        Parameters
        ----------
        metrics : RequestMetrics
            The metrics object from start().
        """
        # Extract domain
        try:
            domain = urlparse(metrics.url).netloc or "unknown"
        except Exception:
            domain = "unknown"

        with self._lock:
            self._domain_stats[domain].record(metrics)

            # Store in recent with fields expected by dashboard
            self._recent.append({
                "url": metrics.url,
                "method": metrics.method,
                "status": metrics.status_code,
                "duration_ms": metrics.duration_ms,
                "ms": metrics.duration_ms,  # Alias for dashboard
                "bytes": metrics.bytes_received,
                "error": metrics.error,
                "cached": metrics.cached,
                "ok": metrics.success,  # For dashboard
            })
            if len(self._recent) > self._max_recent:
                self._recent.pop(0)

        # Notify hooks
        for hook in self._hooks:
            try:
                if metrics.success:
                    hook.on_complete(metrics)
                else:
                    hook.on_error(metrics)
            except Exception:
                pass

    def domain_stats(self, domain: str | None = None) -> dict[str, Any]:
        """Get statistics for a domain or all domains.

        Parameters
        ----------
        domain : str, optional
            Domain to get stats for. If None, returns all domains.

        Returns
        -------
        dict
            Statistics dictionary.
        """
        with self._lock:
            if domain:
                stats = self._domain_stats.get(domain)
                if stats is None:
                    return {}
                return {
                    "total": stats.total_requests,
                    "ok": stats.ok,
                    "failed": stats.failed,
                    "avg_ms": stats.avg_ms,
                    "success_rate": stats.success_rate,
                    "total_bytes": stats.total_bytes,
                    "cache_hits": stats.cache_hits,
                }
            else:
                return {
                    d: {
                        "total": s.total_requests,
                        "ok": s.ok,
                        "failed": s.failed,
                        "avg_ms": s.avg_ms,
                        "success_rate": s.success_rate,
                    }
                    for d, s in self._domain_stats.items()
                }

    def recent(self, n: int = 10) -> list[dict[str, Any]]:
        """Get recent request metrics.

        Parameters
        ----------
        n : int
            Number of recent requests to return.

        Returns
        -------
        list
            List of recent request dictionaries.
        """
        with self._lock:
            return self._recent[-n:]

    def summary(self) -> dict[str, Any]:
        """Get overall summary statistics.

        Returns
        -------
        dict
            Summary statistics with keys expected by dashboard:
            - requests: total request count
            - successful: successful request count
            - failed: failed request count
            - success_rate: success rate (0.0 to 1.0)
            - bytes: total bytes received
            - cache_hits: number of cache hits
            - cache_rate: cache hit rate (0.0 to 1.0)
            - uptime_s: seconds since collector started
            - domains: number of unique domains
            - total_requests: alias for requests
            - total_bytes: alias for bytes
        """
        with self._lock:
            total = sum(s.total_requests for s in self._domain_stats.values())
            ok = sum(s.ok for s in self._domain_stats.values())
            failed = sum(s.failed for s in self._domain_stats.values())
            total_bytes = sum(s.total_bytes for s in self._domain_stats.values())
            cache_hits = sum(s.cache_hits for s in self._domain_stats.values())
            uptime = time.monotonic() - self._start_time

            return {
                # Keys expected by dashboard
                "requests": total,
                "successful": ok,
                "failed": failed,
                "success_rate": ok / total if total > 0 else 0.0,
                "bytes": total_bytes,
                "cache_hits": cache_hits,
                "cache_rate": cache_hits / total if total > 0 else 0.0,
                "uptime_s": uptime,
                "domains": len(self._domain_stats),
                # Backward compatibility aliases
                "total_requests": total,
                "total_bytes": total_bytes,
            }

    def reset(self) -> None:
        """Reset all statistics."""
        with self._lock:
            self._domain_stats.clear()
            self._recent.clear()
            self._start_time = time.monotonic()


# Singleton collector
_default_collector: Collector | None = None
_collector_lock = Lock()


def get_metrics_collector() -> Collector:
    """Get the default metrics collector singleton.

    Returns
    -------
    Collector
        The default collector instance.
    """
    global _default_collector
    with _collector_lock:
        if _default_collector is None:
            _default_collector = Collector()
        return _default_collector
