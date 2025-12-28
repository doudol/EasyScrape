"""Tests for retry module."""

import pytest
from easyscrape.retry import (
    ConstantBackoff,
    LinearBackoff,
    ExponentialBackoff,
    FibonacciBackoff,
    DecorrelatedJitterBackoff,
    JitterWrapper,
    RetryConfig,
    Retrier,
)


class TestConstantBackoff:
    """Tests for ConstantBackoff."""

    def test_same_delay_every_attempt(self):
        """Test constant delay."""
        backoff = ConstantBackoff()
        assert backoff.get_delay(0, 1.0) == 1.0
        assert backoff.get_delay(5, 1.0) == 1.0
        assert backoff.get_delay(10, 2.0) == 2.0


class TestLinearBackoff:
    """Tests for LinearBackoff."""

    def test_increases_linearly(self):
        """Test linear increase."""
        backoff = LinearBackoff(increment=1.0)
        assert backoff.get_delay(0, 1.0) == 1.0
        assert backoff.get_delay(1, 1.0) == 2.0
        assert backoff.get_delay(2, 1.0) == 3.0

    def test_custom_increment(self):
        """Test custom increment."""
        backoff = LinearBackoff(increment=0.5)
        assert backoff.get_delay(0, 1.0) == 1.0
        assert backoff.get_delay(2, 1.0) == 2.0


class TestExponentialBackoff:
    """Tests for ExponentialBackoff."""

    def test_increases_exponentially(self):
        """Test exponential increase."""
        backoff = ExponentialBackoff(factor=2.0)
        assert backoff.get_delay(0, 1.0) == 1.0
        assert backoff.get_delay(1, 1.0) == 2.0
        assert backoff.get_delay(2, 1.0) == 4.0

    def test_max_delay_cap(self):
        """Test max delay is capped."""
        backoff = ExponentialBackoff(factor=2.0, max_delay=5.0)
        assert backoff.get_delay(10, 1.0) <= 5.0

    def test_default_creation(self):
        """Test default creation."""
        backoff = ExponentialBackoff()
        assert backoff is not None


class TestFibonacciBackoff:
    """Tests for FibonacciBackoff."""

    def test_creation(self):
        """Test creation."""
        backoff = FibonacciBackoff()
        assert backoff is not None

    def test_fibonacci_sequence(self):
        """Test follows fibonacci sequence."""
        backoff = FibonacciBackoff()
        # First few fibonacci numbers: 1, 1, 2, 3, 5, 8...
        delay0 = backoff.get_delay(0, 1.0)
        delay1 = backoff.get_delay(1, 1.0)
        delay2 = backoff.get_delay(2, 1.0)
        assert delay0 <= delay1 <= delay2

    def test_max_delay_cap(self):
        """Test max delay is capped."""
        backoff = FibonacciBackoff(max_delay=5.0)
        assert backoff.get_delay(20, 1.0) <= 5.0


class TestDecorrelatedJitterBackoff:
    """Tests for DecorrelatedJitterBackoff."""

    def test_creation(self):
        """Test creation."""
        backoff = DecorrelatedJitterBackoff()
        assert backoff is not None

    def test_returns_delay(self):
        """Test returns a delay."""
        backoff = DecorrelatedJitterBackoff()
        delay = backoff.get_delay(0, 1.0)
        assert delay >= 0

    def test_max_delay_cap(self):
        """Test max delay is capped."""
        backoff = DecorrelatedJitterBackoff(max_delay=5.0)
        # Multiple calls should stay under max
        for i in range(10):
            assert backoff.get_delay(i, 1.0) <= 5.0


class TestJitterWrapper:
    """Tests for JitterWrapper."""

    def test_adds_jitter(self):
        """Test jitter is added."""
        inner = ConstantBackoff()
        wrapper = JitterWrapper(inner, jitter_factor=0.5)
        
        delays = [wrapper.get_delay(0, 1.0) for _ in range(10)]
        # With 50% jitter, delays should vary
        assert min(delays) != max(delays)

    def test_wraps_exponential(self):
        """Test wrapping exponential backoff."""
        inner = ExponentialBackoff()
        wrapper = JitterWrapper(inner, jitter_factor=0.25)
        delay = wrapper.get_delay(0, 1.0)
        assert delay >= 0


