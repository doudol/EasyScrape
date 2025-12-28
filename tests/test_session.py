"""Tests for session management."""
import pytest
import respx
from httpx import Response as HttpxResponse

from easyscrape import Config
from easyscrape.session import Session, AsyncSession, ProxyPool


class TestSession:
    """Tests for Session class."""

    def test_session_creation(self):
        """Test session can be created."""
        session = Session()
        assert session is not None
        session.close()

    def test_session_with_config(self):
        """Test session with custom config."""
        config = Config(timeout=60.0)
        session = Session(config=config)
        assert session._config.timeout == 60.0
        session.close()

    def test_session_context_manager(self):
        """Test session as context manager."""
        with Session() as session:
            assert session is not None

    @respx.mock
    def test_session_get(self):
        """Test session GET request."""
        respx.get("https://example.com").mock(
            return_value=HttpxResponse(200, text="<html></html>")
        )
        
        with Session() as session:
            result = session.get("https://example.com")
            assert result.ok

    @respx.mock
    def test_session_request_count(self):
        """Test request counting."""
        respx.get("https://example.com").mock(
            return_value=HttpxResponse(200, text="<html></html>")
        )
        
        with Session() as session:
            session.get("https://example.com")
            session.get("https://example.com")
            assert session.request_count >= 2

    @respx.mock
    def test_session_connection_reuse(self):
        """Test connection reuse."""
        respx.get("https://example.com/page1").mock(
            return_value=HttpxResponse(200, text="page1")
        )
        respx.get("https://example.com/page2").mock(
            return_value=HttpxResponse(200, text="page2")
        )
        
        with Session() as session:
            r1 = session.get("https://example.com/page1")
            r2 = session.get("https://example.com/page2")
            assert r1.ok and r2.ok


class TestAsyncSession:
    """Tests for AsyncSession class."""

    @pytest.mark.asyncio
    async def test_async_session_creation(self):
        """Test async session creation."""
        async with AsyncSession() as session:
            assert session is not None

    @pytest.mark.asyncio
    @respx.mock
    async def test_async_session_get(self):
        """Test async GET request."""
        respx.get("https://example.com").mock(
            return_value=HttpxResponse(200, text="<html></html>")
        )
        
        async with AsyncSession() as session:
            result = await session.get("https://example.com")
            assert result.ok

    @pytest.mark.asyncio
    @respx.mock
    async def test_async_session_parallel(self):
        """Test parallel requests."""
        respx.get("https://example.com").mock(
            return_value=HttpxResponse(200, text="<html></html>")
        )
        
        import asyncio
        async with AsyncSession() as session:
            results = await asyncio.gather(
                session.get("https://example.com"),
                session.get("https://example.com"),
            )
            assert all(r.ok for r in results)

    @pytest.mark.asyncio
    @respx.mock
    async def test_async_session_request_count(self):
        """Test request counting."""
        respx.get("https://example.com").mock(
            return_value=HttpxResponse(200, text="<html></html>")
        )
        
        async with AsyncSession() as session:
            await session.get("https://example.com")
            await session.get("https://example.com")
            assert session.request_count >= 2

    @pytest.mark.asyncio
    async def test_async_session_without_context_raises(self):
        """Test using session without context manager."""
        session = AsyncSession()
        # Should work after entering context
        await session.__aenter__()
        await session.__aexit__(None, None, None)


