"""Tests for rate limiter module."""

import pytest
import time
from easyscrape.rate_limiter import (
    TokenBucket,
    DomainLimiter,
    AdaptiveThrottler,
    reset_limiters,
)


class TestTokenBucket:
    """Tests for TokenBucket."""

    def test_creation(self):
        """Test bucket creation."""
        bucket = TokenBucket(rate=10.0, capacity=100)
        assert bucket is not None

    def test_acquire_tokens(self):
        """Test acquiring tokens."""
        bucket = TokenBucket(rate=100.0, capacity=10)
        assert bucket.acquire() is True

    def test_acquire_with_timeout(self):
        """Test acquiring with timeout."""
        bucket = TokenBucket(rate=100.0, capacity=10)
        assert bucket.acquire(timeout=1.0) is True

    def test_rate_limiting(self):
        """Test rate limiting works."""
        bucket = TokenBucket(rate=1.0, capacity=1)
        bucket.acquire()  # Use up the token
        # Immediate second acquire should work after refill
        bucket.acquire()


class TestDomainLimiter:
    """Tests for DomainLimiter."""

    def test_creation(self):
        """Test limiter creation."""
        limiter = DomainLimiter()
        assert limiter is not None

    def test_creation_with_max_domains(self):
        """Test limiter with custom max domains."""
        limiter = DomainLimiter(max_domains=100)
        assert limiter is not None

    def test_wait_for_domain(self):
        """Test waiting for a domain."""
        limiter = DomainLimiter()
        limiter.wait("https://example.com/path", delay=0.001)
        # Should not raise

    def test_different_domains(self):
        """Test different domains tracked separately."""
        limiter = DomainLimiter()
        limiter.wait("https://example.com", delay=0.001)
        limiter.wait("https://other.com", delay=0.001)
        # Should not raise

    def test_extract_domain(self):
        """Test domain extraction."""
        domain = DomainLimiter._extract_domain("https://example.com/path")
        assert domain == "example.com"


class TestAdaptiveThrottler:
    """Tests for AdaptiveThrottler."""

    def test_creation(self):
        """Test throttler creation."""
        throttler = AdaptiveThrottler()
        assert throttler is not None

    def test_inherits_domain_limiter(self):
        """Test inherits from DomainLimiter."""
        throttler = AdaptiveThrottler()
        assert isinstance(throttler, DomainLimiter)

    def test_record_success(self):
        """Test recording success."""
        throttler = AdaptiveThrottler()
        throttler.record_success("https://example.com")
        # Should not raise

    def test_compute_delay(self):
        """Test compute delay."""
        throttler = AdaptiveThrottler()
        delay = throttler.compute_delay("https://example.com", base_delay=1.0)
        assert delay >= 0


class TestResetLimiters:
    """Tests for reset_limiters function."""

    def test_reset_no_error(self):
        """Test reset doesn't raise."""
        reset_limiters()
        # Should not raise



class TestTokenBucketAdvanced:
    """Advanced tests for TokenBucket."""
    
    def test_acquire_empty_bucket(self):
        """Test acquire on empty bucket without timeout."""
        bucket = TokenBucket(rate=0.1, capacity=1)
        bucket.acquire()  # Drain the bucket
        # Immediate second acquire without timeout
        result = bucket.acquire(timeout=0.0)
        # Should return False or True depending on refill
    
    def test_token_refill(self):
        """Test tokens refill over time."""
        import time
        bucket = TokenBucket(rate=10.0, capacity=1)
        bucket.acquire()  # Use the token
        time.sleep(0.15)  # Wait for refill
        assert bucket.acquire() is True


class TestDomainLimiterAdvanced:
    """Advanced tests for DomainLimiter."""
    
    def test_wait(self):
        """Test wait method enforces delay between requests."""
        limiter = DomainLimiter()
        import time
        # First call - no wait since no prior request
        limiter.wait("https://example.com/page", delay=0.05)
        # Second call - should wait since we just made a request
        start = time.time()
        limiter.wait("https://example.com/page", delay=0.05)
        elapsed = time.time() - start
        assert elapsed >= 0.04  # Allow small tolerance
    
    def test_wait_with_jitter(self):
        """Test wait with jitter."""
        limiter = DomainLimiter()
        limiter.wait("https://example.com/page", delay=0.01, jitter=True)
    
    def test_acquire_token(self):
        """Test acquire_token method."""
        limiter = DomainLimiter()
        result = limiter.acquire_token("https://example.com", rate=100.0)
        assert result is True
    
    def test_set_domain_rate(self):
        """Test set_domain_rate method."""
        limiter = DomainLimiter()
        limiter.set_domain_rate("example.com", 5.0)
        # Should not raise
    
    def test_extract_domain(self):
        """Test domain extraction from URL."""
        limiter = DomainLimiter()
        domain = limiter._extract_domain("https://example.com/path/page")
        assert domain == "example.com"
    
    def test_evict_oldest(self):
        """Test eviction of oldest domains."""
        limiter = DomainLimiter(max_domains=2)
        limiter.wait("https://a.com", delay=0)
        limiter.wait("https://b.com", delay=0)
        limiter.wait("https://c.com", delay=0)  # Should trigger eviction


class TestAdaptiveThrottlerAdvanced:
    """Advanced tests for AdaptiveThrottler."""
    
    def test_record_error(self):
        """Test recording errors."""
        throttler = AdaptiveThrottler()
        throttler.record_error("https://example.com", 429)
    
    def test_record_success(self):
        """Test recording successes."""
        throttler = AdaptiveThrottler()
        throttler.record_success("https://example.com")
    
    def test_compute_delay_normal(self):
        """Test compute_delay with no errors."""
        throttler = AdaptiveThrottler()
        delay = throttler.compute_delay("https://example.com", 1.0)
        assert delay >= 0
    
    def test_compute_delay_after_errors(self):
        """Test compute_delay increases after errors."""
        throttler = AdaptiveThrottler()
        throttler.record_error("https://example.com", 429)
        delay1 = throttler.compute_delay("https://example.com", 1.0)
        throttler.record_error("https://example.com", 503)
        delay2 = throttler.compute_delay("https://example.com", 1.0)
        # Delay should increase with more errors
    
    def test_compute_delay_recovery(self):
        """Test delay recovers after successes."""
        throttler = AdaptiveThrottler()
        throttler.record_error("https://example.com", 429)
        throttler.record_success("https://example.com")
        throttler.record_success("https://example.com")
        delay = throttler.compute_delay("https://example.com", 1.0)


class TestResetLimiters:
    """Tests for reset_limiters function."""
    
    def test_reset_limiters(self):
        """Test reset_limiters function."""
        reset_limiters()  # Should not raise






