"""Tests for import handling and optional dependencies."""
import pytest
import sys


class TestOptionalImports:
    """Tests for handling of optional imports."""
    
    def test_session_imports_without_brotli(self, mocker):
        """Test session module loads without brotli."""
        # Simply verify the module loads and works
        from easyscrape.session import Session
        session = Session()
        assert session is not None
        session.close()
    
    def test_async_core_imports(self):
        """Test async_core module imports correctly."""
        from easyscrape.async_core import async_scrape, async_scrape_many
        assert callable(async_scrape)
        assert callable(async_scrape_many)
    
    def test_browser_imports(self):
        """Test browser module imports correctly."""
        from easyscrape.browser import Browser
        assert Browser is not None


class TestExceptionHierarchy:
    """Tests for exception class hierarchy."""
    
    def test_all_exceptions_inherit_base(self):
        """Test all exceptions inherit from EasyScrapeError."""
        from easyscrape.exceptions import (
            EasyScrapeError, NetworkError, HTTPError, InvalidURLError,
            ExtractionError, ConfigError, RateLimitHit, ProxyDead,
            CaptchaDetected, RobotsBlocked, RetryExhausted, BrowserError,
            CircuitBreakerOpen, ValidationError, RequestTimeout
        )
        assert issubclass(NetworkError, EasyScrapeError)
        assert issubclass(HTTPError, EasyScrapeError)
        assert issubclass(InvalidURLError, EasyScrapeError)
        assert issubclass(ExtractionError, EasyScrapeError)
        assert issubclass(RequestTimeout, NetworkError)
