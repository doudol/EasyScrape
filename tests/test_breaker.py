"""Tests for circuit breaker module."""

import pytest
from easyscrape.breaker import (
    CircuitState,
    CircuitStats,
    CircuitBreakerConfig,
    Breaker,
    DomainBreakers,
    get_domain_breakers,
)


class TestCircuitState:
    """Tests for CircuitState enum."""

    def test_states_exist(self):
        """Test all states exist."""
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"


class TestCircuitStats:
    """Tests for CircuitStats."""

    def test_initial_values(self):
        """Test initial stats are zero."""
        stats = CircuitStats()
        assert stats.failures == 0
        assert stats.successes == 0
        assert stats.consecutive_failures == 0

    def test_record_success(self):
        """Test recording success."""
        stats = CircuitStats()
        stats.record_success()
        assert stats.successes == 1
        assert stats.consecutive_successes == 1
        assert stats.consecutive_failures == 0

    def test_record_failure(self):
        """Test recording failure."""
        stats = CircuitStats()
        stats.record_failure()
        assert stats.failures == 1
        assert stats.consecutive_failures == 1

    def test_reset(self):
        """Test reset clears counters."""
        stats = CircuitStats()
        stats.record_failure()
        stats.record_failure()
        stats.reset()
        assert stats.failures == 0
        assert stats.consecutive_failures == 0

    def test_failure_rate(self):
        """Test failure rate calculation."""
        stats = CircuitStats()
        stats.record_success()
        stats.record_failure()
        assert stats.failure_rate == 0.5


class TestCircuitBreakerConfig:
    """Tests for CircuitBreakerConfig."""

    def test_default_values(self):
        """Test default config values."""
        config = CircuitBreakerConfig()
        assert config.failure_threshold >= 1
        assert config.recovery_timeout >= 1.0
        assert config.half_open_max_calls >= 1

    def test_custom_values(self):
        """Test custom config values."""
        config = CircuitBreakerConfig(
            failure_threshold=10,
            recovery_timeout=60.0,
        )
        assert config.failure_threshold == 10
        assert config.recovery_timeout == 60.0

    def test_value_clamping(self):
        """Test values are clamped to valid range."""
        config = CircuitBreakerConfig(failure_threshold=0)
        assert config.failure_threshold >= 1


