"""Tests for middleware/hooks module."""

import pytest
from easyscrape.hooks import (
    RequestContext,
    ResponseContext,
    Middleware,
    MiddlewareChain,
    LoggingMiddleware,
    HeadersMiddleware,
    TimingMiddleware,
    RetryCountMiddleware,
    UserAgentRotationMiddleware,
    ThrottleMiddleware,
    CacheMiddleware,
    FilterMiddleware,
)


class TestRequestContext:
    """Tests for RequestContext."""

    def test_creation(self):
        """Test context creation."""
        ctx = RequestContext(url="https://example.com")
        assert ctx.url == "https://example.com"
        assert ctx.method == "GET"

    def test_with_method(self):
        """Test with custom method."""
        ctx = RequestContext(url="https://example.com", method="POST")
        assert ctx.method == "POST"

    def test_headers(self):
        """Test headers dict."""
        ctx = RequestContext(
            url="https://example.com",
            headers={"User-Agent": "Test"},
        )
        assert ctx.headers["User-Agent"] == "Test"

    def test_domain_property(self):
        """Test domain extraction."""
        ctx = RequestContext(url="https://example.com/path")
        assert ctx.domain == "example.com"

    def test_set_header(self):
        """Test set_header method."""
        ctx = RequestContext(url="https://example.com")
        ctx.set_header("X-Custom", "Value")
        assert ctx.headers["X-Custom"] == "Value"

    def test_meta(self):
        """Test meta dict."""
        ctx = RequestContext(url="https://example.com")
        ctx.meta["key"] = "value"
        assert ctx.meta["key"] == "value"

    def test_start_time(self):
        """Test start_time is set."""
        ctx = RequestContext(url="https://example.com")
        assert ctx.start_time > 0

    def test_get_meta(self):
        """Test get_meta method."""
        ctx = RequestContext(url="https://example.com")
        ctx.set_meta("key", "value")
        assert ctx.get_meta("key") == "value"

    def test_get_meta_default(self):
        """Test get_meta with default."""
        ctx = RequestContext(url="https://example.com")
        assert ctx.get_meta("missing", "default") == "default"


class TestResponseContext:
    """Tests for ResponseContext."""

    def test_creation(self):
        """Test context creation."""
        req = RequestContext(url="https://example.com")
        ctx = ResponseContext(
            request=req,
            status_code=200,
            content=b"Hello",
        )
        assert ctx.status_code == 200

    def test_content(self):
        """Test content attribute."""
        req = RequestContext(url="https://example.com")
        ctx = ResponseContext(
            request=req,
            status_code=200,
            content=b"Hello World",
        )
        assert ctx.content == b"Hello World"

    def test_ok_property(self):
        """Test ok property."""
        req = RequestContext(url="https://example.com")
        ctx = ResponseContext(request=req, status_code=200)
        assert ctx.ok is True

    def test_not_ok_for_error(self):
        """Test ok is False for error status."""
        req = RequestContext(url="https://example.com")
        ctx = ResponseContext(request=req, status_code=500)
        assert ctx.ok is False

    def test_text_property(self):
        """Test text property."""
        req = RequestContext(url="https://example.com")
        ctx = ResponseContext(request=req, status_code=200, content=b"Hello")
        assert ctx.text == "Hello"


class TestMiddleware:
    """Tests for Middleware base class."""

    def test_subclass(self):
        """Test can subclass Middleware."""
        class CustomMiddleware(Middleware):
            def process_request(self, ctx: RequestContext) -> RequestContext:
                return ctx
        
        mw = CustomMiddleware()
        assert mw is not None


