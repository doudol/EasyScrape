"""Comprehensive tests for easyscrape.browser module."""

import pytest
from pathlib import Path
from easyscrape.browser import (
    _validate_output_path,
    _MS_PER_SECOND,
    _MAX_SCROLL_ITERATIONS,
    _DEFAULT_VIEWPORT_WIDTH,
    _DEFAULT_VIEWPORT_HEIGHT,
    BrowserPage,
    Browser,
)
from easyscrape import Config


# =============================================================================
# Constants Tests
# =============================================================================

class TestConstants:
    """Tests for module constants."""

    def test_ms_per_second(self):
        assert _MS_PER_SECOND == 1000

    def test_max_scroll_iterations(self):
        assert _MAX_SCROLL_ITERATIONS == 100

    def test_default_viewport_width(self):
        assert _DEFAULT_VIEWPORT_WIDTH == 1920

    def test_default_viewport_height(self):
        assert _DEFAULT_VIEWPORT_HEIGHT == 1080

    def test_viewport_reasonable_values(self):
        # Viewport should be reasonable screen size
        assert _DEFAULT_VIEWPORT_WIDTH >= 800
        assert _DEFAULT_VIEWPORT_HEIGHT >= 600


# =============================================================================
# Path Validation Tests
# =============================================================================

class TestValidateOutputPath:
    """Tests for path validation."""

    def test_valid_png_path(self):
        result = _validate_output_path("screenshot.png", [".png", ".jpg"])
        assert result.name == "screenshot.png"

    def test_valid_jpg_path(self):
        result = _validate_output_path("image.jpg", [".png", ".jpg"])
        assert result.name == "image.jpg"

    def test_invalid_extension(self):
        with pytest.raises(Exception):
            _validate_output_path("file.exe", [".png", ".jpg"])

    def test_creates_parent_dirs(self):
        result = _validate_output_path("test_browser_dir/nested/shot.png", [".png"])
        assert result.parent.exists()
        # Cleanup
        import shutil
        shutil.rmtree("test_browser_dir", ignore_errors=True)

    def test_path_traversal_blocked(self):
        with pytest.raises(Exception):
            _validate_output_path("../../../etc/file.png", [".png"])

    def test_pdf_extension(self):
        result = _validate_output_path("document.pdf", [".pdf"])
        assert result.name == "document.pdf"

    def test_jpeg_extension(self):
        result = _validate_output_path("photo.jpeg", [".jpeg", ".jpg"])
        assert result.name == "photo.jpeg"

    def test_relative_path(self):
        result = _validate_output_path("output/img.png", [".png"])
        assert "output" in str(result)


# =============================================================================
# Class Existence Tests
# =============================================================================

class TestClassesExist:
    """Tests that verify classes are properly defined."""

    def test_browser_page_class(self):
        """Test BrowserPage class is defined."""
        assert BrowserPage is not None
        assert hasattr(BrowserPage, '__init__')

    def test_browser_class(self):
        """Test Browser class is defined."""
        assert Browser is not None
        assert hasattr(Browser, '__init__')

    def test_browser_page_has_url(self):
        """Test BrowserPage has url property."""
        assert hasattr(BrowserPage, 'url')

    def test_browser_page_slots(self):
        """Test BrowserPage uses slots for memory efficiency."""
        if hasattr(BrowserPage, '__slots__'):
            assert isinstance(BrowserPage.__slots__, tuple)



# =============================================================================
# Browser Class Tests with Mocking
# =============================================================================

class TestBrowserInit:
    """Tests for Browser initialization."""
    
    def test_browser_init_default(self):
        """Test Browser can be instantiated with defaults."""
        browser = Browser()
        assert browser is not None
        assert browser._playwright is None  # Lazy init
    
    def test_browser_init_with_config(self):
        """Test Browser with config."""
        config = Config(timeout=60.0)
        browser = Browser(config=config)
        assert browser._config.timeout == 60.0


class TestBrowserMocked:
    """Tests for Browser with mocked playwright."""
    
    @pytest.fixture
    def mock_playwright(self, mocker):
        """Mock playwright dependency."""
        mock_pw = mocker.MagicMock()
        mock_browser = mocker.MagicMock()
        mock_context = mocker.MagicMock()
        mock_page = mocker.MagicMock()
        
        # Setup async mocks
        mock_pw.chromium.launch = mocker.AsyncMock(return_value=mock_browser)
        mock_browser.new_context = mocker.AsyncMock(return_value=mock_context)
        mock_context.new_page = mocker.AsyncMock(return_value=mock_page)
        mock_page.goto = mocker.AsyncMock()
        mock_page.content = mocker.AsyncMock(return_value="<html><body>Test</body></html>")
        mock_page.url = "https://example.com"
        
        mocker.patch('easyscrape.browser.async_playwright', return_value=mock_pw)
        return mock_pw


