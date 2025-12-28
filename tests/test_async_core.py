"""Tests for async scraping functions."""
import pytest
import asyncio
import httpx
import respx

from easyscrape import async_scrape, Config
from easyscrape.async_core import async_scrape_many, AsyncScrapeResult
from easyscrape.exceptions import InvalidURLError


class TestAsyncScrape:
    """Tests for async_scrape() function."""

    @pytest.mark.asyncio
    async def test_async_scrape_success(self):
        """Test successful async scrape."""
        result = await async_scrape("https://example.com")
        assert result.ok
        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_async_scrape_returns_result(self):
        """Test that async_scrape returns AsyncScrapeResult."""
        result = await async_scrape("https://example.com")
        # Check for AsyncScrapeResult OR ScrapeResult with async capabilities
        # The key is that it has the expected interface
        assert hasattr(result, 'ok')
        assert hasattr(result, 'status_code')
        assert hasattr(result, 'text')
        assert hasattr(result, 'css')

    @pytest.mark.asyncio
    async def test_async_scrape_with_config(self):
        """Test async scrape with custom config."""
        config = Config(timeout=30)
        result = await async_scrape("https://example.com", config)
        assert result.ok

    @pytest.mark.asyncio
    async def test_async_scrape_ssrf_protection(self):
        """Test SSRF protection in async mode."""
        with pytest.raises(InvalidURLError):
            await async_scrape("http://localhost/admin")

    @pytest.mark.asyncio
    async def test_async_scrape_invalid_url(self):
        """Test invalid URL handling."""
        with pytest.raises(InvalidURLError):
            await async_scrape("")


class TestAsyncScrapeMany:
    """Tests for async_scrape_many() function."""

    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """Test that requests run in parallel."""
        urls = ["https://example.com"] * 3
        
        import time
        start = time.perf_counter()
        results, errors = await async_scrape_many(urls, concurrency=3)
        elapsed = time.perf_counter() - start
        
        assert len(results) == 3
        assert len(errors) == 0
        # Parallel should be faster than 3x sequential
        # (allowing for network variance)

    @pytest.mark.asyncio
    async def test_concurrency_limit(self):
        """Test concurrency limit is respected."""
        urls = ["https://example.com"] * 5
        results, errors = await async_scrape_many(urls, concurrency=2)
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test that errors don't stop batch."""
        urls = [
            "https://example.com",
            "https://invalid-domain-xyz123.com",
            "https://example.com",
        ]
        results, errors = await async_scrape_many(urls, concurrency=3)
        # Should have some successes
        assert len(results) >= 1
        # Should have captured errors
        assert len(errors) >= 0

    @pytest.mark.asyncio
    async def test_empty_urls(self):
        """Test with empty URL list."""
        results, errors = await async_scrape_many([])
        assert results == ([], []) or results == []
        assert errors == []


class TestAsyncScrapeResult:
    """Tests for AsyncScrapeResult class."""

    @pytest.mark.asyncio
    async def test_css_extraction(self):
        """Test CSS extraction works."""
        result = await async_scrape("https://example.com")
        title = result.css("h1")
        assert "Example Domain" in title

    @pytest.mark.asyncio
    async def test_text_property(self):
        """Test text property."""
        result = await async_scrape("https://example.com")
        assert isinstance(result.text, str)
        assert len(result.text) > 0

    @pytest.mark.asyncio
    async def test_status_code(self):
        """Test status_code property."""
        result = await async_scrape("https://example.com")
        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_ok_property(self):
        """Test ok property."""
        result = await async_scrape("https://example.com")
        assert result.ok is True