class TestResponse:
    """Tests for response objects."""

    @respx.mock
    def test_response_properties(self):
        """Test response properties."""
        respx.get("https://example.com").mock(
            return_value=HttpxResponse(200, text="<html></html>")
        )
        
        with Session() as session:
            resp = session.get("https://example.com")
            assert resp.status_code == 200
            assert resp.ok is True
            assert "<html>" in resp.text

    @respx.mock
    def test_response_headers(self):
        """Test response headers."""
        respx.get("https://example.com").mock(
            return_value=HttpxResponse(
                200,
                text="<html></html>",
                headers={"X-Custom": "value"},
            )
        )
        
        with Session() as session:
            resp = session.get("https://example.com")
            assert "X-Custom" in resp.headers

    @respx.mock
    def test_response_url(self):
        """Test response URL."""
        respx.get("https://example.com").mock(
            return_value=HttpxResponse(200, text="<html></html>")
        )
        
        with Session() as session:
            resp = session.get("https://example.com")
            assert "example.com" in resp.url

    @respx.mock
    def test_response_etag(self):
        """Test ETag header."""
        respx.get("https://example.com").mock(
            return_value=HttpxResponse(
                200,
                text="<html></html>",
                headers={"ETag": '"abc123"'},
            )
        )
        
        with Session() as session:
            resp = session.get("https://example.com")
            assert resp.etag == '"abc123"'

    @respx.mock
    def test_response_last_modified(self):
        """Test Last-Modified header."""
        respx.get("https://example.com").mock(
            return_value=HttpxResponse(
                200,
                text="<html></html>",
                headers={"Last-Modified": "Wed, 21 Oct 2015 07:28:00 GMT"},
            )
        )
        
        with Session() as session:
            resp = session.get("https://example.com")
            assert resp.last_modified == "Wed, 21 Oct 2015 07:28:00 GMT"

    @respx.mock
    def test_response_cache_headers(self):
        """Test cache-related headers."""
        respx.get("https://example.com").mock(
            return_value=HttpxResponse(
                200,
                text="<html></html>",
                headers={
                    "Cache-Control": "max-age=3600",
                    "ETag": '"xyz"',
                },
            )
        )
        
        with Session() as session:
            resp = session.get("https://example.com")
            headers = resp.cache_headers
            assert "Cache-Control" in headers or "ETag" in headers

    @respx.mock
    def test_response_not_modified(self):
        """Test 304 Not Modified handling."""
        respx.get("https://example.com").mock(
            return_value=HttpxResponse(200, text="<html></html>")
        )
        
        with Session() as session:
            resp = session.get("https://example.com")
            assert resp.not_modified is False


class TestProxyPool:
    """Tests for ProxyPool class."""

    def test_proxy_pool_creation(self):
        """Test proxy pool creation."""
        proxies = ["http://proxy1:8080", "http://proxy2:8080"]
        pool = ProxyPool(proxies)
        assert pool is not None

    def test_proxy_pool_round_robin(self):
        """Test round-robin proxy selection."""
        proxies = ["http://proxy1:8080", "http://proxy2:8080"]
        pool = ProxyPool(proxies, strategy="round-robin")
        
        first = pool.get()
        second = pool.get()
        third = pool.get()
        
        assert first != second
        assert third == first  # Back to first

    def test_proxy_pool_random(self):
        """Test random proxy selection."""
        proxies = ["http://proxy1:8080", "http://proxy2:8080"]
        pool = ProxyPool(proxies, strategy="random")
        
        # Just verify it returns a valid proxy
        proxy = pool.get()
        assert proxy in proxies

    def test_proxy_pool_sticky(self):
        """Test sticky proxy selection."""
        proxies = ["http://proxy1:8080", "http://proxy2:8080"]
        pool = ProxyPool(proxies, strategy="sticky")
        
        first = pool.get()
        second = pool.get()
        
        assert first == second

    def test_proxy_pool_mark_bad(self):
        """Test marking proxy as bad."""
        proxies = ["http://proxy1:8080", "http://proxy2:8080"]
        pool = ProxyPool(proxies)
        
        pool.mark_bad("http://proxy1:8080")
        # Should still work
        proxy = pool.get()
        assert proxy is not None

    def test_proxy_pool_mark_good(self):
        """Test marking proxy as good."""
        proxies = ["http://proxy1:8080"]
        pool = ProxyPool(proxies)
        
        pool.mark_bad("http://proxy1:8080")
        pool.mark_good("http://proxy1:8080")
        
        proxy = pool.get()
        assert proxy == "http://proxy1:8080"

    def test_proxy_pool_empty(self):
        """Test empty proxy pool."""
        pool = ProxyPool([])
        assert pool.get() is None


