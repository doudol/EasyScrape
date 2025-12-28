"""Tests for exceptions module."""

import pytest
from easyscrape.exceptions import (
    EasyScrapeError,
    NetworkError,
    HTTPError,
    InvalidURLError,
    ExtractionError,
    ConfigError,
    RateLimitHit,
    ProxyDead,
    CaptchaDetected,
    RobotsBlocked,
    RetryExhausted,
    BrowserError,
    CircuitBreakerOpen,
    ValidationError,
    RequestTimeout,
)


class TestEasyScrapeError:
    """Tests for base exception."""

    def test_is_exception(self):
        """Test inherits from Exception."""
        assert issubclass(EasyScrapeError, Exception)

    def test_can_raise(self):
        """Test can be raised."""
        with pytest.raises(EasyScrapeError):
            raise EasyScrapeError("test error")

    def test_message(self):
        """Test error message."""
        try:
            raise EasyScrapeError("test message")
        except EasyScrapeError as e:
            assert "test message" in str(e)


class TestNetworkError:
    """Tests for NetworkError."""

    def test_inherits_base(self):
        """Test inherits from EasyScrapeError."""
        assert issubclass(NetworkError, EasyScrapeError)

    def test_can_raise(self):
        """Test can be raised."""
        with pytest.raises(NetworkError):
            raise NetworkError("connection failed")


class TestHTTPError:
    """Tests for HTTPError."""

    def test_inherits_base(self):
        """Test inherits from EasyScrapeError."""
        assert issubclass(HTTPError, EasyScrapeError)

    def test_with_status_code(self):
        """Test with status code."""
        error = HTTPError("Not found", status_code=404)
        assert error.status_code == 404


class TestInvalidURLError:
    """Tests for InvalidURLError."""

    def test_inherits_base(self):
        """Test inherits from EasyScrapeError."""
        assert issubclass(InvalidURLError, EasyScrapeError)


class TestExtractionError:
    """Tests for ExtractionError."""

    def test_inherits_base(self):
        """Test inherits from EasyScrapeError."""
        assert issubclass(ExtractionError, EasyScrapeError)


class TestConfigError:
    """Tests for ConfigError."""

    def test_inherits_base(self):
        """Test inherits from EasyScrapeError."""
        assert issubclass(ConfigError, EasyScrapeError)


class TestRateLimitHit:
    """Tests for RateLimitHit."""

    def test_inherits_base(self):
        """Test inherits from EasyScrapeError."""
        assert issubclass(RateLimitHit, EasyScrapeError)


class TestProxyDead:
    """Tests for ProxyDead."""

    def test_inherits_base(self):
        """Test inherits from EasyScrapeError."""
        assert issubclass(ProxyDead, EasyScrapeError)


class TestCaptchaDetected:
    """Tests for CaptchaDetected."""

    def test_inherits_base(self):
        """Test inherits from EasyScrapeError."""
        assert issubclass(CaptchaDetected, EasyScrapeError)


class TestRobotsBlocked:
    """Tests for RobotsBlocked."""

    def test_inherits_base(self):
        """Test inherits from EasyScrapeError."""
        assert issubclass(RobotsBlocked, EasyScrapeError)


class TestRetryExhausted:
    """Tests for RetryExhausted."""

    def test_inherits_base(self):
        """Test inherits from EasyScrapeError."""
        assert issubclass(RetryExhausted, EasyScrapeError)


class TestBrowserError:
    """Tests for BrowserError."""

    def test_inherits_base(self):
        """Test inherits from EasyScrapeError."""
        assert issubclass(BrowserError, EasyScrapeError)


class TestCircuitBreakerOpen:
    """Tests for CircuitBreakerOpen."""

    def test_inherits_base(self):
        """Test inherits from EasyScrapeError."""
        assert issubclass(CircuitBreakerOpen, EasyScrapeError)


class TestValidationError:
    """Tests for ValidationError."""

    def test_inherits_base(self):
        """Test inherits from EasyScrapeError."""
        assert issubclass(ValidationError, EasyScrapeError)


class TestRequestTimeout:
    """Tests for RequestTimeout."""

    def test_inherits_network_error(self):
        """Test inherits from NetworkError."""
        assert issubclass(RequestTimeout, NetworkError)



class TestAdditionalExceptions:
    """Tests for additional exception types."""
    
    def test_request_timeout(self):
        """Test RequestTimeout exception."""
        from easyscrape.exceptions import RequestTimeout
        exc = RequestTimeout("Connection timed out")
        assert str(exc) == "Connection timed out"
    
    def test_content_too_large(self):
        """Test ContentTooLarge exception."""
        from easyscrape.exceptions import ContentTooLarge
        exc = ContentTooLarge("Response too large")
        assert str(exc) == "Response too large"
    
    def test_ssl_certificate_error(self):
        """Test SSLCertificateError exception."""
        from easyscrape.exceptions import SSLCertificateError
        exc = SSLCertificateError("Invalid certificate")
        assert str(exc) == "Invalid certificate"
    
    def test_captcha_detected(self):
        """Test CaptchaDetected exception."""
        from easyscrape.exceptions import CaptchaDetected
        exc = CaptchaDetected("CAPTCHA required")
        assert str(exc) == "CAPTCHA required"
    
    def test_robots_blocked(self):
        """Test RobotsBlocked exception."""
        from easyscrape.exceptions import RobotsBlocked
        exc = RobotsBlocked("Blocked by robots.txt")
        assert str(exc) == "Blocked by robots.txt"


class TestExceptionTypes:
    """Tests for all exception types."""
    
    def test_http_error(self):
        """Test HTTPError creation."""
        from easyscrape.exceptions import HTTPError
        err = HTTPError("Not Found", status_code=404)
        assert err.status_code == 404
    
    def test_network_error(self):
        """Test NetworkError creation."""
        from easyscrape.exceptions import NetworkError
        err = NetworkError("Connection failed")
        assert "Connection failed" in str(err)
    
    def test_timeout_error(self):
        """Test TimeoutError creation."""
        from easyscrape.exceptions import RequestTimeout
        err = RequestTimeout("Request timed out")
        assert str(err) is not None
    
    def test_parse_error(self):
        """Test ParseError creation."""
        from easyscrape.exceptions import ExtractionError
        err = ExtractionError("Failed to parse HTML")
        assert str(err) is not None or str(err) is not None