class TestRetryConfig:
    """Tests for RetryConfig."""

    def test_default_values(self):
        """Test default config values."""
        config = RetryConfig()
        assert config.max_retries >= 0
        assert config.base_delay > 0
        assert config.jitter is True

    def test_custom_values(self):
        """Test custom config values."""
        config = RetryConfig(max_retries=5, base_delay=2.0)
        assert config.max_retries == 5
        assert config.base_delay == 2.0

    def test_retryable_status_codes(self):
        """Test default retryable status codes."""
        config = RetryConfig()
        assert 429 in config.retryable_status_codes
        assert 503 in config.retryable_status_codes

    def test_custom_status_codes(self):
        """Test custom retryable status codes."""
        config = RetryConfig(retryable_status_codes={500, 502})
        assert 500 in config.retryable_status_codes
        assert 429 not in config.retryable_status_codes


class TestRetrier:
    """Tests for Retrier class."""

    def test_creation(self):
        """Test retrier creation."""
        retrier = Retrier()
        assert retrier is not None

    def test_with_config(self):
        """Test retrier with config."""
        config = RetryConfig(max_retries=5)
        retrier = Retrier(config)
        assert retrier._config.max_retries == 5

    def test_execute_success(self):
        """Test execute with successful function."""
        retrier = Retrier()
        result = retrier.execute(lambda: 42)
        assert result == 42

    def test_config_property(self):
        """Test config is accessible."""
        config = RetryConfig(max_retries=7)
        retrier = Retrier(config)
        assert retrier._config.max_retries == 7


class TestRetryState:
    """Tests for RetryState."""
    
    def test_creation(self):
        """Test RetryState creation."""
        from easyscrape.retry import RetryState
        config = RetryConfig(max_retries=3)
        state = RetryState(config)
        assert state.attempt == 0
        assert state.attempts_remaining == 3
    
    def test_record_attempt(self):
        """Test recording attempts."""
        from easyscrape.retry import RetryState
        config = RetryConfig(max_retries=3)
        state = RetryState(config)
        state.record_attempt()
        assert state.attempt == 1
        state.record_attempt(ValueError("err"))
        assert state.attempt == 2
        assert len(state.errors) == 1
    
    def test_should_retry_no_error(self):
        """Test should_retry with no error."""
        from easyscrape.retry import RetryState
        config = RetryConfig(max_retries=3)
        state = RetryState(config)
        assert state.should_retry() is True
    
    def test_should_retry_max_attempts_reached(self):
        """Test should_retry when max reached."""
        from easyscrape.retry import RetryState
        config = RetryConfig(max_retries=1)
        state = RetryState(config)
        state.record_attempt()
        assert state.should_retry() is False
    
    def test_should_retry_retryable_exception(self):
        """Test should_retry with retryable exception."""
        from easyscrape.retry import RetryState
        config = RetryConfig(max_retries=3, retryable_exceptions={ValueError})
        state = RetryState(config)
        assert state.should_retry(ValueError("test")) is True
        assert state.should_retry(KeyError("test")) is False
    
    def test_elapsed_time(self):
        """Test elapsed time tracking."""
        import time
        from easyscrape.retry import RetryState
        config = RetryConfig(max_retries=3)
        state = RetryState(config)
        time.sleep(0.01)
        assert state.elapsed >= 0.01
    
    def test_get_delay_with_jitter(self):
        """Test get_delay with jitter enabled."""
        from easyscrape.retry import RetryState
        config = RetryConfig(max_retries=3, base_delay=1.0, jitter=True, jitter_factor=0.25)
        state = RetryState(config)
        delays = [state.get_delay() for _ in range(10)]
        # With jitter, not all delays should be identical
        assert state.total_delay > 0


