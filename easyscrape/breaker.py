"""Circuit breaker for fault tolerance.

Architecture
------------
The circuit breaker is a stability pattern that prevents cascading failures.
When a service is failing, continuing to hammer it:
- Wastes resources (your requests, their server capacity)
- Delays recovery (overloaded servers need breathing room)
- Causes cascading failures (your app blocks waiting for timeouts)

The circuit breaker "trips" after repeated failures, fast-failing subsequent
requests without attempting the actual operation.

State Machine
-------------
```
    ┌─────────────────────────────────────────────────────────────┐
    │                                                             │
    │  ┌──────────┐      failures > threshold      ┌──────────┐  │
    │  │  CLOSED  │ ─────────────────────────────► │   OPEN   │  │
    │  │ (normal) │                                │  (fail)  │  │
    │  └──────────┘                                └──────────┘  │
    │       ▲                                           │        │
    │       │                                           │        │
    │       │ successes in                    timeout   │        │
    │       │ half-open                       elapsed   │        │
    │       │                                           ▼        │
    │       │                                    ┌───────────┐   │
    │       └─────────────────────────────────── │ HALF-OPEN │   │
    │                                            │  (probe)  │   │
    │                                            └───────────┘   │
    │                                                  │         │
    │                         failure in half-open    │         │
    │                         ───────────────────────►│         │
    │                                                             │
    └─────────────────────────────────────────────────────────────┘
```

States Explained
----------------
1. **CLOSED** (normal operation):
   - Requests flow through normally
   - Failures are counted
   - Trips to OPEN if threshold exceeded

2. **OPEN** (circuit tripped):
   - All requests fail immediately (no network call)
   - Fast-fail with CircuitBreakerOpen exception
   - Waits for recovery_timeout before trying again

3. **HALF-OPEN** (testing recovery):
   - Allows limited probe requests through
   - If probes succeed: return to CLOSED
   - If probes fail: return to OPEN

Why This Pattern?
-----------------
Without circuit breaker:
- Service goes down
- Your requests pile up, waiting for timeouts
- Your app slows down, users frustrated
- You keep hammering the dying service
- Service has no chance to recover

With circuit breaker:
- Service goes down
- After N failures, circuit trips
- Subsequent requests fail instantly (no wait)
- Your app stays responsive (with graceful degradation)
- Service gets breathing room to recover
- After timeout, we probe with limited requests
- If healthy, resume normal operation

Example
-------
    breaker = Breaker("api.example.com", CircuitBreakerConfig(
        failure_threshold=5,      # Trip after 5 consecutive failures
        recovery_timeout=30.0,    # Wait 30s before probing
        half_open_max_calls=3,    # Allow 3 probe requests
    ))

    def call_api():
        return breaker.execute(lambda: httpx.get("https://api.example.com"))

    try:
        response = call_api()
    except CircuitBreakerOpen:
        # Use cached data or show error
        pass
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from threading import Lock
from typing import Callable, Final, TypeVar
from urllib.parse import urlparse

from .constants import (
    CIRCUIT_BREAKER_FAILURE_THRESHOLD,
    CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS,
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
)
from .exceptions import CircuitBreakerOpen
from .log import get_logger

__all__: Final[tuple[str, ...]] = (
    "CircuitState",
    "CircuitStats",
    "CircuitBreakerConfig",
    "Breaker",
    "CircuitBreaker",
    "DomainBreakers",
    "DomainCircuitBreakers",
    "get_domain_breakers",
)

_log = get_logger(__name__)
T = TypeVar("T")


class CircuitState(Enum):
    """Enumeration of circuit breaker states.

    The circuit breaker is a state machine with three states:
    - CLOSED: Normal operation, requests flow through
    - OPEN: Circuit tripped, requests fail immediately
    - HALF_OPEN: Testing recovery, limited requests allowed
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitStats:
    """Statistics for monitoring circuit breaker health.

    Tracks both instantaneous and lifetime metrics:
    - **Instantaneous**: Current failure streak, recent success rate
    - **Lifetime**: Total requests and failures for monitoring

    The consecutive counters are used for trip decisions:
    - consecutive_failures >= threshold → trip to OPEN
    - consecutive_successes in half-open → return to CLOSED
    """

    failures: int = 0
    successes: int = 0
    last_failure_time: float = 0.0
    last_success_time: float = 0.0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    total_requests: int = 0
    total_failures: int = 0

    def record_success(self) -> None:
        """Record a successful request.

        Resets the consecutive failure counter, incrementing the
        consecutive success counter for half-open recovery tracking.
        """
        self.successes += 1
        self.consecutive_successes += 1
        self.consecutive_failures = 0
        self.last_success_time = time.monotonic()
        self.total_requests += 1

    def record_failure(self) -> None:
        """Record a failed request.

        Increments consecutive failures (for trip decision) and
        resets the success counter.
        """
        self.failures += 1
        self.consecutive_failures += 1
        self.consecutive_successes = 0
        self.last_failure_time = time.monotonic()
        self.total_requests += 1
        self.total_failures += 1

    def reset(self) -> None:
        """Reset the window counters (not lifetime totals).

        Called when state transitions to preserve lifetime stats
        while clearing the current evaluation window.
        """
        self.failures = 0
        self.successes = 0
        self.consecutive_failures = 0
        self.consecutive_successes = 0

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate in current window (0.0 to 1.0).

        Returns 0.0 if no requests recorded (avoids division by zero).
        """
        total = self.failures + self.successes
        return self.failures / total if total else 0.0


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behaviour.

    Tuning Guide
    ------------
    - **failure_threshold**: Higher = more tolerant of transient failures.
      Lower = faster trip, less load on failing service.

    - **recovery_timeout**: Higher = longer protection, but slower recovery.
      Lower = quicker recovery attempts, but risks re-tripping.

    - **half_open_max_calls**: How many probe requests before deciding
      if service recovered. More = more confidence, but more risk.

    - **failure_rate_threshold**: Alternative trip condition based on
      percentage rather than consecutive count.

    - **minimum_calls**: Don't evaluate failure_rate until this many
      requests (avoids tripping on first few failures).
    """

    failure_threshold: int = CIRCUIT_BREAKER_FAILURE_THRESHOLD
    recovery_timeout: float = CIRCUIT_BREAKER_RECOVERY_TIMEOUT
    half_open_max_calls: int = CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS
    failure_rate_threshold: float = 0.5
    minimum_calls: int = 10

    def __post_init__(self) -> None:
        """Clamp values to sane ranges to prevent misconfiguration."""
        self.failure_threshold = max(1, min(100, self.failure_threshold))
        self.recovery_timeout = max(1.0, min(3600.0, self.recovery_timeout))
        self.half_open_max_calls = max(1, min(20, self.half_open_max_calls))
        self.failure_rate_threshold = max(0.1, min(1.0, self.failure_rate_threshold))