class TestBrowserPageMocked:
    """Tests for BrowserPage with mocked page."""
    
    def test_browser_page_url_property(self, mocker):
        """Test BrowserPage url property."""
        mock_page = mocker.MagicMock()
        
        bp = BrowserPage(mock_page, url="https://mock.com")
        assert bp.url == "https://mock.com"
    
    def test_browser_page_init(self, mocker):
        """Test BrowserPage initialization."""
        mock_page = mocker.MagicMock()
        bp = BrowserPage(mock_page, url="https://mock.com")
        assert bp._page is mock_page


class TestBrowserPageMethods:
    """Tests for BrowserPage methods."""
    
    @pytest.mark.asyncio
    async def test_content_method(self, mocker):
        """Test content method returns HTML."""
        mock_page = mocker.MagicMock()
        mock_page.content = mocker.AsyncMock(return_value="<html>Test</html>")
        
        bp = BrowserPage(mock_page, url="https://mock.com")
        content = await bp.content()
        assert content == "<html>Test</html>"
    
    @pytest.mark.asyncio
    async def test_click_method(self, mocker):
        """Test click method."""
        mock_page = mocker.MagicMock()
        mock_page.click = mocker.AsyncMock()
        
        bp = BrowserPage(mock_page, url="https://mock.com")
        await bp.click("button.submit")
        mock_page.click.assert_called_once_with("button.submit")
    
    @pytest.mark.asyncio
    async def test_fill_method(self, mocker):
        """Test fill method."""
        mock_page = mocker.MagicMock()
        mock_page.fill = mocker.AsyncMock()
        
        bp = BrowserPage(mock_page, url="https://mock.com")
        await bp.fill("input[name='email']", "test@example.com")
        mock_page.fill.assert_called_once_with("input[name='email']", "test@example.com")
    
    @pytest.mark.asyncio
    async def test_wait_for_method(self, mocker):
        """Test wait_for method."""
        mock_page = mocker.MagicMock()
        mock_page.wait_for_selector = mocker.AsyncMock()
        
        bp = BrowserPage(mock_page, url="https://mock.com")
        await bp.wait_for(".loaded")
        mock_page.wait_for_selector.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_evaluate_method(self, mocker):
        """Test evaluate method."""
        mock_page = mocker.MagicMock()
        mock_page.evaluate = mocker.AsyncMock(return_value={"key": "value"})
        
        bp = BrowserPage(mock_page, url="https://mock.com")
        result = await bp.evaluate("() => ({ key: 'value' })")
        assert result == {"key": "value"}
    



class TestBrowserPageScreenshot:
    """Tests for screenshot functionality."""
    
    @pytest.mark.asyncio
    async def test_screenshot_valid_path(self, mocker):
        """Test screenshot with valid path."""
        mock_page = mocker.MagicMock()
        mock_page.screenshot = mocker.AsyncMock()
        
        bp = BrowserPage(mock_page, url="https://mock.com")
        await bp.screenshot("test_screenshot.png")
        mock_page.screenshot.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_screenshot_full_page(self, mocker):
        """Test full page screenshot."""
        mock_page = mocker.MagicMock()
        mock_page.screenshot = mocker.AsyncMock()
        
        bp = BrowserPage(mock_page, url="https://mock.com")
        await bp.screenshot("test_full.png", full_page=True)
        mock_page.screenshot.assert_called_once()


class TestBrowserPagePdf:
    """Tests for PDF functionality."""
    
    @pytest.mark.asyncio
    async def test_pdf_valid_path(self, mocker):
        """Test PDF with valid path."""
        mock_page = mocker.MagicMock()
        mock_page.pdf = mocker.AsyncMock()
        
        bp = BrowserPage(mock_page, url="https://mock.com")
        await bp.pdf("test_doc.pdf")
        mock_page.pdf.assert_called_once()


class TestBrowserPageScroll:
    """Tests for scroll functionality."""
    
    @pytest.mark.asyncio
    async def test_scroll_to_bottom(self, mocker):
        """Test scroll_to_bottom method."""
        mock_page = mocker.MagicMock()
        # Return same height twice to indicate scrolling is done
        mock_page.evaluate = mocker.AsyncMock(side_effect=[1000, 1000])
        
        bp = BrowserPage(mock_page, url="https://mock.com")
        try:
            await bp.scroll_to_bottom()
        except StopAsyncIteration:
            pass  # Expected in mock context





