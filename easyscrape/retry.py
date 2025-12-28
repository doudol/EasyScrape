"""Retry logic with multiple backoff strategies.

This module provides flexible retry functionality with various backoff
strategies for handling transient failures in HTTP requests.

Backoff Strategies
------------------
- ConstantBackoff: Same delay every retry
- LinearBackoff: Delay increases linearly
- ExponentialBackoff: Delay doubles each retry
- FibonacciBackoff: Delay follows Fibonacci sequence
- DecorrelatedJitterBackoff: Randomized exponential (AWS style)

Example
-------
    from easyscrape.retry import Retrier, RetryConfig

    config = RetryConfig(max_retries=3, base_delay=1.0)
    retrier = Retrier(config)

    result = retrier.execute(lambda: make_request())
"""
from __future__ import annotations

import asyncio
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Final, TypeVar

from .constants import (
    DEFAULT_BACKOFF_FACTOR,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_DELAY,
    MAX_RETRY_DELAY,
    RETRYABLE_STATUS_CODES,
)
from .log import get_logger

__all__: Final[tuple[str, ...]] = (
    "BackoffStrategy",
    "ConstantBackoff",
    "LinearBackoff",
    "ExponentialBackoff",
    "FibonacciBackoff",
    "DecorrelatedJitterBackoff",
    "JitterWrapper",
    "RetryConfig",
    "RetryState",
    "Retrier",
    "RetryPolicy",
    "retry",
    "default_retrier",
    "aggressive_retrier",
    "conservative_retrier",
)

_log = get_logger(__name__)
T = TypeVar("T")


class BackoffStrategy(ABC):
    """Abstract base class for backoff strategies."""

    @abstractmethod
    def get_delay(self, attempt: int, base_delay: float) -> float:
        """Calculate delay for given attempt.

        Parameters
        ----------
        attempt : int
            The attempt number (0-indexed).
        base_delay : float
            The base delay in seconds.

        Returns
        -------
        float
            The delay in seconds.
        """
        ...


class ConstantBackoff(BackoffStrategy):
    """Constant delay between retries."""

    def get_delay(self, attempt: int, base_delay: float) -> float:
        return base_delay


class LinearBackoff(BackoffStrategy):
    """Linearly increasing delay."""

    def __init__(self, increment: float = 1.0) -> None:
        self._increment = increment

    def get_delay(self, attempt: int, base_delay: float) -> float:
        return base_delay + (attempt * self._increment)


class ExponentialBackoff(BackoffStrategy):
    """Exponentially increasing delay."""

    def __init__(
        self,
        factor: float = DEFAULT_BACKOFF_FACTOR,
        max_delay: float = MAX_RETRY_DELAY,
    ) -> None:
        self._factor = factor
        self._max_delay = max_delay

    def get_delay(self, attempt: int, base_delay: float) -> float:
        delay = base_delay * (self._factor ** attempt)
        return min(delay, self._max_delay)


class FibonacciBackoff(BackoffStrategy):
    """Fibonacci sequence delay."""

    def __init__(self, max_delay: float = MAX_RETRY_DELAY) -> None:
        self._max_delay = max_delay
        self._cache: dict[int, int] = {0: 1, 1: 1}

    def _fib(self, n: int) -> int:
        if n in self._cache:
            return self._cache[n]
        self._cache[n] = self._fib(n - 1) + self._fib(n - 2)
        return self._cache[n]

    def get_delay(self, attempt: int, base_delay: float) -> float:
        delay = base_delay * self._fib(attempt)
        return min(delay, self._max_delay)


class DecorrelatedJitterBackoff(BackoffStrategy):
    """AWS-style decorrelated jitter."""

    def __init__(self, max_delay: float = MAX_RETRY_DELAY) -> None:
        self._max_delay = max_delay
        self._prev_delay = 0.0

    def get_delay(self, attempt: int, base_delay: float) -> float:
        if attempt == 0:
            self._prev_delay = base_delay
            return base_delay

        delay = random.uniform(base_delay, self._prev_delay * 3)
        delay = min(delay, self._max_delay)
        self._prev_delay = delay
        return delay


class JitterWrapper(BackoffStrategy):
    """Adds jitter to any backoff strategy."""

    def __init__(
        self,
        inner: BackoffStrategy,
        jitter_factor: float = 0.25,
    ) -> None:
        self._inner = inner
        self._jitter_factor = jitter_factor

    def get_delay(self, attempt: int, base_delay: float) -> float:
        delay = self._inner.get_delay(attempt, base_delay)
        jitter = delay * self._jitter_factor * random.random()
        return delay + jitter