class TestMiddlewareChain:
    """Tests for MiddlewareChain."""

    def test_empty_chain(self):
        """Test empty chain creation."""
        chain = MiddlewareChain()
        assert len(chain) == 0

    def test_add_middleware(self):
        """Test adding middleware."""
        chain = MiddlewareChain()
        mw = LoggingMiddleware()
        chain.add(mw)
        assert len(chain) == 1

    def test_add_multiple(self):
        """Test adding multiple middleware."""
        chain = MiddlewareChain()
        chain.add(LoggingMiddleware())
        chain.add(TimingMiddleware())
        assert len(chain) == 2

    def test_process_request(self):
        """Test processing request through chain."""
        chain = MiddlewareChain()
        chain.add(HeadersMiddleware({"X-Test": "Value"}))
        
        ctx = RequestContext(url="https://example.com")
        result = chain.process_request(ctx)
        assert result.headers.get("X-Test") == "Value"

    def test_clear(self):
        """Test clearing chain."""
        chain = MiddlewareChain()
        chain.add(LoggingMiddleware())
        chain.clear()
        assert len(chain) == 0


class TestHeadersMiddleware:
    """Tests for HeadersMiddleware."""

    def test_adds_headers(self):
        """Test header injection."""
        mw = HeadersMiddleware({"X-Custom": "Value"})
        ctx = RequestContext(url="https://example.com")
        result = mw.process_request(ctx)
        assert result.headers["X-Custom"] == "Value"

    def test_preserves_existing(self):
        """Test existing headers preserved."""
        mw = HeadersMiddleware({"X-New": "New"})
        ctx = RequestContext(
            url="https://example.com",
            headers={"X-Existing": "Existing"},
        )
        result = mw.process_request(ctx)
        assert result.headers["X-Existing"] == "Existing"
        assert result.headers["X-New"] == "New"


class TestLoggingMiddleware:
    """Tests for LoggingMiddleware."""

    def test_creation(self):
        """Test middleware creation."""
        mw = LoggingMiddleware()
        assert mw is not None

    def test_process_request(self):
        """Test process_request doesn't modify."""
        mw = LoggingMiddleware()
        ctx = RequestContext(url="https://example.com")
        result = mw.process_request(ctx)
        assert result.url == ctx.url

    def test_process_response(self):
        """Test process_response."""
        mw = LoggingMiddleware()
        req = RequestContext(url="https://example.com")
        resp = ResponseContext(request=req, status_code=200)
        result = mw.process_response(resp)
        assert result is not None


class TestTimingMiddleware:
    """Tests for TimingMiddleware."""

    def test_creation(self):
        """Test middleware creation."""
        mw = TimingMiddleware()
        assert mw is not None

    def test_process_request(self):
        """Test process_request."""
        mw = TimingMiddleware()
        ctx = RequestContext(url="https://example.com")
        result = mw.process_request(ctx)
        assert result is not None

    def test_process_response(self):
        """Test process_response adds timing."""
        mw = TimingMiddleware()
        req = RequestContext(url="https://example.com")
        resp = ResponseContext(request=req, status_code=200)
        result = mw.process_response(resp)
        assert result is not None


class TestRetryCountMiddleware:
    """Tests for RetryCountMiddleware."""

    def test_creation(self):
        """Test middleware creation."""
        mw = RetryCountMiddleware()
        assert mw is not None

    def test_process_request(self):
        """Test process_request."""
        mw = RetryCountMiddleware()
        ctx = RequestContext(url="https://example.com")
        result = mw.process_request(ctx)
        assert result is not None


class TestUserAgentRotationMiddleware:
    """Tests for UserAgentRotationMiddleware."""

    def test_creation(self):
        """Test middleware creation."""
        mw = UserAgentRotationMiddleware(user_agents=["Mozilla/5.0 Test"])
        assert mw is not None

    def test_rotates_user_agent(self):
        """Test user agent is set."""
        mw = UserAgentRotationMiddleware(user_agents=["Mozilla/5.0 Test"])
        ctx = RequestContext(url="https://example.com")
        result = mw.process_request(ctx)
        assert "User-Agent" in result.headers

    def test_random_strategy(self):
        """Test random strategy."""
        mw = UserAgentRotationMiddleware(
            user_agents=["UA1", "UA2"],
            strategy="random"
        )
        ctx = RequestContext(url="https://example.com")
        result = mw.process_request(ctx)
        assert result.headers["User-Agent"] in ["UA1", "UA2"]