class Breaker:
    """Circuit breaker implementation with automatic state transitions.

    Usage Patterns
    --------------
    **Pattern 1: Manual tracking**
    ```python
    breaker = Breaker("my-service")
    if breaker.allow():
        try:
            result = call_service()
            breaker.record_success()
        except Exception as e:
            breaker.record_failure(e)
            raise
    else:
        raise CircuitBreakerOpen("service unavailable")
    ```

    **Pattern 2: Execute wrapper (recommended)**
    ```python
    breaker = Breaker("my-service")
    try:
        result = breaker.execute(lambda: call_service())
    except CircuitBreakerOpen:
        # Handle gracefully
        pass
    ```

    Thread Safety
    -------------
    All state transitions are protected by a lock. Safe for concurrent
    access from multiple threads.
    """

    __slots__ = (
        "_name",
        "_config",
        "_state",
        "_stats",
        "_lock",
        "_opened_at",
        "_half_open_calls",
    )

    def __init__(self, name: str, config: CircuitBreakerConfig | None = None) -> None:
        """Initialise circuit breaker.

        Args:
            name: Identifier for logging and debugging
            config: Configuration (uses defaults if None)
        """
        self._name = name
        self._config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._lock: Final[Lock] = Lock()
        self._opened_at: float = 0.0
        self._half_open_calls: int = 0
        _log.debug("breaker '%s' init", name)

    @property
    def name(self) -> str:
        """Return the breaker's identifier."""
        return self._name

    @property
    def state(self) -> CircuitState:
        """Current state (triggers transition check).

        Accessing this property may cause a transition from OPEN
        to HALF_OPEN if the recovery timeout has elapsed.
        """
        with self._lock:
            self._maybe_transition()
            return self._state

    @property
    def stats(self) -> CircuitStats:
        """Return the statistics object for monitoring."""
        return self._stats

    @property
    def is_closed(self) -> bool:
        """Return True if circuit is closed (normal operation)."""
        return self.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Return True if circuit is open (failing fast)."""
        return self.state == CircuitState.OPEN

    def _maybe_transition(self) -> None:
        """Check for automatic state transitions.

        OPEN → HALF_OPEN: When recovery_timeout has elapsed since
        the circuit was opened. This allows probe requests to test
        if the service has recovered.
        """
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._opened_at
            if elapsed >= self._config.recovery_timeout:
                _log.info("breaker '%s' -> half-open", self._name)
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                self._stats.reset()

    def _should_trip(self) -> bool:
        """Evaluate if the circuit should trip to OPEN.

        Trip conditions (any one triggers):
        1. Consecutive failures >= threshold
        2. Failure rate >= threshold (after minimum_calls)
        """
        if self._stats.consecutive_failures >= self._config.failure_threshold:
            return True
        if self._stats.total_requests >= self._config.minimum_calls:
            if self._stats.failure_rate >= self._config.failure_rate_threshold:
                return True
        return False

    def allow(self) -> bool:
        """Check if a request should be allowed through.

        Returns:
            True if request can proceed, False if should fail fast.

        Behaviour by State
        -----------------
        - CLOSED: Always allow
        - OPEN: Never allow
        - HALF_OPEN: Allow up to half_open_max_calls probes
        """
        with self._lock:
            self._maybe_transition()

            if self._state == CircuitState.CLOSED:
                return True
            if self._state == CircuitState.OPEN:
                return False

            # HALF_OPEN: Allow limited probe requests
            if self._half_open_calls < self._config.half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False

    def record_success(self) -> None:
        """Record a successful request.

        In HALF_OPEN state, enough consecutive successes will
        close the circuit (return to normal operation).
        """
        with self._lock:
            self._stats.record_success()

            if self._state == CircuitState.HALF_OPEN:
                if self._stats.consecutive_successes >= self._config.half_open_max_calls:
                    _log.info("breaker '%s' recovered", self._name)
                    self._state = CircuitState.CLOSED
                    self._stats.reset()

    def record_failure(self, err: Exception | None = None) -> None:
        """Record a failed request.

        Args:
            err: Optional exception for logging (not used currently)

        In HALF_OPEN state, any failure immediately reopens the circuit.
        In CLOSED state, trips if threshold exceeded.
        """
        with self._lock:
            self._stats.record_failure()

            if self._state == CircuitState.HALF_OPEN:
                # Recovery failed - back to OPEN
                _log.warning("breaker '%s' recovery failed", self._name)
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
                return

            if self._state == CircuitState.CLOSED and self._should_trip():
                _log.warning("breaker '%s' tripped", self._name)
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()

    def execute(self, fn: Callable[[], T]) -> T:
        """Execute a function with circuit breaker protection.

        Args:
            fn: Zero-argument callable to execute

        Returns:
            Result of fn() if successful

        Raises:
            CircuitBreakerOpen: If circuit is open/half-open at capacity
            Any exception from fn: Propagated after recording failure

        This is the recommended way to use the circuit breaker as it
        handles all the allow/record logic automatically.
        """
        if not self.allow():
            raise CircuitBreakerOpen(f"breaker '{self._name}' is open")
        try:
            result = fn()
            self.record_success()
            return result
        except Exception as e:
            self.record_failure(e)
            raise

    def reset(self) -> None:
        """Force reset to CLOSED state.

        Use for manual intervention or testing. The circuit will
        immediately start accepting requests again.
        """
        with self._lock:
            _log.info("breaker '%s' reset", self._name)
            self._state = CircuitState.CLOSED
            self._stats.reset()
            self._half_open_calls = 0

    def trip(self) -> None:
        """Force the circuit to OPEN state.

        Use for manual intervention when you know the service is
        down but haven't hit the failure threshold yet.
        """
        with self._lock:
            _log.warning("breaker '%s' forced open", self._name)
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()


# Backward compatibility alias
CircuitBreaker = Breaker


class DomainBreakers:
    """Manage one circuit breaker per domain.

    Why Per-Domain?
    ---------------
    Different services fail independently. If api.example.com is down,
    we shouldn't stop requests to cdn.example.com.

    This class automatically creates and manages breakers for each
    unique domain, simplifying usage in scraping scenarios.

    Example
    -------
        breakers = DomainBreakers()

        # Each domain gets its own breaker
        if breakers.allow_request("https://api1.example.com/data"):
            try:
                response = fetch("https://api1.example.com/data")
                breakers.record_success("https://api1.example.com/data")
            except Exception:
                breakers.record_failure("https://api1.example.com/data")
    """

    __slots__ = ("_config", "_breakers", "_lock")

    def __init__(self, config: CircuitBreakerConfig | None = None) -> None:
        """Initialise with shared configuration for all breakers.

        Args:
            config: Configuration applied to all domain breakers
        """
        self._config = config or CircuitBreakerConfig()
        self._breakers: dict[str, Breaker] = {}
        self._lock: Final[Lock] = Lock()

    def _domain(self, url: str) -> str:
        """Extract domain from URL for breaker lookup."""
        parsed = urlparse(url)
        return parsed.netloc if parsed.netloc else url

    def get(self, url: str) -> Breaker:
        """Get or create breaker for the URL's domain.

        Args:
            url: Full URL (domain extracted automatically)

        Returns:
            Breaker instance for the domain (created if new)
        """
        domain = self._domain(url)
        with self._lock:
            if domain not in self._breakers:
                self._breakers[domain] = Breaker(domain, self._config)
            return self._breakers[domain]

    def allow_request(self, url: str) -> bool:
        """Check if a request to the URL is allowed.

        Convenience method that combines get() and allow().
        """
        return self.get(url).allow()

    def record_success(self, url: str) -> None:
        """Record a successful request to the URL's domain."""
        self.get(url).record_success()

    def record_failure(self, url: str, err: Exception | None = None) -> None:
        """Record a failed request to the URL's domain."""
        self.get(url).record_failure(err)

    def get_stats(self) -> dict[str, dict[str, object]]:
        """Return stats for all tracked domains.

        Returns:
            Dict mapping domain to stats dict with keys:
            state, total, failures, rate
        """
        with self._lock:
            return {
                domain: {
                    "state": b.state.value,
                    "total": b.stats.total_requests,
                    "failures": b.stats.total_failures,
                    "rate": b.stats.failure_rate,
                }
                for domain, b in self._breakers.items()
            }

    def reset_all(self) -> None:
        """Reset all breakers to CLOSED state."""
        with self._lock:
            for b in self._breakers.values():
                b.reset()

    def clear(self) -> None:
        """Remove all breakers (useful for testing)."""
        with self._lock:
            self._breakers.clear()


# Backward compatibility alias
DomainCircuitBreakers = DomainBreakers

# Module-level singleton
_domain_breakers: DomainBreakers | None = None
_lock: Final[Lock] = Lock()


def get_domain_breakers(config: CircuitBreakerConfig | None = None) -> DomainBreakers:
    """Get or create the singleton DomainBreakers instance.

    Args:
        config: Configuration (only used on first call)

    Returns:
        The global DomainBreakers instance

    Note:
        This provides a convenient global instance. For isolated
        testing or custom configurations, create DomainBreakers directly.
    """
    global _domain_breakers
    with _lock:
        if _domain_breakers is None:
            _domain_breakers = DomainBreakers(config)
        return _domain_breakers
