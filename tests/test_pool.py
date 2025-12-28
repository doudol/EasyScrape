"""Tests for connection pool module."""

import pytest
from easyscrape.pool import (
    PoolConfig,
    ConnectionPoolManager,
    get_pool_manager,
    close_all_pools,
)


class TestPoolConfig:
    """Tests for PoolConfig."""

    def test_default_values(self):
        """Test default config values."""
        config = PoolConfig()
        assert config.max_connections > 0
        assert config.max_keepalive_connections >= 0
        assert config.keepalive_expiry > 0

    def test_custom_values(self):
        """Test custom config values."""
        config = PoolConfig(max_connections=50, http2=False)
        assert config.max_connections == 50
        assert config.http2 is False

    def test_value_clamping(self):
        """Test values are clamped to valid range."""
        config = PoolConfig(max_connections=0)
        assert config.max_connections >= 1

        config = PoolConfig(max_connections=10000)
        assert config.max_connections <= 1000


class TestConnectionPoolManager:
    """Tests for ConnectionPoolManager."""

    def test_creation(self):
        """Test manager creation."""
        manager = ConnectionPoolManager()
        assert manager is not None

    def test_get_pool(self):
        """Test getting pool for domain."""
        manager = ConnectionPoolManager()
        pool = manager.get_pool("example.com")
        assert pool is not None

    def test_same_pool_for_same_domain(self):
        """Test same pool returned for same domain."""
        manager = ConnectionPoolManager()
        p1 = manager.get_pool("example.com")
        p2 = manager.get_pool("example.com")
        assert p1 is p2

    def test_different_pools_for_different_domains(self):
        """Test different pools for different domains."""
        manager = ConnectionPoolManager()
        p1 = manager.get_pool("example.com")
        p2 = manager.get_pool("other.com")
        assert p1 is not p2

    def test_close_all(self):
        """Test closing all pools."""
        manager = ConnectionPoolManager()
        manager.get_pool("example.com")
        manager.get_pool("other.com")
        manager.close_all()  # Should not raise


class TestGetPoolManager:
    """Tests for singleton accessor."""

    def test_returns_manager(self):
        """Test returns manager instance."""
        manager = get_pool_manager()
        assert isinstance(manager, ConnectionPoolManager)

    def test_singleton(self):
        """Test returns same instance."""
        m1 = get_pool_manager()
        m2 = get_pool_manager()
        assert m1 is m2


class TestCloseAllPools:
    """Tests for close_all_pools function."""

    def test_closes_without_error(self):
        """Test closing doesn't raise."""
        close_all_pools()  # Should not raise



class TestPoolStats:
    """Tests for PoolStats dataclass."""

    def test_import(self):
        """Test PoolStats is importable."""
        from easyscrape.pool import PoolStats
        assert PoolStats is not None

    def test_creation(self):
        """Test PoolStats creation."""
        from easyscrape.pool import PoolStats
        stats = PoolStats()
        assert stats is not None

    def test_default_values(self):
        """Test default values."""
        from easyscrape.pool import PoolStats
        stats = PoolStats()
        data = stats.get_stats()
        assert data["active"] == 0
        assert data["created"] == 0
        assert data["reused"] == 0


class TestDomainPool:
    """Tests for DomainPool class."""

    def test_import(self):
        """Test DomainPool is importable."""
        from easyscrape.pool import DomainPool
        assert DomainPool is not None

    def test_creation(self):
        """Test DomainPool creation."""
        from easyscrape.pool import DomainPool, PoolConfig
        config = PoolConfig()
        pool = DomainPool("example.com", config)
        assert pool is not None

    def test_domain_property(self):
        """Test domain property."""
        from easyscrape.pool import DomainPool, PoolConfig
        config = PoolConfig()
        pool = DomainPool("example.com", config)
        assert pool.domain == "example.com"

    def test_request_count(self):
        """Test request_count property."""
        from easyscrape.pool import DomainPool, PoolConfig
        config = PoolConfig()
        pool = DomainPool("example.com", config)
        assert pool.request_count == 0