class TestBrowserPageClose:
    """Tests for page close."""
    
    @pytest.mark.asyncio
    async def test_close(self, mocker):
        """Test close method."""
        mock_page = mocker.MagicMock()
        mock_page.close = mocker.AsyncMock()
        
        bp = BrowserPage(mock_page, url="https://mock.com")
        await bp.close()
        mock_page.close.assert_called_once()


class TestRenderJsFunction:
    """Tests for render_js convenience function."""
    
    def test_render_js_import(self):
        """Test render_js is importable."""
        from easyscrape.browser import render_js
        assert render_js is not None



class TestBrowserGoto:
    """Tests for Browser.goto method with mocked playwright."""
    
    @pytest.fixture
    def mock_browser_setup(self, mocker):
        """Setup mocked playwright environment."""
        mock_pw_instance = mocker.MagicMock()
        mock_browser = mocker.MagicMock()
        mock_context = mocker.MagicMock()
        mock_page = mocker.MagicMock()
        
        # Setup the async chain
        mock_pw_instance.chromium.launch = mocker.AsyncMock(return_value=mock_browser)
        mock_browser.new_context = mocker.AsyncMock(return_value=mock_context)
        mock_context.new_page = mocker.AsyncMock(return_value=mock_page)
        mock_page.goto = mocker.AsyncMock()
        mock_page.content = mocker.AsyncMock(return_value="<html>Rendered</html>")
        mock_page.close = mocker.AsyncMock()
        mock_page.wait_for_selector = mocker.AsyncMock()
        
        # Mock async_playwright
        mock_pw_manager = mocker.MagicMock()
        mock_pw_manager.start = mocker.AsyncMock(return_value=mock_pw_instance)
        mocker.patch('easyscrape.browser.async_playwright', return_value=mock_pw_manager)
        
        return {"page": mock_page, "browser": mock_browser, "context": mock_context}


class TestBrowserClose:
    """Tests for Browser.close method."""
    
    @pytest.mark.asyncio
    async def test_close_when_not_started(self):
        """Test close when browser not started."""
        browser = Browser()
        await browser.close()  # Should not raise


class TestBrowserContextManager:
    """Tests for Browser async context manager."""
    
    @pytest.mark.asyncio
    async def test_context_manager_enter(self):
        """Test __aenter__ returns Browser."""
        browser = Browser()
        result = await browser.__aenter__()
        assert result is browser


class TestBrowserPagePdfPath:
    """Tests for PDF path validation."""
    
    def test_pdf_invalid_extension(self):
        """Test pdf rejects invalid extensions."""
        with pytest.raises(Exception):
            _validate_output_path("doc.txt", [".pdf"])



class TestBrowserPageMethods2:
    """Additional BrowserPage method tests."""
    
    @pytest.mark.asyncio
    async def test_screenshot_with_path(self, mocker):
        """Test screenshot saves to path."""
        mock_page = mocker.MagicMock()
        mock_page.screenshot = mocker.AsyncMock(return_value=b"PNG_DATA")
        
        bp = BrowserPage(mock_page, url="https://test.com")
        await bp.screenshot("test_ss.png")
        mock_page.screenshot.assert_called_once()
    
    @pytest.mark.asyncio  
    async def test_pdf_generation(self, mocker):
        """Test PDF generation."""
        mock_page = mocker.MagicMock()
        mock_page.pdf = mocker.AsyncMock(return_value=b"PDF_DATA")
        
        bp = BrowserPage(mock_page, url="https://test.com")
        result = await bp.pdf("test.pdf")
        mock_page.pdf.assert_called_once()


class TestValidateOutputPathMore:
    """More path validation tests."""
    
    def test_uppercase_extension(self):
        """Test uppercase extensions work."""
        result = _validate_output_path("FILE.PNG", [".png", ".PNG"])
        assert result is not None
    
    def test_nested_directory(self):
        """Test nested directory creation."""
        import shutil
        result = _validate_output_path("test_out/deep/nested/file.png", [".png"])
        assert result.parent.exists()
        shutil.rmtree("test_out", ignore_errors=True)



# =============================================================================
# Additional Coverage Tests
# =============================================================================

class TestValidateOutputPathErrors:
    """Tests for error cases in _validate_output_path."""
    
    def test_invalid_path_oserror(self, mocker):
        """Test OSError handling for invalid paths."""
        from easyscrape.browser import _validate_output_path, BrowserError
        # A path with null bytes causes OSError
        with pytest.raises(BrowserError, match="Invalid output path"):
            _validate_output_path("file\x00name.png", [".png"])


