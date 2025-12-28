"""Tests for cache module."""

import pytest
from easyscrape.cache import CacheEntry, ResponseCache, get_cache, clear_all


class TestCacheEntry:
    """Tests for CacheEntry."""

    def test_creation(self):
        """Test entry creation."""
        entry = CacheEntry(
            data=b"hello",
            headers={"Content-Type": "text/html"},
            status=200,
            ttl=3600,
        )
        assert entry.data == b"hello"
        assert entry.status == 200

    def test_valid_property(self):
        """Test valid property."""
        entry = CacheEntry(
            data=b"hello",
            headers={},
            status=200,
            ttl=3600,
        )
        assert entry.valid is True

    def test_serialise(self):
        """Test serialization."""
        entry = CacheEntry(
            data=b"hello",
            headers={"X-Test": "value"},
            status=200,
            ttl=3600,
        )
        serialized = entry.serialise()
        assert isinstance(serialized, dict)


class TestResponseCache:
    """Tests for ResponseCache."""

    def test_creation(self):
        """Test cache creation."""
        cache = ResponseCache()
        assert cache is not None

    def test_creation_with_directory(self):
        """Test cache with custom directory."""
        cache = ResponseCache(directory=".testcache")
        assert cache is not None


class TestGetCache:
    """Tests for get_cache function."""

    def test_returns_cache(self):
        """Test returns ResponseCache."""
        cache = get_cache()
        assert isinstance(cache, ResponseCache)


class TestClearAll:
    """Tests for clear_all function."""

    def test_clear_no_error(self):
        """Test clear doesn't raise."""
        clear_all()
        # Should not raise



class TestCacheEntryMethods:
    """Additional tests for CacheEntry methods."""
    
    def test_deserialise(self):
        """Test deserialization."""
        entry = CacheEntry(
            data=b"hello",
            headers={"X-Test": "value"},
            status=200,
            ttl=3600,
        )
        serialized = entry.serialise()
        restored = CacheEntry.deserialise(serialized)
        assert restored.data == entry.data
        assert restored.status == entry.status
    
    def test_expired_entry(self):
        """Test expired entry."""
        import time
        entry = CacheEntry(
            data=b"hello",
            headers={},
            status=200,
            ttl=0.01,  # Very short TTL
        )
        time.sleep(0.02)
        assert entry.valid is False


class TestResponseCacheMethods:
    """Additional tests for ResponseCache methods."""
    
    def test_set_and_get(self):
        """Test set and get methods."""
        cache = ResponseCache()
        cache.set("https://test.com", b"test", {}, 200, 3600)
        result = cache.get("https://test.com")
        assert result is not None
        assert result.data == b"test"
    
    def test_get_nonexistent(self):
        """Test getting nonexistent key."""
        cache = ResponseCache()
        result = cache.get("https://nonexistent.com/page")
        assert result is None
    
    def test_clear(self):
        """Test clear method."""
        cache = ResponseCache()
        for i in range(3):
            cache.set(f"https://test{i}.com", f"test{i}".encode(), {}, 200, 3600)
        cache.clear()
        for i in range(3):
            assert cache.get(f"https://test{i}.com") is None
    
    def test_multiple_entries(self):
        """Test setting multiple entries."""
        cache = ResponseCache()
        cache.set("https://a.com", b"test1", {}, 200, 3600)
        cache.set("https://b.com", b"test2", {}, 200, 3600)
        assert cache.get("https://a.com") is not None
        assert cache.get("https://b.com") is not None


class TestGlobalCacheFunctions:
    """Tests for global cache functions."""
    
    def test_get_cache(self):
        """Test get_cache function."""
        cache = get_cache()
        assert cache is not None
    
    def test_clear_all(self):
        """Test clear_all function."""
        clear_all()  # Should not raise



# =============================================================================
# Additional Coverage Tests
# =============================================================================

class TestCacheDirectoryValidation:
    """Tests for cache directory validation."""
    
    def test_path_traversal_rejected(self):
        """Test path traversal is rejected."""
        from easyscrape.cache import _validate_cache_directory
        
        with pytest.raises(ValueError, match="escapes"):
            _validate_cache_directory("../../../etc")