class TestPoolConfigAdvanced:
    """Additional tests for PoolConfig."""

    def test_http2_enabled_by_default(self):
        """Test HTTP/2 is enabled by default."""
        config = PoolConfig()
        assert config.http2 is True

    def test_keepalive_connections(self):
        """Test keepalive connections config."""
        config = PoolConfig(max_keepalive_connections=10)
        assert config.max_keepalive_connections == 10

    def test_keepalive_expiry(self):
        """Test keepalive expiry config."""
        config = PoolConfig(keepalive_expiry=30.0)
        assert config.keepalive_expiry == 30.0

    def test_connect_timeout(self):
        """Test connect timeout config."""
        config = PoolConfig(connect_timeout=10.0)
        assert config.connect_timeout == 10.0


class TestConnectionPoolManagerAdvanced:
    """Additional tests for ConnectionPoolManager."""

    def test_with_custom_config(self):
        """Test manager with custom config."""
        config = PoolConfig(max_connections=20)
        manager = ConnectionPoolManager(config=config)
        assert manager is not None

    def test_context_manager(self):
        """Test as context manager."""
        with ConnectionPoolManager() as manager:
            pool = manager.get_pool("example.com")
            assert pool is not None

    def test_stats(self):
        """Test getting manager stats."""
        manager = ConnectionPoolManager()
        manager.get_pool("https://example.com")
        stats = manager.stats.get_stats()
        assert isinstance(stats, dict)
        assert "created" in stats



class TestPoolStatsAdvanced:
    """Advanced tests for PoolStats."""
    
    def test_connection_created(self):
        """Test connection_created updates stats."""
        from easyscrape.pool import PoolStats
        stats = PoolStats()
        stats.connection_created()
        data = stats.get_stats()
        assert data["created"] == 1
        assert data["active"] == 1
        assert data["peak"] == 1
    
    def test_connection_reused(self):
        """Test connection_reused updates stats."""
        from easyscrape.pool import PoolStats
        stats = PoolStats()
        stats.connection_reused()
        data = stats.get_stats()
        assert data["reused"] == 1
    
    def test_connection_closed(self):
        """Test connection_closed updates stats."""
        from easyscrape.pool import PoolStats
        stats = PoolStats()
        stats.connection_created()
        stats.connection_closed()
        data = stats.get_stats()
        assert data["closed"] == 1
        assert data["active"] == 0
    
    def test_peak_connections(self):
        """Test peak connections tracking."""
        from easyscrape.pool import PoolStats
        stats = PoolStats()
        stats.connection_created()
        stats.connection_created()
        stats.connection_closed()
        data = stats.get_stats()
        assert data["peak"] == 2
        assert data["active"] == 1
    
    def test_reset(self):
        """Test reset method."""
        from easyscrape.pool import PoolStats
        stats = PoolStats()
        stats.connection_created()
        stats.connection_reused()
        stats.reset()
        data = stats.get_stats()
        assert data["created"] == 0
        assert data["reused"] == 0


class TestDomainPoolAdvanced:
    """Advanced tests for DomainPool."""
    
    def test_idle_time(self):
        """Test idle_time property."""
        import time
        from easyscrape.pool import DomainPool, PoolConfig
        config = PoolConfig()
        pool = DomainPool("https://example.com", config)
        time.sleep(0.01)
        assert pool.idle_time >= 0.01
    
    def test_close(self):
        """Test close method."""
        from easyscrape.pool import DomainPool, PoolConfig
        config = PoolConfig()
        pool = DomainPool("https://example.com", config)
        pool.close()  # Should not raise