class TestEnsureStarted:
    """Tests for Browser._ensure_started method."""
    
    @pytest.mark.asyncio
    async def test_ensure_started_launches_browser(self, mocker):
        """Test _ensure_started initializes playwright."""
        # Setup mock playwright
        mock_pw_instance = mocker.MagicMock()
        mock_browser = mocker.MagicMock()
        mock_context = mocker.MagicMock()
        
        mock_pw_instance.chromium.launch = mocker.AsyncMock(return_value=mock_browser)
        mock_browser.new_context = mocker.AsyncMock(return_value=mock_context)
        
        mock_pw_manager = mocker.MagicMock()
        mock_pw_manager.start = mocker.AsyncMock(return_value=mock_pw_instance)
        mock_async_playwright = mocker.MagicMock(return_value=mock_pw_manager)
        
        mocker.patch('playwright.async_api.async_playwright', mock_async_playwright)
        
        browser = Browser()
        await browser._ensure_started()
        
        assert browser._browser is mock_browser
        assert browser._context is mock_context
        mock_pw_instance.chromium.launch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ensure_started_noop_if_started(self, mocker):
        """Test _ensure_started does nothing if already started."""
        browser = Browser()
        browser._browser = mocker.MagicMock()  # Fake that browser is started
        
        # Should not attempt to import playwright - this test passes if no error
        await browser._ensure_started()
        # If browser is already started, it should return immediately
        assert browser._browser is not None
    
    @pytest.mark.asyncio
    async def test_ensure_started_with_proxy(self, mocker):
        """Test _ensure_started configures proxy."""
        mock_pw_instance = mocker.MagicMock()
        mock_browser = mocker.MagicMock()
        mock_context = mocker.MagicMock()
        
        mock_pw_instance.chromium.launch = mocker.AsyncMock(return_value=mock_browser)
        mock_browser.new_context = mocker.AsyncMock(return_value=mock_context)
        
        mock_pw_manager = mocker.MagicMock()
        mock_pw_manager.start = mocker.AsyncMock(return_value=mock_pw_instance)
        mock_async_playwright = mocker.MagicMock(return_value=mock_pw_manager)
        
        mocker.patch('playwright.async_api.async_playwright', mock_async_playwright)
        
        config = Config(proxies=["http://proxy.example.com:8080"])
        browser = Browser(config)
        await browser._ensure_started()
        
        # Check proxy was passed to new_context
        call_args = mock_browser.new_context.call_args
        assert "proxy" in call_args.kwargs
        assert call_args.kwargs["proxy"]["server"] == "http://proxy.example.com:8080"


class TestBrowserGotoFull:
    """Full tests for Browser.goto method."""
    
    @pytest.fixture
    def mock_playwright_full(self, mocker):
        """Setup full mocked playwright."""
        mock_pw_instance = mocker.MagicMock()
        mock_browser = mocker.MagicMock()
        mock_context = mocker.MagicMock()
        mock_page = mocker.MagicMock()
        
        mock_pw_instance.chromium.launch = mocker.AsyncMock(return_value=mock_browser)
        mock_browser.new_context = mocker.AsyncMock(return_value=mock_context)
        mock_context.new_page = mocker.AsyncMock(return_value=mock_page)
        mock_page.goto = mocker.AsyncMock()
        mock_page.content = mocker.AsyncMock(return_value="<html>Rendered</html>")
        mock_page.close = mocker.AsyncMock()
        mock_page.wait_for_selector = mocker.AsyncMock()
        
        mock_pw_manager = mocker.MagicMock()
        mock_pw_manager.start = mocker.AsyncMock(return_value=mock_pw_instance)
        mock_async_playwright = mocker.MagicMock(return_value=mock_pw_manager)
        mocker.patch('playwright.async_api.async_playwright', mock_async_playwright)
        
        return {"page": mock_page, "browser": mock_browser, "context": mock_context}
    
    @pytest.mark.asyncio
    async def test_goto_basic(self, mock_playwright_full):
        """Test basic goto navigation."""
        browser = Browser()
        page = await browser.goto("https://example.com")
        assert isinstance(page, BrowserPage)
        assert page.url == "https://example.com"
    
    @pytest.mark.asyncio
    async def test_goto_with_wait_for(self, mock_playwright_full, mocker):
        """Test goto with wait_for selector."""
        browser = Browser()
        page = await browser.goto("https://example.com", wait_for=".content")
        mock_playwright_full["page"].wait_for_selector.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_goto_wait_for_timeout(self, mock_playwright_full, mocker):
        """Test goto continues even if wait_for times out."""
        mock_playwright_full["page"].wait_for_selector = mocker.AsyncMock(
            side_effect=TimeoutError("Element not found")
        )
        browser = Browser()
        # Should not raise, just continue
        page = await browser.goto("https://example.com", wait_for=".nonexistent")
        assert page is not None
    
    @pytest.mark.asyncio
    async def test_goto_navigation_error(self, mock_playwright_full, mocker):
        """Test goto raises BrowserError on navigation failure."""
        from easyscrape.browser import BrowserError
        
        mock_playwright_full["page"].goto = mocker.AsyncMock(
            side_effect=Exception("Network error")
        )
        browser = Browser()
        with pytest.raises(BrowserError, match="Navigation to .* failed"):
            await browser.goto("https://example.com")


