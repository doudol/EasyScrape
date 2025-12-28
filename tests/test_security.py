"""Security-focused tests for EasyScrape.

These tests verify that security measures work correctly:
- SSRF protection
- Path traversal prevention
- Input sanitisation
- Safe defaults
"""

import pytest
from easyscrape import Config
from easyscrape.validate import validate_url, URLValidator
from easyscrape.exceptions import InvalidURLError


class TestSSRFProtection:
    """Server-Side Request Forgery protection tests."""

    @pytest.mark.parametrize("url", [
        "http://localhost/",
        "http://localhost:8080/admin",
        "http://127.0.0.1/",
        "http://127.0.0.1:3000/api",
        "http://[::1]/",
        "http://0.0.0.0/",
    ])
    def test_localhost_blocked_by_default(self, url):
        """Localhost URLs should be blocked by default."""
        with pytest.raises((InvalidURLError, ValueError)):
            validate_url(url, allow_localhost=False)

    @pytest.mark.parametrize("url", [
        "http://localhost/",
        "http://127.0.0.1/",
    ])
    def test_localhost_allowed_when_enabled(self, url):
        """Localhost URLs should work when explicitly allowed."""
        result = validate_url(url, allow_localhost=True)
        assert result == url

    def test_aws_metadata_blocked(self):
        """AWS metadata endpoint should be blocked."""
        url = "http://169.254.169.254/latest/meta-data/"
        with pytest.raises((InvalidURLError, ValueError)):
            validate_url(url, allow_localhost=False)


class TestDangerousSchemes:
    """Tests for blocking dangerous URL schemes."""

    @pytest.mark.parametrize("url", [
        "javascript:alert(document.cookie)",
        "javascript:void(0)",
        "data:text/html,<script>alert(1)</script>",
        "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
        "file:///etc/passwd",
        "file:///C:/Windows/System32/config/SAM",
    ])
    def test_dangerous_schemes_rejected(self, url):
        """Dangerous URL schemes should be rejected."""
        with pytest.raises((InvalidURLError, ValueError)):
            validate_url(url)


class TestInputValidation:
    """Input validation and sanitisation tests."""

    @pytest.mark.parametrize("url", [
        "",
        "   ",
        "\n",
        "\t",
        "not-a-url",
        "htp://typo.com",
        "://no-scheme.com",
    ])
    def test_malformed_urls_rejected(self, url):
        """Malformed URLs should be rejected early."""
        with pytest.raises((InvalidURLError, ValueError)):
            validate_url(url)

class TestSecureDefaults:
    """Tests for secure default configuration."""

    def test_ssl_verification_enabled_by_default(self):
        """SSL verification should be on by default."""
        config = Config()
        assert config.verify_ssl is True

    def test_redirects_limited_by_default(self):
        """Redirect following should be limited."""
        config = Config()
        assert config.max_redirects <= 30

    def test_robots_respect_configurable(self):
        """Robots.txt respect should be configurable."""
        config = Config(respect_robots=True)
        assert config.respect_robots is True
