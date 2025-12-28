"""Rate limiting utilities using token bucket algorithm.

Architecture
------------
This module provides three levels of rate limiting:

1. **TokenBucket**: Core algorithm - controls request rate with optional bursting
2. **DomainLimiter**: Per-domain rate limiting - different rates for different sites
3. **AdaptiveThrottler**: Auto-adjusts based on server responses (429, 503, etc.)

Why Rate Limiting Matters
-------------------------
Aggressive scraping causes problems:
- **For targets**: Server overload, increased costs, degraded service
- **For you**: IP bans, CAPTCHAs, legal issues

Rate limiting is the polite (and sustainable) approach.

Token Bucket Algorithm
----------------------
Imagine a bucket that:
- Holds up to N tokens (capacity)
- Refills at R tokens/second (rate)
- Each request consumes 1 token
- If empty, requests must wait

Example with rate=2, capacity=5:
```
Time 0: Bucket has 5 tokens (full)
Request 1: Consumes 1 token, 4 remaining (instant)
Request 2: Consumes 1 token, 3 remaining (instant)
...
Request 5: Consumes 1 token, 0 remaining (instant)
Request 6: Must wait 0.5s for bucket to refill 1 token
```

The capacity allows "bursting" - quick succession of requests up to the
limit, then throttled to the steady rate.

Thread Safety
-------------
All classes use threading locks for safe concurrent access.

Example
-------
    from easyscrape.rate_limiter import default_limiter

    # Wait 1 second between requests to same domain
    default_limiter.wait("https://example.com/page1", delay=1.0)
    default_limiter.wait("https://example.com/page2", delay=1.0)  # Waits ~1s
    default_limiter.wait("https://other.com/page1", delay=1.0)    # No wait (different domain)
"""
from __future__ import annotations

import time
from random import Random
from threading import Lock
from typing import Final
from urllib.parse import urlparse

__all__: Final[tuple[str, ...]] = (
    "TokenBucket",
    "DomainLimiter",
    "AdaptiveThrottler",
    "default_limiter",
    "adaptive_throttler",
    "reset_limiters",
    # Aliases
    "RateLimiter",
    "Throttler",
)


class TokenBucket:
    """Token bucket rate limiter with configurable rate and burst capacity.

    How It Works
    ------------
    The bucket starts full (capacity tokens). Each request consumes 1 token.
    Tokens refill at `rate` tokens per second. If empty, requests block.

    Parameters Explained
    --------------------
    - **rate**: Tokens per second. rate=2 means 2 requests/second sustained.
    - **capacity**: Maximum tokens. capacity=5 allows 5 rapid requests before throttling.

    Math Example
    ------------
    rate=0.5, capacity=1 (1 request every 2 seconds):
    - Request at t=0: OK (1 token consumed, 0 remaining)
    - Request at t=1: Waits 1s (only 0.5 tokens refilled, need 1)
    - Request at t=2: OK (1 token refilled)

    Thread Safety
    -------------
    Uses a Lock for thread-safe token management. Multiple threads can
    safely call acquire() concurrently.

    Example
    -------
        bucket = TokenBucket(rate=2.0, capacity=5.0)  # 2 req/sec, burst of 5

        for i in range(10):
            bucket.acquire()  # First 5 instant, then 2/sec
            make_request()
    """

    __slots__ = ("_rate", "_capacity", "_tokens", "_last", "_lock", "_rng")

    def __init__(self, rate: float, capacity: float = 1.0) -> None:
        """Initialise token bucket.

        Args:
            rate: Tokens per second to refill (e.g., 2.0 = 2 requests/sec)
            capacity: Maximum tokens / burst size (default 1.0 = no bursting)

        Why Monotonic Time?
        -------------------
        We use time.monotonic() instead of time.time() because:
        - time.time() can jump backwards (NTP sync, DST, manual changes)
        - time.monotonic() always increases, preventing negative elapsed times
        """
        self._rate = rate
        self._capacity = capacity
        self._tokens = capacity  # Start full
        self._last = time.monotonic()
        self._lock: Final[Lock] = Lock()
        self._rng: Final[Random] = Random()

    def acquire(self, timeout: float | None = None) -> bool:
        """Acquire a token, blocking until available or timeout.

        Args:
            timeout: Maximum seconds to wait. None = wait forever.
                     0 or negative = don't wait, return immediately.

        Returns:
            True if token acquired, False if timeout exceeded.

        Algorithm
        ---------
        1. Calculate elapsed time since last check
        2. Add refilled tokens (elapsed * rate), capped at capacity
        3. If tokens >= 1: consume and return True
        4. Else: sleep briefly and retry (or timeout)

        The sleep is capped at 50ms to remain responsive to timeouts
        while avoiding busy-waiting.
        """
        # Fast path: immediate check with no waiting
        if timeout is not None and timeout <= 0:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self._last
                self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
                self._last = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return True
                return False

        deadline = time.monotonic() + timeout if timeout else None

        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self._last
                self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
                self._last = now

                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return True

            # Check timeout
            if deadline is not None and time.monotonic() >= deadline:
                return False

            # Calculate sleep time (when will we have 1 token?)
            with self._lock:
                if self._rate <= 0:
                    return False  # Zero rate = no tokens ever
                sleep_for = (1.0 - self._tokens) / self._rate

            # Sleep in small increments to stay responsive
            time.sleep(min(sleep_for, 0.05))