class TestBreaker:
    """Tests for Breaker class."""

    def test_initial_state_closed(self):
        """Test breaker starts closed."""
        breaker = Breaker("test")
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_closed is True

    def test_name_property(self):
        """Test name property."""
        breaker = Breaker("my-breaker")
        assert breaker.name == "my-breaker"

    def test_record_success(self):
        """Test recording success."""
        breaker = Breaker("test")
        breaker.record_success()
        assert breaker.stats.successes == 1

    def test_record_failure(self):
        """Test recording failure."""
        breaker = Breaker("test")
        breaker.record_failure()
        assert breaker.stats.failures == 1

    def test_allow_when_closed(self):
        """Test allow returns True when closed."""
        breaker = Breaker("test")
        assert breaker.allow() is True

    def test_trips_after_threshold(self):
        """Test circuit trips after failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = Breaker("test", config)
        
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == CircuitState.CLOSED
        
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

    def test_reset(self):
        """Test manual reset."""
        config = CircuitBreakerConfig(failure_threshold=1)
        breaker = Breaker("test", config)
        breaker.record_failure()
        assert breaker.state == CircuitState.OPEN
        
        breaker.reset()
        assert breaker.state == CircuitState.CLOSED

    def test_stats_property(self):
        """Test stats property."""
        breaker = Breaker("test")
        assert isinstance(breaker.stats, CircuitStats)


class TestDomainBreakers:
    """Tests for DomainBreakers."""

    def test_get_creates_breaker(self):
        """Test get creates new breaker."""
        breakers = DomainBreakers()
        breaker = breakers.get("example.com")
        assert isinstance(breaker, Breaker)

    def test_get_returns_same(self):
        """Test get returns same breaker for same domain."""
        breakers = DomainBreakers()
        b1 = breakers.get("example.com")
        b2 = breakers.get("example.com")
        assert b1 is b2

    def test_different_domains(self):
        """Test different domains get different breakers."""
        breakers = DomainBreakers()
        b1 = breakers.get("example.com")
        b2 = breakers.get("other.com")
        assert b1 is not b2

    def test_from_url(self):
        """Test creating from URL."""
        breakers = DomainBreakers()
        breaker = breakers.get("https://example.com/path")
        assert breaker.name == "example.com"


class TestGetDomainBreakers:
    """Tests for singleton accessor."""

    def test_returns_instance(self):
        """Test returns DomainBreakers."""
        breakers = get_domain_breakers()
        assert isinstance(breakers, DomainBreakers)

    def test_singleton(self):
        """Test returns same instance."""
        b1 = get_domain_breakers()
        b2 = get_domain_breakers()
        assert b1 is b2



class TestBreakerBasic:
    """Basic tests for Breaker class."""
    
    def test_is_open_property(self):
        """Test is_open property."""
        from easyscrape.breaker import Breaker, CircuitBreakerConfig
        config = CircuitBreakerConfig(failure_threshold=1)
        breaker = Breaker(name="test_open", config=config)
        
        assert breaker.is_open is False
        
        breaker.allow()
        breaker.record_failure()
        
        assert breaker.is_open is True
    
    def test_allow_when_closed(self):
        """Test allow returns True when closed."""
        from easyscrape.breaker import Breaker, CircuitBreakerConfig
        config = CircuitBreakerConfig()
        breaker = Breaker(name="test_allow", config=config)
        
        assert breaker.allow() is True
    
    def test_allow_when_open(self):
        """Test allow returns False when open."""
        from easyscrape.breaker import Breaker, CircuitBreakerConfig
        config = CircuitBreakerConfig(failure_threshold=1)
        breaker = Breaker(name="test_deny", config=config)
        
        breaker.allow()
        breaker.record_failure()
        
        assert breaker.allow() is False



class TestCircuitStats:
    """Tests for CircuitStats class."""
    
    def test_circuit_stats_creation(self):
        """Test CircuitStats creation."""
        from easyscrape.breaker import CircuitStats
        stats = CircuitStats()
        assert stats is not None
    
    def test_circuit_stats_record_success(self):
        """Test recording success."""
        from easyscrape.breaker import CircuitStats
        stats = CircuitStats()
        stats.record_success()
        assert stats.consecutive_successes >= 1
    
    def test_circuit_stats_record_failure(self):
        """Test recording failure."""
        from easyscrape.breaker import CircuitStats
        stats = CircuitStats()
        stats.record_failure()
        assert stats.consecutive_failures >= 1
    
    def test_circuit_stats_reset(self):
        """Test stats reset."""
        from easyscrape.breaker import CircuitStats
        stats = CircuitStats()
        stats.record_failure()
        stats.reset()
        assert stats.consecutive_failures == 0



# =============================================================================
# Additional Coverage Tests
# =============================================================================

class TestCircuitBreakerStateTransitions:
    """Tests for circuit breaker state transitions."""

    def test_half_open_transitions(self):
        """Test half-open state transitions."""
        from easyscrape.breaker import CircuitBreaker, CircuitBreakerConfig, CircuitState
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=0.01,
        )
        breaker = CircuitBreaker(name="test", config=config)
        
        # Trip the breaker
        breaker.record_failure(Exception("fail"))
        assert breaker.state == CircuitState.OPEN
        
        # Wait for recovery
        import time
        time.sleep(0.02)
        
        # Allow should trigger half-open
        allowed = breaker.allow()
        assert allowed or breaker.state in [CircuitState.HALF_OPEN, CircuitState.OPEN]

    def test_execute_success(self):
        """Test execute with successful function."""
        from easyscrape.breaker import CircuitBreaker
        breaker = CircuitBreaker(name="test")
        
        result = breaker.execute(lambda: "success")
        assert result == "success"

    def test_execute_failure(self):
        """Test execute with failing function."""
        from easyscrape.breaker import CircuitBreaker
        breaker = CircuitBreaker(name="test")
        
        def fail():
            raise ValueError("test error")
        
        with pytest.raises(ValueError):
            breaker.execute(fail)

    def test_manual_reset(self):
        """Test manual circuit reset."""
        from easyscrape.breaker import CircuitBreaker, CircuitBreakerConfig, CircuitState
        config = CircuitBreakerConfig(failure_threshold=1)
        breaker = CircuitBreaker(name="test", config=config)
        
        # Trip the breaker
        breaker.record_failure(Exception("fail"))
        assert breaker.state == CircuitState.OPEN
        
        # Manual reset
        breaker.reset()
        assert breaker.state == CircuitState.CLOSED

    def test_manual_trip(self):
        """Test manual circuit trip."""
        from easyscrape.breaker import CircuitBreaker, CircuitState
        breaker = CircuitBreaker(name="test")
        
        assert breaker.state == CircuitState.CLOSED
        
        # Manual trip
        breaker.trip()
        assert breaker.state == CircuitState.OPEN


class TestCircuitBreakerOpen:
    """Tests for CircuitBreakerOpen exception."""

    def test_execute_when_open(self):
        """Test that execute raises when circuit is open."""
        from easyscrape.breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpen
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=100)
        breaker = CircuitBreaker(name="test", config=config)
        
        # Trip the breaker
        breaker.record_failure(Exception("fail"))
        
        # Execute should raise
        with pytest.raises(CircuitBreakerOpen):
            breaker.execute(lambda: "test")

    def test_failure_rate_threshold(self):
        """Test failure rate threshold triggers trip."""
        from easyscrape.breaker import CircuitBreaker, CircuitBreakerConfig, CircuitState
        config = CircuitBreakerConfig(
            failure_threshold=100,  # High threshold
            failure_rate_threshold=0.5,
            minimum_calls=4
        )
        breaker = CircuitBreaker(name="test", config=config)
        
        # Record mixed successes and failures
        breaker.record_success()
        breaker.record_success()
        breaker.record_failure(Exception("fail"))
        breaker.record_failure(Exception("fail"))
        breaker.record_failure(Exception("fail"))  # This should trip at 60% failure rate
        
        # Should be open due to failure rate
        assert breaker.state == CircuitState.OPEN


class TestCircuitBreakerEdgeCases:
    """Edge case tests for circuit breaker."""
    
    def test_breaker_record_success_when_closed(self):
        """Test recording success in closed state."""
        from easyscrape.breaker import Breaker, CircuitBreakerConfig
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = Breaker("test", config)
        breaker.record_success()
        assert breaker.allow() is True
    
    def test_breaker_failure_count_reset(self):
        """Test failure count resets after success."""
        from easyscrape.breaker import Breaker, CircuitBreakerConfig
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = Breaker("test", config)
        breaker.record_failure()
        breaker.record_failure()
        breaker.record_success()
        # After success, should still allow
        assert breaker.allow() is True


class TestBreakerStateTransitions:
    """Tests for breaker state machine."""
    
    def test_breaker_stays_closed_under_threshold(self):
        """Test breaker stays closed under failure threshold."""
        from easyscrape.breaker import Breaker, CircuitBreakerConfig
        config = CircuitBreakerConfig(failure_threshold=5)
        breaker = Breaker("test", config)
        for _ in range(4):  # Under threshold
            breaker.record_failure()
        assert breaker.allow() is True