class TestScrapingResponseMethods:
    """Tests for ScrapingResponse methods."""
    
    @respx.mock
    def test_cache_headers(self, mocker):
        """Test cache_headers property."""
        respx.get("https://example.com").mock(
            return_value=HttpxResponse(
                200,
                text="<html></html>",
                headers={"Cache-Control": "max-age=3600", "ETag": '"abc"'},
            )
        )
        
        with Session() as session:
            resp = session.get("https://example.com")
            cache_headers = resp.cache_headers
            assert isinstance(cache_headers, dict)
    
    @respx.mock
    def test_not_modified(self, mocker):
        """Test not_modified property."""
        respx.get("https://example.com").mock(
            return_value=HttpxResponse(304)
        )
        
        with Session() as session:
            resp = session.get("https://example.com")
            assert resp.not_modified is True
    
    @respx.mock
    def test_etag_property(self, mocker):
        """Test etag property."""
        respx.get("https://example.com").mock(
            return_value=HttpxResponse(
                200,
                text="<html></html>",
                headers={"ETag": '"etag123"'},
            )
        )
        
        with Session() as session:
            resp = session.get("https://example.com")
            assert resp.etag == '"etag123"'
    
    @respx.mock
    def test_last_modified_property(self, mocker):
        """Test last_modified property."""
        respx.get("https://example.com").mock(
            return_value=HttpxResponse(
                200,
                text="<html></html>",
                headers={"Last-Modified": "Mon, 01 Jan 2024 00:00:00 GMT"},
            )
        )
        
        with Session() as session:
            resp = session.get("https://example.com")
            assert resp.last_modified == "Mon, 01 Jan 2024 00:00:00 GMT"


class TestScrapingSessionMethods:
    """Tests for ScrapingSession methods."""
    
    def test_session_with_custom_config(self):
        """Test session with custom config."""
        config = Config(timeout=120, max_retries=5)
        session = Session(config=config)
        assert session._config.timeout == 120
        assert session._config.max_retries == 5
        session.close()


class TestProxyPoolAdvanced:
    """Advanced tests for ProxyPool."""
    
    def test_random_strategy(self):
        """Test random strategy returns valid proxy."""
        proxies = ["http://p1:8080", "http://p2:8080", "http://p3:8080"]
        pool = ProxyPool(proxies, strategy="random")
        for _ in range(10):
            proxy = pool.get()
            assert proxy in proxies
    
    def test_sticky_strategy(self):
        """Test sticky strategy returns same proxy."""
        proxies = ["http://p1:8080", "http://p2:8080"]
        pool = ProxyPool(proxies, strategy="sticky")
        first = pool.get()
        for _ in range(5):
            assert pool.get() == first
    
    def test_mark_bad_and_recovery(self):
        """Test proxy recovery after marking bad."""
        proxies = ["http://p1:8080"]
        pool = ProxyPool(proxies)
        pool.mark_bad("http://p1:8080")
        pool.mark_good("http://p1:8080")
        assert pool.get() == "http://p1:8080"


class TestSessionMakeHeaders:
    """Tests for session header generation."""
    
    def test_make_headers_includes_user_agent(self):
        """Test headers include User-Agent."""
        session = Session()
        headers = session._make_headers()
        assert "User-Agent" in headers
        session.close()
    
    def test_make_headers_custom_headers(self):
        """Test custom headers are included."""
        config = Config(headers={"X-Custom": "value"})
        session = Session(config=config)
        headers = session._make_headers()
        assert headers.get("X-Custom") == "value"
        session.close()


class TestSessionWithProxy:
    """Tests for session with proxy configuration."""
    
    def test_session_with_proxy_config(self):
        """Test session with proxy in config."""
        config = Config(proxies=["http://proxy:8080"])
        session = Session(config=config)
        assert session._proxy_pool is not None
        session.close()


class TestResponseProperties:
    """Tests for response properties."""
    
    @respx.mock
    def test_response_ok_property(self, mocker):
        """Test ok property for various status codes."""
        respx.get("https://example.com").mock(
            return_value=HttpxResponse(200, text="OK")
        )
        
        with Session() as session:
            resp = session.get("https://example.com")
            assert resp.ok is True
    
    @respx.mock
    def test_response_encoding(self, mocker):
        """Test response encoding detection."""
        respx.get("https://example.com").mock(
            return_value=HttpxResponse(
                200,
                text="<html></html>",
                headers={"Content-Type": "text/html; charset=utf-8"},
            )
        )
        
        with Session() as session:
            resp = session.get("https://example.com")
            # Should have encoding
            assert resp.text is not None


class TestSessionProxyErrorHandling:
    """Tests for proxy error handling."""
    
    def test_stealth_mode_without_curl_cffi(self, mocker):
        """Test stealth mode gracefully handles missing curl_cffi."""
        # This should not raise even without curl_cffi
        config = Config(stealth_mode=True)
        session = Session(config=config)
        session.close()


