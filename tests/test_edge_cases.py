"""
Edge case tests for comprehensive coverage.

Tests boundary conditions, malformed inputs, and unusual scenarios
that might occur in production but are easy to miss in normal testing.
"""

import pytest
from easyscrape import Config
from easyscrape.validate import validate_url, URLValidator
from easyscrape.utils import normalise_url, domain_of, clean_text, is_valid_url
from easyscrape.exceptions import InvalidURLError


class TestURLEdgeCases:
    """URL validation edge cases."""

    @pytest.mark.parametrize("url", [
        "",  # Empty string
        "   ",  # Whitespace only
        "\n\t",  # Newlines and tabs
        "not-a-url",  # No scheme
        "://missing-scheme.com",  # Missing scheme
        "http://",  # Scheme only
        "http:///path",  # Missing host
        "http://user:pass@",  # Auth but no host
    ])
    def test_invalid_urls_rejected(self, url):
        """Malformed URLs should raise InvalidURLError."""
        with pytest.raises((InvalidURLError, ValueError)):
            validate_url(url)

    @pytest.mark.parametrize("url", [
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "file:///etc/passwd",
    ])
    def test_dangerous_schemes_blocked(self, url):
        """Dangerous URL schemes should be rejected."""
        with pytest.raises((InvalidURLError, ValueError)):
            validate_url(url)

    @pytest.mark.parametrize("url", [
        "http://localhost/admin",
        "http://127.0.0.1:8080/",
        "http://[::1]/",
    ])
    def test_ssrf_vectors_blocked(self, url):
        """SSRF attack vectors should be blocked by default."""
        with pytest.raises((InvalidURLError, ValueError)):
            validate_url(url, allow_localhost=False)

    def test_unicode_domain(self):
        """Unicode domains should be handled."""
        url = "https://例え.jp/path"
        # Should not raise
        result = normalise_url(url)
        assert result is not None

    def test_very_long_url(self):
        """Extremely long URLs should be handled gracefully."""
        long_path = "a" * 10000
        url = f"https://example.com/{long_path}"
        result = normalise_url(url)
        assert len(result) > 10000


class TestTextProcessingEdgeCases:
    """Text cleaning edge cases."""

    @pytest.mark.parametrize("text,expected", [
        ("", ""),  # Empty
        ("   ", ""),  # Whitespace only
        ("\n\n\n", ""),  # Newlines only
        ("hello", "hello"),  # Normal text
        ("  hello  world  ", "hello world"),  # Extra spaces
        ("café", "café"),  # Accented characters
        ("你好世界", "你好世界"),  # CJK characters
        ("🎉🎊", "🎉🎊"),  # Emoji
    ])
    def test_clean_text_edge_cases(self, text, expected):
        """Text cleaning handles various edge cases."""
        result = clean_text(text)
        assert result == expected


class TestDomainExtraction:
    """Domain extraction edge cases."""

    @pytest.mark.parametrize("url,expected", [
        ("https://example.com", "example.com"),
        ("https://sub.example.com/path", "sub.example.com"),
    ])
    def test_domain_extraction(self, url, expected):
        """Domain extraction works correctly."""
        assert domain_of(url) == expected


class TestConfigEdgeCases:
    """Configuration edge cases."""

    def test_default_timeout(self):
        """Default timeout should be applied."""
        config = Config()
        assert config.timeout == 30.0

    def test_custom_timeout(self):
        """Custom timeout should work."""
        config = Config(timeout=60.0)
        assert config.timeout == 60.0

    def test_very_large_timeout(self):
        """Very large timeout values should work."""
        config = Config(timeout=86400)  # 24 hours
        assert config.timeout == 86400

    def test_empty_headers(self):
        """Empty headers dict should work."""
        config = Config(headers={})
        assert config.headers == {}

    def test_custom_headers(self):
        """Custom headers should be preserved."""
        headers = {"X-Custom": "value"}
        config = Config(headers=headers)
        assert config.headers == headers


class TestConfigDefaults:
    """Test config default values."""

    def test_default_values(self):
        """All default values should be sensible."""
        config = Config()
        assert config.timeout > 0
        assert config.max_retries >= 0
        assert config.cache_ttl > 0