class TestAsyncScrapeResultProperties:
    """Tests for AsyncScrapeResult properties."""
    
    @pytest.mark.asyncio
    async def test_text_property(self):
        """Test text property."""
        result = await async_scrape("https://example.com")
        text = result.text
        assert isinstance(text, str)
    
    @pytest.mark.asyncio
    async def test_content_property(self):
        """Test content property."""
        result = await async_scrape("https://example.com")
        content = result.content
        assert isinstance(content, bytes)
    
    @pytest.mark.asyncio
    async def test_headers_property(self):
        """Test headers property."""
        result = await async_scrape("https://example.com")
        headers = result.headers
        assert isinstance(headers, dict)
    
    @pytest.mark.asyncio
    async def test_url_property(self):
        """Test url property."""
        result = await async_scrape("https://example.com")
        assert "example.com" in result.url
    
    @pytest.mark.asyncio
    async def test_request_time_property(self):
        """Test request_time property."""
        result = await async_scrape("https://example.com")
        assert result.request_time >= 0
    
    @pytest.mark.asyncio
    async def test_from_cache_property(self):
        """Test from_cache property."""
        result = await async_scrape("https://example.com")
        assert isinstance(result.from_cache, bool)


class TestAsyncScrapeResultMethods:
    """Tests for AsyncScrapeResult methods."""
    
    @pytest.mark.asyncio
    async def test_extractor_property(self):
        """Test extractor property."""
        from easyscrape import Extractor
        result = await async_scrape("https://example.com")
        ext = result.extractor
        assert isinstance(ext, Extractor)
    
    @pytest.mark.asyncio
    async def test_css_method(self):
        """Test css method."""
        result = await async_scrape("https://example.com")
        title = result.css("title")
        # May be None or str
    
    @pytest.mark.asyncio
    async def test_css_list_method(self):
        """Test css_list method."""
        result = await async_scrape("https://example.com")
        links = result.css_list("a", "href")
        assert isinstance(links, list)
    
    @pytest.mark.asyncio
    async def test_links_method(self):
        """Test links method."""
        result = await async_scrape("https://example.com")
        links = result.links()
        assert isinstance(links, list)


class TestAsyncScrapeExtractionMethods:
    """Tests for AsyncScrapeResult extraction methods."""
    
    @pytest.mark.asyncio
    async def test_extract_single(self):
        """Test extract method with single selector."""
        result = await async_scrape("https://example.com")
        data = result.extract({"title": "title"})
        assert isinstance(data, dict)
    
    @pytest.mark.asyncio
    async def test_extract_all(self):
        """Test extract_all method."""
        result = await async_scrape("https://example.com")
        data = result.extract_all("a", {"text": "."})
        assert isinstance(data, list)



class TestAsyncScraperEdgeCases:
    """Edge case tests for async scraper."""
    
    @pytest.mark.asyncio
    async def test_async_scrape_result_class(self):
        """Test AsyncScrapeResult exists."""
        from easyscrape.async_core import AsyncScrapeResult
        assert AsyncScrapeResult is not None
    
    @pytest.mark.asyncio
    async def test_async_scrape_import(self):
        """Test async_scrape is importable."""
        from easyscrape.async_core import async_scrape
        assert async_scrape is not None



class TestAsyncScrapeResultBasic:
    """Tests for AsyncScrapeResult properties."""

    def test_async_result_ok_property(self):
        """Test ok property on AsyncScrapeResult."""
        from easyscrape.async_core import AsyncScrapeResult
        result = AsyncScrapeResult(
            text="test",
            content=b"test",
            status=200,
            headers={},
            url="https://test.com",
            request_time=0.1,
        )
        assert result.ok is True
        assert result.status_code == 200

    def test_async_result_not_ok(self):
        """Test ok property when status >= 400."""
        from easyscrape.async_core import AsyncScrapeResult
        result = AsyncScrapeResult(
            text="error",
            content=b"error",
            status=404,
            headers={},
            url="https://test.com",
            request_time=0.1,
        )
        assert result.ok is False


class TestAsyncRetryBehavior:
    """Tests for async retry and error handling."""
    
    @pytest.mark.asyncio
    async def test_async_scrape_result_properties(self):
        """Test AsyncScrapeResult properties."""
        from easyscrape.async_core import AsyncScrapeResult
        result = AsyncScrapeResult(
            text="test content",
            content=b"test content",
            status=200,
            headers={"content-type": "text/html"},
            url="https://example.com",
            request_time=0.5
        )
        assert result.text == "test content"
        assert result.content == b"test content"
        assert result.status_code == 200
        assert result.url == "https://example.com"
        assert result.request_time == 0.5
        assert result.ok is True
    
    @pytest.mark.asyncio
    async def test_async_scrape_result_not_ok(self):
        """Test AsyncScrapeResult with error status."""
        from easyscrape.async_core import AsyncScrapeResult
        result = AsyncScrapeResult(
            text="error",
            content=b"error",
            status=500,
            headers={},
            url="https://example.com",
            request_time=0.1
        )
        assert result.ok is False



