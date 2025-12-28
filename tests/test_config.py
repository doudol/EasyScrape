"""Tests for configuration management."""
import pytest
from easyscrape import Config
from easyscrape.config import StealthConfig, DistributedConfig, ComplianceConfig


class TestConfig:
    """Tests for Config dataclass."""

    def test_default_config(self):
        """Test default config values."""
        config = Config()
        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.cache_enabled is True
        assert config.rate_limit == 0.0
        assert config.javascript is False

    def test_custom_timeout(self):
        """Test custom timeout."""
        config = Config(timeout=60.0)
        assert config.timeout == 60.0

    def test_custom_retries(self):
        """Test custom retries."""
        config = Config(max_retries=5)
        assert config.max_retries == 5

    def test_cache_disabled(self):
        """Test cache can be disabled."""
        config = Config(cache_enabled=False)
        assert config.cache_enabled is False

    def test_rate_limit(self):
        """Test rate limit setting."""
        config = Config(rate_limit=2.0)
        assert config.rate_limit == 2.0

    def test_javascript_enabled(self):
        """Test JavaScript rendering flag."""
        config = Config(javascript=True)
        assert config.javascript is True

    def test_custom_headers(self):
        """Test custom headers."""
        headers = {"X-Custom": "value"}
        config = Config(headers=headers)
        assert config.headers["X-Custom"] == "value"

    def test_proxy_config(self):
        """Test proxy configuration."""
        proxies = ["http://proxy1:8080", "http://proxy2:8080"]
        config = Config(proxies=proxies, proxy_mode="round-robin")
        assert len(config.proxies) == 2
        assert config.proxy_mode == "round-robin"

    def test_ssl_verification(self):
        """Test SSL verification setting."""
        config = Config(verify_ssl=False)
        assert config.verify_ssl is False

    def test_follow_redirects(self):
        """Test redirect following."""
        config = Config(follow_redirects=False)
        assert config.follow_redirects is False


class TestStealthConfig:
    """Tests for StealthConfig."""

    def test_stealth_defaults(self):
        """Test StealthConfig default values."""
        config = StealthConfig()
        # use_stealth defaults to False for opt-in behavior
        assert config.use_stealth is False
        assert config.rotate_ua is True

    def test_stealth_random_delays(self):
        """Test random delay settings."""
        config = StealthConfig(random_delays=True, delay_min=1.0, delay_max=3.0)
        assert config.random_delays is True
        assert config.delay_min == 1.0
        assert config.delay_max == 3.0


class TestDistributedConfig:
    """Tests for DistributedConfig."""

    def test_distributed_defaults(self):
        """Test DistributedConfig default values."""
        config = DistributedConfig()
        assert config.redis_url is None

    def test_distributed_redis(self):
        """Test Redis configuration."""
        config = DistributedConfig(redis_url="redis://localhost:6379")
        assert config.redis_url == "redis://localhost:6379"


class TestComplianceConfig:
    """Tests for ComplianceConfig."""

    def test_compliance_defaults(self):
        """Test ComplianceConfig default values."""
        config = ComplianceConfig()
        # respect_robots defaults to False for opt-in behavior
        assert config.respect_robots is False

    def test_compliance_robots(self):
        """Test robots.txt respect setting."""
        config = ComplianceConfig(respect_robots=False)
        assert config.respect_robots is False



class TestDistributedConfig:
    """Tests for DistributedConfig."""
    
    def test_creation(self):
        """Test DistributedConfig creation."""
        from easyscrape.config import DistributedConfig
        config = DistributedConfig()
        assert config is not None


class TestStealthConfig:
    """Tests for StealthConfig."""
    
    def test_creation(self):
        """Test StealthConfig creation."""
        from easyscrape.config import StealthConfig
        config = StealthConfig()
        assert config is not None


class TestComplianceConfig:
    """Tests for ComplianceConfig."""
    
    def test_creation(self):
        """Test ComplianceConfig creation."""
        from easyscrape.config import ComplianceConfig
        config = ComplianceConfig()
        assert config is not None


class TestSafeFloatInt:
    """Tests for _safe_float and _safe_int helpers."""
    
    def test_safe_float_default(self):
        """Test _safe_float with invalid env."""
        import os
        from easyscrape.config import _safe_float
        # Should return default on non-existent env
        result = _safe_float("NONEXISTENT_VAR_12345", "1.5")
        assert result == 1.5
    
    def test_safe_int_default(self):
        """Test _safe_int with invalid env."""
        import os
        from easyscrape.config import _safe_int
        result = _safe_int("NONEXISTENT_VAR_12345", "10")
        assert result == 10


class TestConfigEdgeCases:
    """Tests for config edge cases."""
    
    def test_config_from_env_missing(self, mocker):
        """Test config when env vars are missing."""
        mocker.patch.dict('os.environ', {}, clear=True)
        from easyscrape.config import Config
        config = Config()
        assert config is not None
    
    def test_config_with_all_options(self):
        """Test config with all options set."""
        from easyscrape.config import Config
        config = Config(
            timeout=30,
            max_retries=5,
            follow_redirects=False,
            verify_ssl=False,
            use_stealth=True,
            cache_enabled=True,
            cache_ttl=600
        )
        assert config.timeout == 30
        assert config.max_retries == 5
        assert config.follow_redirects is False
        assert config.verify_ssl is False