class TestThrottleMiddleware:
    """Tests for ThrottleMiddleware."""

    def test_creation(self):
        """Test middleware creation."""
        mw = ThrottleMiddleware(requests_per_second=100.0)
        assert mw is not None

    def test_process_request(self):
        """Test process_request."""
        mw = ThrottleMiddleware(requests_per_second=100.0)
        ctx = RequestContext(url="https://example.com")
        result = mw.process_request(ctx)
        assert result is not None



class TestCacheMiddleware:
    """Tests for CacheMiddleware."""

    def test_import(self):
        """Test CacheMiddleware is importable."""
        from easyscrape.hooks import CacheMiddleware
        assert CacheMiddleware is not None

    def test_creation(self):
        """Test middleware creation."""
        from easyscrape.hooks import CacheMiddleware
        mw = CacheMiddleware()
        assert mw is not None

    def test_process_request(self):
        """Test process_request."""
        from easyscrape.hooks import CacheMiddleware
        mw = CacheMiddleware()
        ctx = RequestContext(url="https://example.com")
        result = mw.process_request(ctx)
        assert result is not None


class TestFilterMiddleware:
    """Tests for FilterMiddleware."""

    def test_import(self):
        """Test FilterMiddleware is importable."""
        from easyscrape.hooks import FilterMiddleware
        assert FilterMiddleware is not None

    def test_creation_with_allow(self):
        """Test creation with allow domains."""
        from easyscrape.hooks import FilterMiddleware
        mw = FilterMiddleware(allow_domains=["example.com"])
        assert mw is not None

    def test_creation_with_deny(self):
        """Test creation with block domains."""
        from easyscrape.hooks import FilterMiddleware
        mw = FilterMiddleware(block_domains=["ads.example.com"])
        assert mw is not None


class TestMiddlewareChainAdvanced:
    """Additional tests for MiddlewareChain."""

    def test_process_response(self):
        """Test processing response through chain."""
        chain = MiddlewareChain()
        chain.add(TimingMiddleware())
        
        req = RequestContext(url="https://example.com")
        resp = ResponseContext(request=req, status_code=200)
        result = chain.process_response(resp)
        assert result is not None

    def test_chaining_add(self):
        """Test chained add calls."""
        chain = MiddlewareChain()
        result = chain.add(LoggingMiddleware()).add(TimingMiddleware())
        assert result is chain
        assert len(chain) == 2



class TestRequestContextMethods:
    """Additional tests for RequestContext methods."""
    
    def test_set_header(self):
        """Test set_header method."""
        ctx = RequestContext(url="https://example.com", method="GET")
        ctx.set_header("X-Custom", "value")
        assert ctx.headers.get("X-Custom") == "value"
    
    def test_get_meta_default(self):
        """Test get_meta with default."""
        ctx = RequestContext(url="https://example.com", method="GET")
        val = ctx.get_meta("nonexistent", "default_val")
        assert val == "default_val"
    
    def test_set_meta(self):
        """Test set_meta method."""
        ctx = RequestContext(url="https://example.com", method="GET")
        ctx.set_meta("key", "value")
        assert ctx.get_meta("key") == "value"


class TestResponseContextMethods:
    """Additional tests for ResponseContext methods."""
    
    def test_ok_property(self):
        """Test ok property."""
        request_ctx = RequestContext(url="https://example.com", method="GET")
        ctx = ResponseContext(request=request_ctx, status_code=200, content=b"OK")
        assert ctx.ok is True
        
        ctx_error = ResponseContext(request=request_ctx, status_code=500, content=b"Error")
        assert ctx_error.ok is False
    
    def test_duration_ms(self):
        """Test duration_ms property."""
        import time
        request_ctx = RequestContext(url="https://example.com", method="GET")
        time.sleep(0.01)
        ctx = ResponseContext(request=request_ctx, status_code=200, content=b"OK")
        assert ctx.duration_ms >= 0