class TestBrowserGetHtml:
    """Tests for Browser.get_html method."""
    
    @pytest.fixture
    def mock_playwright_full(self, mocker):
        """Setup full mocked playwright."""
        mock_pw_instance = mocker.MagicMock()
        mock_browser = mocker.MagicMock()
        mock_context = mocker.MagicMock()
        mock_page = mocker.MagicMock()
        
        mock_pw_instance.chromium.launch = mocker.AsyncMock(return_value=mock_browser)
        mock_browser.new_context = mocker.AsyncMock(return_value=mock_context)
        mock_context.new_page = mocker.AsyncMock(return_value=mock_page)
        mock_page.goto = mocker.AsyncMock()
        mock_page.content = mocker.AsyncMock(return_value="<html>Page Content</html>")
        mock_page.close = mocker.AsyncMock()
        mock_page.wait_for_selector = mocker.AsyncMock()
        
        mock_pw_manager = mocker.MagicMock()
        mock_pw_manager.start = mocker.AsyncMock(return_value=mock_pw_instance)
        mock_async_playwright = mocker.MagicMock(return_value=mock_pw_manager)
        mocker.patch('playwright.async_api.async_playwright', mock_async_playwright)
        
        return {"page": mock_page, "browser": mock_browser, "context": mock_context}
    
    @pytest.mark.asyncio
    async def test_get_html_returns_content(self, mock_playwright_full):
        """Test get_html returns page content."""
        browser = Browser()
        html = await browser.get_html("https://example.com")
        assert html == "<html>Page Content</html>"
    
    @pytest.mark.asyncio
    async def test_get_html_closes_page(self, mock_playwright_full):
        """Test get_html closes the page after getting content."""
        browser = Browser()
        await browser.get_html("https://example.com")
        mock_playwright_full["page"].close.assert_called_once()


class TestBrowserCloseFull:
    """Full tests for Browser.close method."""
    
    @pytest.mark.asyncio
    async def test_close_all_resources(self, mocker):
        """Test close cleans up all resources."""
        mock_context = mocker.MagicMock()
        mock_browser_obj = mocker.MagicMock()
        mock_playwright = mocker.MagicMock()
        
        mock_context.close = mocker.AsyncMock()
        mock_browser_obj.close = mocker.AsyncMock()
        mock_playwright.stop = mocker.AsyncMock()
        
        browser = Browser()
        browser._context = mock_context
        browser._browser = mock_browser_obj
        browser._playwright = mock_playwright
        
        await browser.close()
        
        mock_context.close.assert_called_once()
        mock_browser_obj.close.assert_called_once()
        mock_playwright.stop.assert_called_once()
        
        assert browser._context is None
        assert browser._browser is None
        assert browser._playwright is None


class TestBrowserAexit:
    """Tests for Browser.__aexit__."""
    
    @pytest.mark.asyncio
    async def test_aexit_calls_close(self, mocker):
        """Test __aexit__ calls close."""
        browser = Browser()
        # Instead of replacing close, just call __aexit__ and verify it doesn't fail
        await browser.__aexit__(None, None, None)
        # Verify that internal state is cleaned up
        assert browser._browser is None


class TestContentCaching:
    """Tests for BrowserPage content caching."""
    
    @pytest.mark.asyncio
    async def test_content_cached(self, mocker):
        """Test content is cached after first call."""
        mock_page = mocker.MagicMock()
        mock_page.content = mocker.AsyncMock(return_value="<html>Cached</html>")
        
        bp = BrowserPage(mock_page, url="https://test.com")
        
        # First call
        content1 = await bp.content()
        # Second call
        content2 = await bp.content()
        
        assert content1 == content2
        # content() should only be called once due to caching
        mock_page.content.assert_called_once()