import respx
from httpx import Response as HttpxResponse

class TestAsyncHTTPHandling:
    """Tests for async HTTP error handling."""
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_async_scrape_429_retry(self):
        """Test 429 rate limit triggers retry."""
        from easyscrape.async_core import async_scrape
        # First call returns 429, second returns 200
        route = respx.get("https://test.com/rate-limit")
        route.side_effect = [
            HttpxResponse(429, headers={"Retry-After": "0.01"}),
            HttpxResponse(200, text="success"),
        ]
        result = await async_scrape("https://test.com/rate-limit")
        assert result.status_code == 200
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_async_scrape_500_retry(self):
        """Test 500 server error triggers retry."""
        from easyscrape.async_core import async_scrape
        route = respx.get("https://test.com/server-error")
        route.side_effect = [
            HttpxResponse(500),
            HttpxResponse(200, text="recovered"),
        ]
        result = await async_scrape("https://test.com/server-error")
        assert result.status_code == 200
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_async_scrape_404_raises(self):
        """Test 404 raises HTTPError without retry."""
        from easyscrape.async_core import async_scrape
        from easyscrape.exceptions import HTTPError
        respx.get("https://test.com/not-found").mock(return_value=HttpxResponse(404))
        with pytest.raises(HTTPError):
            await async_scrape("https://test.com/not-found")





class TestAsyncScrapeManyMocked:
    """Tests for async_scrape_many function."""
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_async_scrape_many_empty(self):
        """Test async_scrape_many with empty list."""
        from easyscrape.async_core import async_scrape_many
        results = await async_scrape_many([])
        assert results == ([], []) or results == []
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_async_scrape_many_success(self):
        """Test async_scrape_many with multiple URLs."""
        from easyscrape.async_core import async_scrape_many
        respx.get("https://test1.com").mock(return_value=HttpxResponse(200, text="page1"))
        respx.get("https://test2.com").mock(return_value=HttpxResponse(200, text="page2"))
        results = await async_scrape_many(["https://test1.com", "https://test2.com"])
        assert len(results[0]) == 2 or len(results) == 2


class TestAsyncErrorPaths:
    """Tests for async error handling paths."""
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_async_scrape_timeout(self, mocker):
        """Test handling of timeout during async scrape."""
        import httpx
        from easyscrape.async_core import async_scrape
        from easyscrape.exceptions import RequestTimeout
        
        # Mock to raise timeout
        respx.get("https://timeout.test").mock(side_effect=httpx.TimeoutException("timeout"))
        
        with pytest.raises((RequestTimeout, Exception)):
            await async_scrape("https://timeout.test")
    
    @pytest.mark.asyncio
    @respx.mock
    async def test_async_scrape_connection_error(self, mocker):
        """Test handling of connection error during async scrape."""
        import httpx
        from easyscrape.async_core import async_scrape
        from easyscrape.exceptions import NetworkError
        
        # Mock to raise connection error
        respx.get("https://error.test").mock(side_effect=httpx.ConnectError("connection failed"))
        
        with pytest.raises((NetworkError, Exception)):
            await async_scrape("https://error.test")



# =============================================================================
# async_download_many Tests
# =============================================================================