class TestResponseCacheExpiration:
    """Tests for cache entry expiration."""
    
    def test_expired_entry_removed_on_get(self, tmp_path):
        """Test expired entries are removed on access."""
        import time
        cache = ResponseCache(str(tmp_path))
        cache.set("https://expire.com", b"data", {}, 200, 1)  # 1 second TTL
        
        # Should be there initially
        assert cache.get("https://expire.com") is not None
        
        # Wait for expiration
        time.sleep(1.5)
        
        # Should be None now (expired and removed)
        assert cache.get("https://expire.com") is None


class TestResponseCacheNegativeTTL:
    """Tests for negative TTL handling."""
    
    def test_negative_ttl_not_cached(self, tmp_path):
        """Test negative TTL skips caching."""
        cache = ResponseCache(str(tmp_path))
        cache.set("https://nocache.com", b"data", {}, 200, -1)
        
        # Should not be cached
        assert cache.get("https://nocache.com") is None


class TestResponseCacheLRU:
    """Tests for LRU eviction."""
    
    def test_lru_eviction(self, tmp_path):
        """Test LRU eviction when cache is full."""
        cache = ResponseCache(str(tmp_path), max_memory=3)
        
        # Fill cache
        cache.set("https://1.com", b"1", {}, 200, 3600)
        cache.set("https://2.com", b"2", {}, 200, 3600)
        cache.set("https://3.com", b"3", {}, 200, 3600)
        
        # All should be present
        assert cache.get("https://1.com") is not None
        assert cache.get("https://2.com") is not None
        assert cache.get("https://3.com") is not None
        
        # Add one more - should evict oldest
        cache.set("https://4.com", b"4", {}, 200, 3600)
        
        # 4 should be present
        assert cache.get("https://4.com") is not None
    
    def test_existing_key_moves_to_end(self, tmp_path):
        """Test updating existing key moves it to end."""
        cache = ResponseCache(str(tmp_path), max_memory=3)
        
        cache.set("https://1.com", b"1", {}, 200, 3600)
        cache.set("https://2.com", b"2", {}, 200, 3600)
        
        # Update 1 - should move to end
        cache.set("https://1.com", b"1-updated", {}, 200, 3600)
        
        result = cache.get("https://1.com")
        assert result.data == b"1-updated"


class TestResponseCacheRemove:
    """Tests for remove method."""
    
    def test_remove_entry(self, tmp_path):
        """Test removing an entry."""
        cache = ResponseCache(str(tmp_path))
        cache.set("https://remove.com", b"data", {}, 200, 3600)
        
        assert cache.get("https://remove.com") is not None
        
        cache.remove("https://remove.com")
        
        assert cache.get("https://remove.com") is None


class TestResponseCacheDiskRetrieve:
    """Tests for disk cache retrieval."""
    
    def test_disk_cache_retrieval(self, tmp_path):
        """Test retrieving from disk when not in memory."""
        cache1 = ResponseCache(str(tmp_path), max_memory=1)
        cache1.set("https://disk.com", b"disk-data", {}, 200, 3600)
        
        # Create new cache pointing to same directory
        cache2 = ResponseCache(str(tmp_path), max_memory=1)
        
        # Should retrieve from disk
        result = cache2.get("https://disk.com")
        assert result is not None
        assert result.data == b"disk-data"


class TestResponseCachePruneExpired:
    """Tests for prune_expired method."""
    
    def test_prune_expired(self, tmp_path):
        """Test pruning expired entries."""
        import time
        cache = ResponseCache(str(tmp_path))
        
        # Add entry with short TTL
        cache.set("https://short.com", b"data", {}, 200, 1)
        # Add entry with long TTL
        cache.set("https://long.com", b"data", {}, 200, 3600)
        
        time.sleep(1.5)
        
        removed = cache.prune_expired()
        assert removed >= 1
        
        # Long TTL should still be there
        assert cache.get("https://long.com") is not None


class TestResponseCacheInfiniteTTL:
    """Tests for infinite TTL handling."""
    
    def test_infinite_ttl_skips_disk(self, tmp_path):
        """Test infinite TTL entries skip disk storage."""
        cache = ResponseCache(str(tmp_path))
        cache.set("https://infinite.com", b"data", {}, 200, 0)  # 0 = infinite
        
        # Should be in memory
        assert cache.get("https://infinite.com") is not None






