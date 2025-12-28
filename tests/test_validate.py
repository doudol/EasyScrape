"""Tests for URL validation and security."""
import pytest

from easyscrape.validate import (
    validate_url,
    is_safe_url,
    is_private_ip,
    sanitize_header_value,
)
from easyscrape.exceptions import InvalidURLError


class TestValidateUrl:
    """Tests for validate_url() function."""

    def test_valid_http_url(self):
        """Test valid HTTP URL."""
        url = validate_url("http://example.com")
        assert url == "http://example.com"

    def test_valid_https_url(self):
        """Test valid HTTPS URL."""
        url = validate_url("https://example.com/page?q=1")
        assert url == "https://example.com/page?q=1"

    def test_missing_scheme(self):
        """Test URL without scheme."""
        with pytest.raises(InvalidURLError) as exc:
            validate_url("example.com")
        assert "scheme" in str(exc.value).lower()

    def test_dangerous_scheme_javascript(self):
        """Test javascript: scheme is blocked."""
        with pytest.raises(InvalidURLError) as exc:
            validate_url("javascript:alert(1)")
        assert "dangerous" in str(exc.value).lower()

    def test_dangerous_scheme_data(self):
        """Test data: scheme is blocked."""
        with pytest.raises(InvalidURLError):
            validate_url("data:text/html,<h1>Hi</h1>")

    def test_dangerous_scheme_file(self):
        """Test file: scheme is blocked."""
        with pytest.raises(InvalidURLError):
            validate_url("file:///etc/passwd")

    def test_invalid_scheme(self):
        """Test unsupported scheme."""
        with pytest.raises(InvalidURLError):
            validate_url("ftp://example.com")

    def test_missing_hostname(self):
        """Test URL without hostname."""
        with pytest.raises(InvalidURLError):
            validate_url("http:///path")

    def test_localhost_blocked(self):
        """Test localhost is blocked."""
        with pytest.raises(InvalidURLError) as exc:
            validate_url("http://localhost/admin")
        assert "blocked" in str(exc.value).lower()

    def test_localhost_subdomain_blocked(self):
        """Test localhost subdomain is blocked."""
        with pytest.raises(InvalidURLError):
            validate_url("http://foo.localhost/admin")

    def test_loopback_ip_blocked(self):
        """Test 127.0.0.1 is blocked."""
        with pytest.raises(InvalidURLError):
            validate_url("http://127.0.0.1/admin")

    def test_private_ip_10_blocked(self):
        """Test 10.x.x.x is blocked."""
        with pytest.raises(InvalidURLError):
            validate_url("http://10.0.0.1/internal")

    def test_private_ip_172_blocked(self):
        """Test 172.16.x.x is blocked."""
        with pytest.raises(InvalidURLError):
            validate_url("http://172.16.0.1/internal")

    def test_private_ip_192_blocked(self):
        """Test 192.168.x.x is blocked."""
        with pytest.raises(InvalidURLError):
            validate_url("http://192.168.1.1/router")

    def test_metadata_ip_blocked(self):
        """Test cloud metadata IP is blocked."""
        with pytest.raises(InvalidURLError):
            validate_url("http://169.254.169.254/latest/meta-data")

    def test_url_too_long(self):
        """Test URL length limit."""
        long_url = "https://example.com/" + "a" * 10000
        with pytest.raises(InvalidURLError) as exc:
            validate_url(long_url)
        assert "long" in str(exc.value).lower()

    def test_caching(self):
        """Test that validation results are cached."""
        url = "https://example.com"
        # First call
        result1 = validate_url(url)
        # Second call (should hit cache)
        result2 = validate_url(url)
        assert result1 == result2


class TestIsSafeUrl:
    """Tests for is_safe_url() function."""

    def test_safe_url(self):
        """Test safe URL returns True."""
        assert is_safe_url("https://example.com") is True

    def test_unsafe_url(self):
        """Test unsafe URL returns False."""
        assert is_safe_url("http://localhost") is False
        assert is_safe_url("javascript:alert(1)") is False
        assert is_safe_url("http://127.0.0.1") is False


class TestIsPrivateIp:
    """Tests for is_private_ip() function."""

    def test_public_ip(self):
        """Test public IP returns False."""
        assert is_private_ip("8.8.8.8") is False
        assert is_private_ip("93.184.216.34") is False

    def test_loopback_ip(self):
        """Test loopback IP returns True."""
        assert is_private_ip("127.0.0.1") is True
        assert is_private_ip("127.0.0.2") is True

    def test_private_class_a(self):
        """Test class A private IP."""
        assert is_private_ip("10.0.0.1") is True
        assert is_private_ip("10.255.255.255") is True

    def test_private_class_b(self):
        """Test class B private IP."""
        assert is_private_ip("172.16.0.1") is True
        assert is_private_ip("172.31.255.255") is True

    def test_private_class_c(self):
        """Test class C private IP."""
        assert is_private_ip("192.168.0.1") is True
        assert is_private_ip("192.168.255.255") is True

    def test_link_local(self):
        """Test link-local IP."""
        assert is_private_ip("169.254.1.1") is True

    def test_metadata_ip(self):
        """Test cloud metadata IP."""
        assert is_private_ip("169.254.169.254") is True

    def test_ipv6_loopback(self):
        """Test IPv6 loopback."""
        assert is_private_ip("::1") is True

    def test_invalid_ip(self):
        """Test invalid IP returns False."""
        assert is_private_ip("not-an-ip") is False
        assert is_private_ip("example.com") is False


class TestSanitizeHeaderValue:
    """Tests for sanitize_header_value() function."""

    def test_normal_value(self):
        """Test normal value unchanged."""
        assert sanitize_header_value("normal value") == "normal value"

    def test_crlf_removal(self):
        """Test CRLF characters are removed."""
        result = sanitize_header_value("value\r\nX-Injected: bad")
        assert "\r" not in result
        assert "\n" not in result

    def test_cr_only(self):
        """Test CR only is removed."""
        result = sanitize_header_value("value\rinjected")
        assert "\r" not in result

    def test_lf_only(self):
        """Test LF only is removed."""
        result = sanitize_header_value("value\ninjected")
        assert "\n" not in result