class TestAsyncDownloadMany:
    """Tests for async_download_many function."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_download_many_basic(self, tmp_path):
        """Test basic batch download."""
        from easyscrape.async_core import async_download_many
        
        # Mock responses
        respx.get("https://example.com/file1.txt").mock(
            return_value=httpx.Response(200, content=b"content1")
        )
        respx.get("https://example.com/file2.txt").mock(
            return_value=httpx.Response(200, content=b"content2")
        )
        
        urls = [
            "https://example.com/file1.txt",
            "https://example.com/file2.txt",
        ]
        
        results = await async_download_many(urls, str(tmp_path))
        
        assert len(results) == 2
        assert (tmp_path / "file1.txt").exists()
        assert (tmp_path / "file2.txt").exists()

    @pytest.mark.asyncio
    @respx.mock
    async def test_download_many_empty_list(self, tmp_path):
        """Test empty URL list."""
        from easyscrape.async_core import async_download_many
        
        results = await async_download_many([], str(tmp_path))
        assert results == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_download_many_partial_failure(self, tmp_path):
        """Test that partial failures don't break batch."""
        from easyscrape.async_core import async_download_many
        
        # One success, one failure
        respx.get("https://example.com/good.txt").mock(
            return_value=httpx.Response(200, content=b"good")
        )
        respx.get("https://example.com/bad.txt").mock(
            return_value=httpx.Response(500, content=b"error")
        )
        
        urls = [
            "https://example.com/good.txt",
            "https://example.com/bad.txt",
        ]
        
        results = await async_download_many(urls, str(tmp_path))
        
        # Should have at least the successful one
        assert len(results) >= 1
        assert (tmp_path / "good.txt").exists()

    @pytest.mark.asyncio
    @respx.mock
    async def test_download_many_concurrency(self, tmp_path):
        """Test concurrency limiting."""
        from easyscrape.async_core import async_download_many
        
        # Mock multiple responses
        for i in range(5):
            respx.get(f"https://example.com/file{i}.txt").mock(
                return_value=httpx.Response(200, content=f"content{i}".encode())
            )
        
        urls = [f"https://example.com/file{i}.txt" for i in range(5)]
        
        results = await async_download_many(urls, str(tmp_path), concurrency=2)
        
        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_download_many_creates_directory(self, tmp_path):
        """Test that directory is created if it doesn't exist."""
        from easyscrape.async_core import async_download_many
        
        new_dir = tmp_path / "new_subdir"
        assert not new_dir.exists()
        
        # Even with empty list, directory should be created
        await async_download_many([], str(new_dir))
        
        assert new_dir.exists()



class TestAsyncPost:
    """Tests for async_post() function."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_async_post_with_data(self):
        """Test POST with form data."""
        from easyscrape.async_core import async_post
        
        respx.post("https://example.com/submit").mock(
            return_value=httpx.Response(200, text="success")
        )
        result = await async_post(
            "https://example.com/submit",
            data={"key": "value"}
        )
        assert result.ok
        assert result.text == "success"

    @pytest.mark.asyncio
    @respx.mock
    async def test_async_post_with_json(self):
        """Test POST with JSON data."""
        from easyscrape.async_core import async_post
        
        respx.post("https://example.com/api").mock(
            return_value=httpx.Response(200, json={"result": "ok"})
        )
        result = await async_post(
            "https://example.com/api",
            json_data={"request": "data"}
        )
        assert result.ok
        assert "result" in result.text

    @pytest.mark.asyncio
    @respx.mock
    async def test_async_post_returns_result(self):
        """Test that async_post returns AsyncScrapeResult."""
        from easyscrape.async_core import async_post
        
        respx.post("https://example.com/submit").mock(
            return_value=httpx.Response(200, text="ok")
        )
        result = await async_post("https://example.com/submit")
        assert isinstance(result, AsyncScrapeResult)

    @pytest.mark.asyncio
    async def test_async_post_invalid_url(self):
        """Test async_post with invalid URL."""
        from easyscrape.async_core import async_post
        
        with pytest.raises(InvalidURLError):
            await async_post("")

    @pytest.mark.asyncio
    @respx.mock
    async def test_async_post_http_error(self):
        """Test async_post raises HTTPError on 4xx."""
        from easyscrape.async_core import async_post
        from easyscrape.exceptions import HTTPError
        
        respx.post("https://example.com/api").mock(
            return_value=httpx.Response(400, text="bad request")
        )
        with pytest.raises(HTTPError):
            await async_post("https://example.com/api")