@dataclass
class RetryConfig:
    """Configuration for retry behaviour."""

    max_retries: int = DEFAULT_MAX_RETRIES
    base_delay: float = DEFAULT_RETRY_DELAY
    max_delay: float = MAX_RETRY_DELAY
    backoff: BackoffStrategy = field(default_factory=ExponentialBackoff)
    jitter: bool = True
    jitter_factor: float = 0.25
    retryable_status_codes: set[int] = field(
        default_factory=lambda: set(RETRYABLE_STATUS_CODES)
    )
    retryable_exceptions: set[type[Exception]] = field(
        default_factory=lambda: {Exception}
    )


def _get_time() -> float:
    """Get current time using highest resolution timer available."""
    # Use perf_counter for highest resolution on all platforms
    return time.perf_counter()


@dataclass
class RetryState:
    """Tracks state during retry attempts."""

    config: RetryConfig
    attempt: int = 0
    errors: list[Exception] = field(default_factory=list)
    start_time: float = field(default_factory=_get_time)
    total_delay: float = 0.0

    @property
    def attempts_remaining(self) -> int:
        return max(0, self.config.max_retries - self.attempt)

    @property
    def elapsed(self) -> float:
        return _get_time() - self.start_time

    def record_attempt(self, error: Exception | None = None) -> None:
        self.attempt += 1
        if error:
            self.errors.append(error)

    def should_retry(self, error: Exception | None = None) -> bool:
        if self.attempt >= self.config.max_retries:
            return False
        if error and self.config.retryable_exceptions:
            return any(
                isinstance(error, exc_type)
                for exc_type in self.config.retryable_exceptions
            )
        return True

    def get_delay(self) -> float:
        delay = self.config.backoff.get_delay(self.attempt, self.config.base_delay)
        if self.config.jitter:
            jitter = delay * self.config.jitter_factor * random.random()
            delay += jitter
        delay = min(delay, self.config.max_delay)
        self.total_delay += delay
        return delay


class Retrier:
    """Executes functions with retry logic."""

    def __init__(self, config: RetryConfig | None = None) -> None:
        self._config = config or RetryConfig()

    def execute(
        self,
        func: Callable[[], T],
        on_retry: Callable[[int, Exception], None] | None = None,
    ) -> T:
        """Execute function with retries.

        Parameters
        ----------
        func : Callable
            Function to execute.
        on_retry : Callable, optional
            Callback called on each retry.

        Returns
        -------
        T
            The function result.

        Raises
        ------
        Exception
            The last exception if all retries fail.
        """
        state = RetryState(self._config)
        last_error: Exception | None = None

        while True:
            try:
                return func()
            except Exception as e:
                last_error = e
                state.record_attempt(e)

                if not state.should_retry(e):
                    raise

                if on_retry:
                    on_retry(state.attempt, e)

                delay = state.get_delay()
                _log.debug(
                    "Retry %d/%d after %.2fs: %s",
                    state.attempt,
                    self._config.max_retries,
                    delay,
                    e,
                )
                time.sleep(delay)

    async def async_execute(
        self,
        func: Callable[[], T],
        on_retry: Callable[[int, Exception], None] | None = None,
    ) -> T:
        """Execute async function with retries."""
        state = RetryState(self._config)

        while True:
            try:
                result = func()
                if asyncio.iscoroutine(result):
                    return await result
                return result
            except Exception as e:
                state.record_attempt(e)

                if not state.should_retry(e):
                    raise

                if on_retry:
                    on_retry(state.attempt, e)

                delay = state.get_delay()
                await asyncio.sleep(delay)


class RetryPolicy:
    """Simple retry policy for session.py compatibility."""

    def __init__(
        self,
        max_attempts: int = DEFAULT_MAX_RETRIES,
        base_delay: float = DEFAULT_RETRY_DELAY,
        multiplier: float = DEFAULT_BACKOFF_FACTOR,
    ) -> None:
        self._config = RetryConfig(
            max_retries=max_attempts,
            base_delay=base_delay,
            backoff=ExponentialBackoff(factor=multiplier),
        )
        self._retrier = Retrier(self._config)

    def execute(self, func: Callable[[], T]) -> T:
        """Execute function with retries."""
        return self._retrier.execute(func)


def retry(
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_RETRY_DELAY,
    **kwargs: Any,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for adding retry logic to functions.

    Parameters
    ----------
    max_retries : int
        Maximum retry attempts.
    base_delay : float
        Base delay between retries.

    Example
    -------
        @retry(max_retries=3)
        def fetch_data():
            return requests.get(url)
    """
    config = RetryConfig(max_retries=max_retries, base_delay=base_delay, **kwargs)
    retrier = Retrier(config)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kw: Any) -> T:
            return retrier.execute(lambda: func(*args, **kw))
        return wrapper
    return decorator


# Pre-configured retriers
default_retrier = Retrier(RetryConfig())

aggressive_retrier = Retrier(RetryConfig(
    max_retries=5,
    base_delay=0.5,
    backoff=ExponentialBackoff(factor=1.5),
))

conservative_retrier = Retrier(RetryConfig(
    max_retries=2,
    base_delay=2.0,
    backoff=LinearBackoff(increment=2.0),
))