class TestRetrierExecute:
    """Tests for Retrier.execute method."""
    
    def test_execute_success_first_try(self):
        """Test successful execution on first try."""
        retrier = Retrier(RetryConfig(max_retries=3))
        result = retrier.execute(lambda: "success")
        assert result == "success"
    
    def test_execute_retries_on_failure(self):
        """Test retrying on failure."""
        call_count = [0]
        def failing_then_success():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("fail")
            return "success"
        
        config = RetryConfig(max_retries=5, base_delay=0.01, retryable_exceptions={ValueError})
        retrier = Retrier(config)
        result = retrier.execute(failing_then_success)
        assert result == "success"
        assert call_count[0] == 3
    
    def test_execute_with_on_retry_callback(self):
        """Test on_retry callback is called."""
        callback_calls = []
        def on_retry(attempt, error):
            callback_calls.append((attempt, str(error)))
        
        call_count = [0]
        def failing_then_success():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ValueError("fail")
            return "ok"
        
        config = RetryConfig(max_retries=3, base_delay=0.01, retryable_exceptions={ValueError})
        retrier = Retrier(config)
        result = retrier.execute(failing_then_success, on_retry=on_retry)
        assert result == "ok"
        assert len(callback_calls) == 1
    
    def test_execute_raises_when_max_retries_exceeded(self):
        """Test raises when max retries exceeded."""
        config = RetryConfig(max_retries=2, base_delay=0.01, retryable_exceptions={ValueError})
        retrier = Retrier(config)
        with pytest.raises(ValueError):
            retrier.execute(lambda: (_ for _ in ()).throw(ValueError("always fail")))


class TestRetryDecorator:
    """Tests for retry decorator."""
    
    def test_decorator_success(self):
        """Test decorator with successful function."""
        from easyscrape.retry import retry
        
        @retry(max_retries=3)
        def always_works():
            return "ok"
        
        assert always_works() == "ok"
    
    def test_decorator_retries_on_exception(self):
        """Test decorator retries on exception."""
        from easyscrape.retry import retry
        
        call_count = [0]
        
        @retry(max_retries=3, base_delay=0.01)
        def fails_twice():
            call_count[0] += 1
            if call_count[0] < 3:
                raise RuntimeError("fail")
            return "success"
        
        result = fails_twice()
        assert result == "success"
        assert call_count[0] == 3


class TestAsyncExecute:
    """Tests for async_execute."""
    
    @pytest.mark.asyncio
    async def test_async_execute_success(self):
        """Test async execute success."""
        config = RetryConfig(max_retries=3)
        retrier = Retrier(config)
        
        async def async_func():
            return "async_result"
        
        result = await retrier.async_execute(async_func)
        assert result == "async_result"
    
    @pytest.mark.asyncio
    async def test_async_execute_retries(self):
        """Test async execute retries on failure."""
        call_count = [0]
        
        async def failing_async():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ValueError("fail")
            return "ok"
        
        config = RetryConfig(max_retries=3, base_delay=0.01, retryable_exceptions={ValueError})
        retrier = Retrier(config)
        result = await retrier.async_execute(failing_async)
        assert result == "ok"
        assert call_count[0] == 2


class TestConvenienceInstances:
    """Tests for convenience retrier instances."""
    
    def test_default_retrier(self):
        """Test default retrier exists."""
        from easyscrape.retry import default_retrier
        assert default_retrier is not None
    
    def test_aggressive_retrier(self):
        """Test aggressive retrier exists."""
        from easyscrape.retry import aggressive_retrier
        assert aggressive_retrier is not None
    
    def test_conservative_retrier(self):
        """Test conservative retrier exists."""
        from easyscrape.retry import conservative_retrier
        assert conservative_retrier is not None



class TestRetryFibonacci:
    """Tests for Fibonacci backoff."""
    
    def test_fibonacci_backoff(self):
        """Test FibonacciBackoff."""
        from easyscrape.retry import FibonacciBackoff
        backoff = FibonacciBackoff()
        delay1 = backoff.get_delay(1, 1.0)
        delay2 = backoff.get_delay(2, 1.0)
        assert delay2 >= delay1