class TestConnectionPoolManagerMethods:
    """Tests for ConnectionPoolManager methods."""
    
    def test_get_pool_creates_new(self):
        """Test get_pool creates new pool for unknown domain."""
        manager = ConnectionPoolManager()
        pool = manager.get_pool("https://newdomain.com/path")
        assert pool is not None
        assert pool.domain == "https://newdomain.com"
        manager.close_all()
    
    def test_get_pool_reuses_existing(self):
        """Test get_pool reuses existing pool."""
        manager = ConnectionPoolManager()
        pool1 = manager.get_pool("https://example.com/a")
        pool2 = manager.get_pool("https://example.com/b")
        assert pool1 is pool2
        manager.close_all()
    
    def test_close_pool(self):
        """Test close_pool method."""
        manager = ConnectionPoolManager()
        manager.get_pool("https://example.com")
        manager.close_pool("https://example.com")
        # Getting it again should create a new one
        stats = manager.get_pool_stats()
        manager.close_all()
    
    def test_get_pool_stats(self):
        """Test get_pool_stats method."""
        manager = ConnectionPoolManager()
        manager.get_pool("https://example.com")
        stats = manager.get_pool_stats()
        assert "pool_count" in stats
        assert stats["pool_count"] == 1
        assert "pools" in stats
        assert "connection_stats" in stats
        manager.close_all()
    
    def test_close_all(self):
        """Test close_all method."""
        manager = ConnectionPoolManager()
        manager.get_pool("https://a.com")
        manager.get_pool("https://b.com")
        manager.close_all()
        stats = manager.get_pool_stats()
        assert stats["pool_count"] == 0


class TestGlobalPoolFunctions:
    """Tests for global pool functions."""
    
    def test_get_pool_manager(self):
        """Test get_pool_manager singleton."""
        from easyscrape.pool import get_pool_manager, close_all_pools
        manager1 = get_pool_manager()
        manager2 = get_pool_manager()
        assert manager1 is manager2
        close_all_pools()
    
    def test_close_all_pools(self):
        """Test close_all_pools function."""
        from easyscrape.pool import get_pool_manager, close_all_pools
        manager = get_pool_manager()
        manager.get_pool("https://test.com")
        close_all_pools()
        # Manager is reset, getting it again creates new one



class TestConnectionPoolMethods:
    """Tests for ConnectionPool methods."""
    
    def test_get_client(self):
        """Test getting sync client."""
        manager = ConnectionPoolManager()
        pool = manager.get_pool("test-client.com")
        client = pool.get_client()
        assert client is not None
        pool.close()
    
    @pytest.mark.asyncio
    async def test_get_async_client(self):
        """Test getting async client."""
        manager = ConnectionPoolManager()
        pool = manager.get_pool("test-async.com")
        client = await pool.get_async_client()
        assert client is not None
        await pool.aclose()
    
    def test_close_pool(self):
        """Test closing pool."""
        manager = ConnectionPoolManager()
        pool = manager.get_pool("test-close.com")
        pool.get_client()  # Create a client
        pool.close()
        # Should not raise
    
    @pytest.mark.asyncio
    async def test_aclose_pool(self):
        """Test async closing pool."""
        manager = ConnectionPoolManager()
        pool = manager.get_pool("test-aclose.com")
        await pool.get_async_client()  # Create a client
        await pool.aclose()
        # Should not raise


class TestPoolManagerClose:
    """Tests for pool manager close operations."""
    
    def test_close_all(self):
        """Test closing all pools."""
        manager = ConnectionPoolManager()
        manager.get_pool("domain1.com")
        manager.get_pool("domain2.com")
        manager.close_all()
    
    @pytest.mark.asyncio
    async def test_aclose_all(self):
        """Test async closing all pools."""
        manager = ConnectionPoolManager()
        manager.get_pool("async-domain1.com")
        manager.get_pool("async-domain2.com")
        await manager.aclose_all()


class TestPoolReuse:
    """Tests for pool reuse behavior."""
    
    def test_client_reuse(self):
        """Test same client is reused."""
        manager = ConnectionPoolManager()
        pool = manager.get_pool("reuse-test.com")
        client1 = pool.get_client()
        client2 = pool.get_client()
        assert client1 is client2
        pool.close()
    
    @pytest.mark.asyncio
    async def test_async_client_reuse(self):
        """Test same async client is reused."""
        manager = ConnectionPoolManager()
        pool = manager.get_pool("async-reuse.com")
        client1 = await pool.get_async_client()
        client2 = await pool.get_async_client()
        assert client1 is client2
        await pool.aclose()



# Additional tests removed - ConnectionPool and WorkerPool classes don't exist