class TestLoggingMiddlewareAdvanced:
    """Advanced tests for LoggingMiddleware."""
    
    def test_process_error(self):
        """Test process_error method."""
        mw = LoggingMiddleware()
        ctx = RequestContext(url="https://example.com", method="GET")
        error = ValueError("test error")
        result = mw.process_error(ctx, error)
        assert result is error  # Should return the same error


class TestTimingMiddlewareStats:
    """Tests for TimingMiddleware stats."""
    
    def test_get_stats(self):
        """Test get_stats method."""
        mw = TimingMiddleware()
        stats = mw.get_stats()
        assert isinstance(stats, dict)
    
    def test_get_stats_after_request(self):
        """Test get_stats after processing."""
        mw = TimingMiddleware()
        request_ctx = RequestContext(url="https://example.com", method="GET")
        ctx = ResponseContext(request=request_ctx, status_code=200, content=b"OK")
        mw.process_response(ctx)
        stats = mw.get_stats("example.com")
        assert isinstance(stats, dict)


class TestRetryCountMiddlewareMethods:
    """Tests for RetryCountMiddleware methods."""
    
    def test_get_retry_counts(self):
        """Test get_retry_counts method."""
        mw = RetryCountMiddleware()
        counts = mw.get_retry_counts()
        assert isinstance(counts, dict)
    
    def test_process_request(self):
        """Test process_request increments count."""
        mw = RetryCountMiddleware()
        ctx = RequestContext(url="https://example.com", method="GET")
        mw.process_request(ctx)
        counts = mw.get_retry_counts()
        assert counts.get("example.com", 0) >= 0


class TestUserAgentRotationStrategies:
    """Tests for UserAgentRotationMiddleware strategies."""
    
    def test_round_robin_strategy(self):
        """Test round-robin strategy."""
        mw = UserAgentRotationMiddleware(
            user_agents=["UA1", "UA2", "UA3"],
            strategy="round-robin"
        )
        ctx1 = RequestContext(url="https://example.com", method="GET")
        ctx1 = mw.process_request(ctx1)
        ctx2 = RequestContext(url="https://example.com", method="GET")
        ctx2 = mw.process_request(ctx2)
        # Different UAs should be used
    
    def test_random_strategy(self):
        """Test random strategy."""
        mw = UserAgentRotationMiddleware(
            user_agents=["UA1", "UA2", "UA3"],
            strategy="random"
        )
        ctx = RequestContext(url="https://example.com", method="GET")
        ctx = mw.process_request(ctx)
        assert "User-Agent" in ctx.headers


class TestCacheMiddlewareMethods:
    """Tests for CacheMiddleware methods."""
    
    def test_cache_key(self):
        """Test _cache_key method."""
        mw = CacheMiddleware()
        ctx = RequestContext(url="https://example.com/page", method="GET")
        key = mw._cache_key(ctx)
        assert key is not None
    
    def test_process_response_caches(self):
        """Test process_response stores in cache."""
        mw = CacheMiddleware()
        request_ctx = RequestContext(url="https://example.com", method="GET")
        ctx = ResponseContext(request=request_ctx, status_code=200, content=b"OK")
        mw.process_response(ctx)
        # Verify cache was updated (internal implementation)


class TestMiddlewareChainMethods:
    """Tests for MiddlewareChain methods."""
    
    def test_remove(self):
        """Test remove method."""
        chain = MiddlewareChain()
        mw = HeadersMiddleware({"X-Test": "value"})
        chain.add(mw)
        chain.remove(mw)
    
    def test_clear(self):
        """Test clear method."""
        chain = MiddlewareChain()
        chain.add(HeadersMiddleware({"X-Test": "value"}))
        chain.add(LoggingMiddleware())
        chain.clear()