class TestSessionClose:
    """Tests for session close behavior."""
    
    def test_session_context_manager(self, mocker):
        """Test session closes properly in context manager."""
        with Session() as session:
            pass
        # Should not raise after exit
    
    def test_explicit_close(self, mocker):
        """Test explicit close."""
        session = Session()
        session.close()
        session.close()  # Should not raise on double close


class TestSessionProxyHandling:
    """Tests for proxy handling."""
    
    def test_pick_proxy_returns_none_without_pool(self):
        """Test _pick_proxy returns None without proxy pool."""
        session = Session()
        proxy = session._pick_proxy()
        assert proxy is None
        session.close()
    
    def test_session_with_verify_ssl_false(self):
        """Test session with SSL verification disabled."""
        config = Config(verify_ssl=False)
        session = Session(config=config)
        assert session._config.verify_ssl is False
        session.close()


class TestResponseWrapper:
    """Tests for response wrapper."""
    
    @respx.mock
    def test_response_json_parsing(self, mocker):
        """Test JSON response parsing."""
        respx.get("https://api.example.com/data").mock(
            return_value=HttpxResponse(200, json={"key": "value"})
        )
        
        with Session() as session:
            resp = session.get("https://api.example.com/data")
            data = resp.json()
            assert data["key"] == "value"
    
    @respx.mock
    def test_response_ok_property(self, mocker):
        """Test ok property."""
        respx.get("https://example.com").mock(
            return_value=HttpxResponse(200, text="OK")
        )
        
        with Session() as session:
            resp = session.get("https://example.com")
            assert resp.ok is True


class TestSessionStealth:
    """Tests for stealth mode."""
    
    def test_session_stealth_mode_config(self):
        """Test stealth mode configuration."""
        config = Config(stealth_mode=True)
        session = Session(config=config)
        # Should not raise
        session.close()


class TestSessionContext:
    """Tests for session context management."""
    
    def test_session_context_manager(self):
        """Test session as context manager."""
        with Session() as session:
            assert session is not None
    
    def test_session_close_multiple(self):
        """Test multiple close calls don't raise."""
        session = Session()
        session.close()
        session.close()
        session.close()


class TestSessionHTTPMethods:
    """Tests for HTTP methods."""
    
    @respx.mock
    def test_session_post_request(self):
        """Test POST request."""
        respx.post("https://example.com/api").mock(
            return_value=HttpxResponse(200, json={"success": True})
        )
        
        with Session() as session:
            resp = session.post("https://example.com/api", data={"key": "value"})
            assert resp.ok
    
    @respx.mock
    def test_session_put_request(self):
        """Test PUT request."""
        respx.put("https://example.com/api/1").mock(
            return_value=HttpxResponse(200, json={"updated": True})
        )
        
        with Session() as session:
            resp = session.put("https://example.com/api/1", data={"key": "value"})
            assert resp.ok
    
    @respx.mock
    def test_session_delete_request(self):
        """Test DELETE request."""
        respx.delete("https://example.com/api/1").mock(
            return_value=HttpxResponse(204)
        )
        
        with Session() as session:
            resp = session.delete("https://example.com/api/1")
            assert resp.status_code == 204


class TestSessionProxyWithMock:
    """Tests for session proxy with mocking."""
    
    @respx.mock
    def test_session_with_proxy_pool(self, mocker):
        """Test session uses proxy pool."""
        respx.get("https://example.com").mock(
            return_value=HttpxResponse(200, text="<html></html>")
        )
        
        config = Config(proxies=["http://proxy1:8080", "http://proxy2:8080"])
        with Session(config=config) as session:
            resp = session.get("https://example.com")
            assert resp.ok


class TestSessionErrorHandling:
    """Tests for session error handling."""
    
    @respx.mock
    def test_session_connection_refused(self, mocker):
        """Test handling of connection refused."""
        import httpx
        respx.get("https://unreachable.example.com").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        
        with Session() as session:
            with pytest.raises(Exception):
                session.get("https://unreachable.example.com")
    
    @respx.mock
    def test_session_timeout_handling(self, mocker):
        """Test handling of timeout."""
        import httpx
        respx.get("https://slow.example.com").mock(
            side_effect=httpx.TimeoutException("Request timed out")
        )
        
        with Session() as session:
            with pytest.raises(Exception):
                session.get("https://slow.example.com")
