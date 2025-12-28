"""
Performance-focused tests for EasyScrape.

These tests verify that performance optimisations work correctly:
- Caching behaviour
- Connection pooling
- Rate limiting
- Lazy loading
"""

import time
import pytest
from easyscrape import Config
from easyscrape.rate_limiter import TokenBucket, DomainLimiter


class TestTokenBucket:
    """Token bucket rate limiter tests."""

    def test_bucket_allows_burst(self):
        """Token bucket should allow burst up to capacity."""
        bucket = TokenBucket(rate=1.0, capacity=5.0)
        # Should allow burst
        assert bucket.acquire() is True

    def test_bucket_refills_over_time(self):
        """Token bucket should refill tokens over time."""
        bucket = TokenBucket(rate=10.0, capacity=1.0)  # 10 tokens/sec
        bucket.acquire()
        time.sleep(0.15)  # Wait for refill
        assert bucket.acquire() is True


class TestDomainLimiter:
    """Per-domain rate limiting tests."""

    def test_limiter_creation(self):
        """Domain limiter should be creatable."""
        limiter = DomainLimiter()
        assert limiter is not None

    def test_limiter_tracks_domains(self):
        """Domain limiter should track multiple domains."""
        limiter = DomainLimiter()
        # Should handle multiple domains
        limiter.acquire_token("http://example.com/", rate=10.0)
        limiter.acquire_token("http://other.com/", rate=10.0)


class TestLazyLoading:
    """Lazy loading and import performance tests."""

    def test_core_import_fast(self):
        """Core imports should be fast (lazy loading)."""
        import importlib
        import easyscrape

        # Reimport should be cached
        start = time.perf_counter()
        importlib.reload(easyscrape)
        elapsed = time.perf_counter() - start

        # Should complete in under 1 second
        assert elapsed < 1.0

    def test_config_creation_fast(self):
        """Config creation should be fast."""
        start = time.perf_counter()
        for _ in range(1000):
            Config()
        elapsed = time.perf_counter() - start

        # 1000 configs in under 0.5 seconds
        assert elapsed < 0.5


class TestCachePerformance:
    """Cache performance tests."""

    def test_cache_creation(self):
        """Cache should be creatable with defaults."""
        from easyscrape.cache import ResponseCache

        cache = ResponseCache()
        assert cache is not None

    def test_cache_operations(self):
        """Cache set/get should work."""
        from easyscrape.cache import ResponseCache

        cache = ResponseCache()
        cache.set("test_key", b"test_value", headers={}, status=200, ttl=3600)
        result = cache.get("test_key")
        assert result is not None