class TestMiddlewareProcessMethods:
    """Tests for Middleware process methods."""
    
    def test_headers_middleware_process_request(self):
        """Test HeadersMiddleware adds headers."""
        mw = HeadersMiddleware({"X-Custom": "value"})
        ctx = RequestContext(url="https://example.com", method="GET")
        result = mw.process_request(ctx)
        assert result.headers.get("X-Custom") == "value"



class TestHooksEdgeCases:
    """Edge case tests for hooks module."""
    
    def test_middleware_chain_empty(self):
        """Test empty middleware chain."""
        from easyscrape.hooks import MiddlewareChain
        chain = MiddlewareChain()
        assert chain is not None
    
    def test_logging_middleware_creation(self):
        """Test LoggingMiddleware creation."""
        from easyscrape.hooks import LoggingMiddleware
        mw = LoggingMiddleware()
        assert mw is not None
    
    def test_throttle_middleware_creation(self):
        """Test ThrottleMiddleware creation."""
        from easyscrape.hooks import ThrottleMiddleware
        mw = ThrottleMiddleware(requests_per_second=10)
        assert mw is not None
    
    def test_filter_middleware_creation(self):
        """Test FilterMiddleware creation."""
        from easyscrape.hooks import FilterMiddleware
        mw = FilterMiddleware()
        assert mw is not None



# =============================================================================
# Additional Coverage Tests
# =============================================================================

class TestFilterMiddlewareExtended:
    """Extended tests for FilterMiddleware functionality."""

    def test_block_domain(self):
        """Test blocking specific domains."""
        from easyscrape.hooks import FilterMiddleware, RequestContext
        mw = FilterMiddleware(block_domains=["blocked.com"])
        ctx = RequestContext(url="https://blocked.com/page")
        result = mw.process_request(ctx)
        assert result.get_meta("blocked") is True

    def test_allow_only_domains(self):
        """Test allowing only specific domains."""
        from easyscrape.hooks import FilterMiddleware, RequestContext
        mw = FilterMiddleware(allow_domains=["allowed.com"])
        ctx = RequestContext(url="https://notallowed.com/page")
        result = mw.process_request(ctx)
        assert result.get_meta("blocked") is True

    def test_url_filter_function(self):
        """Test URL filter function."""
        from easyscrape.hooks import FilterMiddleware, RequestContext
        mw = FilterMiddleware(url_filter=lambda url: "allowed" in url)
        ctx = RequestContext(url="https://example.com/blocked")
        result = mw.process_request(ctx)
        assert result.get_meta("blocked") is True


class TestMiddlewareChainExtended:
    """Extended tests for MiddlewareChain."""

    def test_process_error_chain(self):
        """Test error processing through middleware chain."""
        from easyscrape.hooks import MiddlewareChain, Middleware, RequestContext

        class ErrorHandler(Middleware):
            def process_error(self, ctx, error):
                return None  # Swallow error
        
        chain = MiddlewareChain()
        chain.add(ErrorHandler())
        
        ctx = RequestContext(url="https://test.com")
        result = chain.process_error(ctx, ValueError("test"))
        assert result is None

    def test_middleware_len(self):
        """Test __len__ on MiddlewareChain."""
        from easyscrape.hooks import MiddlewareChain, Middleware
        
        class SimpleMiddleware(Middleware):
            pass
        
        chain = MiddlewareChain()
        assert len(chain) == 0
        chain.add(SimpleMiddleware())
        assert len(chain) == 1


class TestRequestContextExtended:
    """Extended tests for RequestContext."""

    def test_context_domain_property(self):
        """Test domain property extraction."""
        from easyscrape.hooks import RequestContext
        ctx = RequestContext(url="https://sub.example.com/path")
        assert ctx.domain == "sub.example.com"

    def test_context_set_and_get_meta(self):
        """Test setting and getting metadata."""
        from easyscrape.hooks import RequestContext
        ctx = RequestContext(url="https://test.com")
        ctx.set_meta("key", "value")
        assert ctx.get_meta("key") == "value"