class DomainLimiter:
    """Per-domain rate limiting for polite multi-site scraping.

    Why Per-Domain?
    ---------------
    Different sites have different tolerances:
    - Large sites (Google, Amazon): Can handle more traffic
    - Small sites: Easily overwhelmed
    - Your own sites: No limit needed

    By tracking domains separately, we can scrape multiple sites
    concurrently without slowing down one because another is rate-limited.

    Two Modes
    ---------
    1. **Simple delay**: `wait(url, delay)` - fixed delay between requests
    2. **Token bucket**: `acquire_token(url, rate)` - sustained rate with bursting

    Thread Safety
    -------------
    All operations are thread-safe. Multiple threads can rate-limit
    different domains concurrently.

    Example
    -------
        limiter = DomainLimiter()

        # 1 second between requests to same domain
        limiter.wait("https://site1.com/page1", delay=1.0)
        limiter.wait("https://site1.com/page2", delay=1.0)  # Waits 1s
        limiter.wait("https://site2.com/page1", delay=1.0)  # No wait
    """

    __slots__ = ("_timestamps", "_buckets", "_lock", "_rng", "_max_domains")

    # Maximum domains to track before LRU eviction
    MAX_TRACKED_DOMAINS: int = 1000

    def __init__(self, max_domains: int = MAX_TRACKED_DOMAINS) -> None:
        """Initialise with empty domain tracking."""
        self._timestamps: dict[str, float] = {}
        self._buckets: dict[str, TokenBucket] = {}
        self._lock: Final[Lock] = Lock()
        self._rng: Final[Random] = Random()
        self._max_domains = max_domains

    def _evict_oldest(self) -> None:
        """Evict oldest entries if over max capacity (LRU eviction)."""
        if len(self._timestamps) > self._max_domains:
            # Remove oldest 10% of entries
            sorted_domains = sorted(self._timestamps.items(), key=lambda x: x[1])
            evict_count = max(1, len(sorted_domains) // 10)
            for domain, _ in sorted_domains[:evict_count]:
                self._timestamps.pop(domain, None)
                self._buckets.pop(domain, None)

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain (netloc) from a URL.

        Examples:
            "https://example.com/page" → "example.com"
            "https://sub.example.com:8080/page" → "sub.example.com:8080"
        """
        parsed = urlparse(url)
        return parsed.netloc or parsed.path.split("/")[0]

    def wait(self, url: str, delay: float, jitter: bool = False) -> None:
        """Wait for specified delay since last request to this domain.

        Args:
            url: Request URL (domain extracted automatically)
            delay: Minimum seconds between requests to same domain
            jitter: If True, add random variation (-10% to +20%) to avoid
                    synchronized request patterns (looks less bot-like)

        Jitter Explained
        ----------------
        Without jitter, requests happen at exactly 1.0s intervals:
            t=0.0, t=1.0, t=2.0, t=3.0 (robotic pattern)

        With jitter, intervals vary:
            t=0.0, t=0.92, t=2.15, t=3.08 (human-like pattern)

        This reduces the chance of triggering bot detection.
        """
        if delay <= 0:
            return

        domain = self._extract_domain(url)

        with self._lock:
            last_req = self._timestamps.get(domain, 0.0)
            now = time.monotonic()
            time_since = now - last_req
            wait_time = delay - time_since

            if jitter and wait_time > 0:
                # Add -10% to +20% randomness
                wait_time += self._rng.uniform(-delay * 0.1, delay * 0.2)

        if wait_time > 0:
            time.sleep(wait_time)

        with self._lock:
            self._timestamps[domain] = time.monotonic()
            self._evict_oldest()

    def acquire_token(self, url: str, rate: float, timeout: float | None = None) -> bool:
        """Acquire a rate-limit token for the URL's domain.

        Args:
            url: Request URL (domain extracted automatically)
            rate: Seconds between requests (e.g., 1.0 = 1 req/sec)
            timeout: Maximum seconds to wait for token

        Returns:
            True if token acquired, False if timeout or rate=0.

        Note:
            Creates a TokenBucket per domain on first access. The bucket
            rate is 1/rate tokens per second (rate=2 means 0.5 tokens/sec).
        """
        if rate <= 0:
            return True  # No rate limiting

        domain = self._extract_domain(url)

        with self._lock:
            if domain not in self._buckets:
                # rate param is "seconds between requests"
                # TokenBucket rate is "tokens per second"
                self._buckets[domain] = TokenBucket(1.0 / rate)
            bucket = self._buckets[domain]

        return bucket.acquire(timeout)

    def set_domain_rate(self, domain: str, rate: float) -> None:
        """Set a custom rate limit for a specific domain.

        Args:
            domain: Domain name (e.g., "example.com")
            rate: Seconds between requests (0 = no limit)

        Use this to configure known limits:
            limiter.set_domain_rate("api.github.com", 0.72)  # 5000/hour
            limiter.set_domain_rate("mysite.local", 0)  # No limit
        """
        with self._lock:
            bucket_rate = 1.0 / rate if rate > 0 else float("inf")
            self._buckets[domain] = TokenBucket(bucket_rate)


class AdaptiveThrottler(DomainLimiter):
    """Rate limiter that automatically backs off on error responses.

    Why Adaptive?
    -------------
    Fixed rate limits are guesswork. Too slow wastes time, too fast
    triggers blocks. Adaptive throttling learns from server responses:

    - **Success (2xx)**: Gradually speed up
    - **Rate limited (429)**: Slow down (exponential backoff)
    - **Server error (5xx)**: Slow down (server is struggling)

    Backoff Algorithm
    -----------------
    Each error doubles the delay (exponential backoff), capped at 64x:
    - 0 errors: base_delay (e.g., 1s)
    - 1 error: 2x (2s)
    - 2 errors: 4x (4s)
    - 3 errors: 8x (8s)
    - ...
    - 6+ errors: 64x (64s max)

    Successes gradually reduce the error count, speeding back up.

    Tracked Status Codes
    --------------------
    - 429: Too Many Requests (explicit rate limit)
    - 503: Service Unavailable (server overloaded)
    - 520-524: Cloudflare errors (CDN overload)

    Example
    -------
        throttler = AdaptiveThrottler()

        response = make_request(url)
        if response.status_code >= 400:
            throttler.record_error(url, response.status_code)
        else:
            throttler.record_success(url)

        # Next request delay adapts based on history
        delay = throttler.compute_delay(url, base_delay=1.0)
        time.sleep(delay)
    """

    def __init__(self) -> None:
        """Initialise with parent DomainLimiter and error tracking."""
        super().__init__()
        self._error_counts: dict[str, int] = {}

    # Status codes that indicate we should slow down
    _BACKOFF_CODES: Final[frozenset[int]] = frozenset({
        429,  # Too Many Requests
        503,  # Service Unavailable
        520,  # Cloudflare: Web server returned unknown error
        521,  # Cloudflare: Web server is down
        522,  # Cloudflare: Connection timed out
        523,  # Cloudflare: Origin is unreachable
        524,  # Cloudflare: A timeout occurred
    })

    def record_error(self, url: str, status_code: int) -> None:
        """Record an error that should trigger backoff.

        Args:
            url: Request URL (domain extracted automatically)
            status_code: HTTP status code from response

        Only codes in _BACKOFF_CODES increment the error counter.
        Other errors (404, 500, etc.) are not rate-limit related.
        """
        if status_code not in self._BACKOFF_CODES:
            return
        domain = self._extract_domain(url)
        with self._lock:
            self._error_counts[domain] = self._error_counts.get(domain, 0) + 1

    def record_success(self, url: str) -> None:
        """Record a successful response to gradually reduce backoff.

        Each success decrements the error count by 1 (min 0).
        This allows recovery after temporary rate limiting.

        Args:
            url: Request URL (domain extracted automatically)
        """
        domain = self._extract_domain(url)
        with self._lock:
            if domain in self._error_counts:
                self._error_counts[domain] = max(0, self._error_counts[domain] - 1)

    def compute_delay(self, url: str, base_delay: float) -> float:
        """Compute delay multiplied by backoff factor based on errors.

        Args:
            url: Request URL (domain extracted automatically)
            base_delay: Starting delay in seconds

        Returns:
            Adjusted delay: base_delay * (2 ^ error_count), capped at 64x

        Example:
            base_delay=1.0, error_count=3 → 8.0 seconds
            base_delay=0.5, error_count=5 → 16.0 seconds
        """
        domain = self._extract_domain(url)
        with self._lock:
            error_count = self._error_counts.get(domain, 0)

        if error_count == 0:
            return base_delay

        # Exponential backoff: 2^n, capped at 2^6 = 64
        multiplier: int = 2 ** min(error_count, 6)
        return float(base_delay * multiplier)


# Module-level singletons for convenience
_limiter_lock: Final[Lock] = Lock()
default_limiter = DomainLimiter()
adaptive_throttler = AdaptiveThrottler()


def reset_limiters() -> None:
    """Reset global limiters to fresh state.

    Useful for testing or when you need to clear rate limit history.
    Creates new instances of both DomainLimiter and AdaptiveThrottler.
    """
    global default_limiter, adaptive_throttler
    with _limiter_lock:
        default_limiter = DomainLimiter()
        adaptive_throttler = AdaptiveThrottler()


# Common alternative names that users might expect

RateLimiter = TokenBucket  # Common name alias
Throttler = AdaptiveThrottler  # Short alias
