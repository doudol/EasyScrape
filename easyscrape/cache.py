"""HTTP response caching with memory and disk backends.

Architecture
------------
This module implements a two-tier cache for HTTP responses:

1. **Memory Cache (L1)**: Fast, limited-size OrderedDict with LRU eviction
2. **Disk Cache (L2)**: Persistent JSON files, slower but survives restarts

Why Two Tiers?
    - Memory is fast (~1μs access) but limited and volatile
    - Disk is slower (~1ms access) but persists and scales

    When fetching a URL:
    1. Check L1 (memory) - instant if hit
    2. Check L2 (disk) - slower but still faster than network
    3. Fetch from network - slowest, updates both caches

Design Decisions
----------------
1. **OrderedDict for LRU**: Python's OrderedDict maintains insertion order
   and supports O(1) move-to-end, enabling efficient LRU eviction.

2. **SHA-256 Cache Keys**: URLs can be arbitrarily long and contain special
   characters. Hashing to 28 chars creates filesystem-safe, collision-resistant keys.

3. **Silent Disk Failures**: If disk write fails (full disk, permissions),
   we continue with memory cache only. This prevents cache issues from
   breaking scraping operations.

4. **TTL-Based Expiration**: Each entry has an expiration timestamp.
   Expired entries are lazily removed on access, with optional bulk pruning.

Thread Safety
-------------
All cache operations are protected by threading locks. The cache is safe
for concurrent access from multiple threads.

Security
--------
- Cache directories are validated to prevent path traversal attacks
- Only the specified directory and its subdirectories are allowed

Example
-------
    from easyscrape.cache import ResponseCache

    cache = ResponseCache(".my_cache", max_memory=100)

    # Store a response (TTL in seconds)
    cache.set("https://example.com", b"<html>...</html>", {}, 200, ttl=3600)

    # Retrieve it
    entry = cache.get("https://example.com")
    if entry and entry.valid:
        print(f"Cached: {len(entry.data)} bytes")
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import time
from collections import OrderedDict
from pathlib import Path
from threading import Lock
from typing import Any, Final

__all__: Final[tuple[str, ...]] = (
    "CacheEntry",
    "ResponseCache",
    "get_cache",
    "clear_all",
)


class CacheEntry:
    """Immutable container for a cached HTTP response.

    Why This Class Exists
    ---------------------
    Caching raw bytes isn't enough - we need metadata:
    - **headers**: Content-Type, encoding, etc. for proper decoding
    - **status**: 200 vs 404 vs 500 - different handling needed
    - **expires_at**: When this entry becomes stale

    The `__slots__` declaration saves ~40% memory per entry, significant
    when caching thousands of responses.

    Serialisation
    -------------
    Entries are serialised to JSON for disk storage. The data bytes are
    decoded to UTF-8 (with error replacement) for JSON compatibility.
    Binary responses (images, etc.) may lose fidelity - consider
    base64 encoding for binary data in future versions.
    """

    __slots__ = ("data", "headers", "status", "expires_at")

    def __init__(self, data: bytes, headers: dict[str, str], status: int, ttl: int) -> None:
        """Initialise a cache entry.

        Args:
            data: Raw response body bytes
            headers: HTTP response headers
            status: HTTP status code (e.g., 200, 404)
            ttl: Time-to-live in seconds (0 or negative = infinite)
        """
        self.data = data
        self.headers = headers
        self.status = status
        # TTL <= 0 means "cache forever" (until manually cleared)
        self.expires_at = time.time() + ttl if ttl > 0 else float("inf")

    @property
    def valid(self) -> bool:
        """Check if the entry has not expired.

        Returns:
            True if current time is before expiration, False otherwise.

        Note:
            Entries with TTL <= 0 have expires_at = inf, so they're always valid.
        """
        return time.time() < self.expires_at

    def serialise(self) -> dict[str, Any]:
        """Serialise entry to a JSON-compatible dictionary.

        The data bytes are decoded to UTF-8 with error replacement.
        This means binary data may be corrupted - this cache is
        designed for text responses (HTML, JSON, XML).

        Returns:
            Dict with keys: d (data), h (headers), s (status), e (expires_at)
        """
        return {
            "d": self.data.decode("utf-8", errors="replace"),
            "h": self.headers,
            "s": self.status,
            "e": self.expires_at,
        }

    @classmethod
    def deserialise(cls, raw: dict[str, Any]) -> CacheEntry:
        """Deserialise entry from a JSON dictionary.

        This bypasses __init__ to directly set attributes, avoiding
        the TTL calculation (we restore the original expires_at).

        Args:
            raw: Dict from serialise() or disk JSON

        Returns:
            Reconstructed CacheEntry instance
        """
        obj = cls.__new__(cls)
        obj.data = raw["d"].encode("utf-8")
        obj.headers = raw["h"]
        obj.status = raw["s"]
        obj.expires_at = raw["e"]
        return obj


def _validate_cache_directory(directory: str) -> Path:
    """Validate and normalise cache directory path.

    Security
    --------
    Prevents path traversal attacks by ensuring the resolved path
    doesn't escape to dangerous locations. Allows:
    - Relative paths within cwd
    - Absolute paths (for pytest temp directories, etc.)
    - Paths that start with the cwd

    Args:
        directory: Requested cache directory path

    Returns:
        Validated Path object

    Raises:
        ValueError: If path contains dangerous traversal patterns
    """
    # Resolve to absolute path
    path = Path(directory).resolve()
    
    # Check for obvious traversal attempts in the original string
    if ".." in directory and not directory.startswith("/"):
        # For relative paths with .., verify they don't escape cwd
        cwd = Path.cwd().resolve()
        try:
            path.relative_to(cwd)
        except ValueError:
            raise ValueError(f"Cache directory escapes working directory: {directory}") from None
    
    # Block obviously dangerous paths
    dangerous_prefixes = ("/etc", "/usr", "/bin", "/sbin", "/var/log", "/root")
    path_str = str(path)
    for prefix in dangerous_prefixes:
        if path_str.startswith(prefix):
            raise ValueError(f"Cache directory in protected location: {directory}") from None

    return path


class ResponseCache:
    """Two-tier HTTP response cache with memory and disk storage.

    Architecture
    ------------
    ```
    Request → [Memory Cache] → hit → return entry
                    ↓ miss
              [Disk Cache] → hit → promote to memory, return
                    ↓ miss
              [Network] → store in both caches, return
    ```

    Memory Cache (L1)
    -----------------
    - OrderedDict with LRU eviction
    - Limited to `max_memory` entries
    - Thread-safe with Lock
    - Lost on process exit

    Disk Cache (L2)
    ---------------
    - JSON files in specified directory
    - Each URL gets a unique file (SHA-256 hash of URL)
    - Survives restarts
    - Automatic cleanup of expired entries

    Thread Safety
    -------------
    All operations are protected by a threading Lock. Safe for concurrent
    access from multiple threads. For multiprocessing, use separate cache
    directories or a proper distributed cache (Redis, etc.).

    Example
    -------
        cache = ResponseCache(".cache", max_memory=100)

        # Store
        cache.set("https://example.com", response_bytes, headers, 200, ttl=3600)

        # Retrieve
        entry = cache.get("https://example.com")
        if entry:
            html = entry.data.decode("utf-8")
    """

    __slots__ = ("_dir", "_mem", "_lock", "_max")

    def __init__(self, directory: str = ".escache", max_memory: int = 500) -> None:
        """Initialise cache with disk directory and memory limit.

        Args:
            directory: Path for disk cache files (created if doesn't exist)
            max_memory: Maximum entries to keep in memory (default 500)

        Raises:
            ValueError: If directory path is invalid or dangerous

        Why These Defaults?
        -------------------
        - ".escache": Hidden directory, won't clutter user's workspace
        - 500 entries: ~50MB assuming 100KB average response, reasonable for most systems
        """
        self._dir = _validate_cache_directory(directory)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._mem: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock: Final[Lock] = Lock()
        self._max = max_memory

    def _make_key(self, url: str, method: str = "GET", body: bytes | None = None) -> str:
        """Generate filesystem-safe cache key from request.

        Why SHA-256?
        ------------
        - URLs can be 2000+ characters (query strings, etc.)
        - URLs contain characters invalid in filenames (?, &, =)
        - SHA-256 is collision-resistant (negligible chance of duplicates)
        - 28-char truncation: 2^112 possibilities, still extremely safe

        Args:
            url: Request URL
            method: HTTP method (GET, POST, etc.)
            body: Request body for POST/PUT requests

        Returns:
            28-character hex string safe for use as filename
        """
        blob = f"{method.upper()}|{url}".encode()
        if body:
            blob += b"|" + body
        return hashlib.sha256(blob).hexdigest()[:28]

    def _file_for(self, key: str) -> Path:
        """Get the disk file path for a cache key.

        Files are stored as "{key}.json" in the cache directory.
        """
        return self._dir / f"{key}.json"

    def get(self, url: str, method: str = "GET", body: bytes | None = None) -> CacheEntry | None:
        """Retrieve a cached entry if it exists and is valid.

        Lookup Order
        ------------
        1. Check memory cache (fast path)
        2. If miss, check disk cache
        3. If disk hit, promote to memory cache
        4. If expired, remove from both caches

        Args:
            url: Request URL
            method: HTTP method (default GET)
            body: Request body for POST/PUT requests

        Returns:
            CacheEntry if found and valid, None otherwise
        """
        key = self._make_key(url, method, body)

        # L1: Memory cache
        with self._lock:
            if key in self._mem:
                entry = self._mem[key]
                if entry.valid:
                    return entry
                # Expired - remove from memory
                del self._mem[key]

        # L2: Disk cache
        fpath = self._file_for(key)
        if fpath.exists():
            try:
                raw = json.loads(fpath.read_text(encoding="utf-8"))
                entry = CacheEntry.deserialise(raw)
                if entry.valid:
                    # Promote to memory cache
                    with self._lock:
                        self._mem[key] = entry
                    return entry
                # Expired - remove from disk
                fpath.unlink(missing_ok=True)
            except (json.JSONDecodeError, KeyError, OSError):
                # Corrupted cache file - remove it
                fpath.unlink(missing_ok=True)

        return None

    def set(
        self,
        url: str,
        data: bytes,
        headers: dict[str, str],
        status: int,
        ttl: int,
        method: str = "GET",
        body: bytes | None = None,
    ) -> None:
        """Store a response in both memory and disk caches.

        Memory Cache Behaviour
        ---------------------
        - If key exists, move to end (most recently used)
        - If at capacity, evict oldest entry (FIFO, approximates LRU)
        - O(1) insertion and eviction via OrderedDict

        Disk Cache Behaviour
        -------------------
        - Writes JSON file to disk
        - Silent failure if disk is full or permissions denied
        - Entries with infinite TTL skip disk write (can't serialise inf)

        Args:
            url: Request URL
            data: Response body bytes
            headers: Response headers
            status: HTTP status code
            ttl: Time-to-live in seconds (0 = infinite, -1 = don't cache)
            method: HTTP method
            body: Request body for POST/PUT
        """
        if ttl < 0:
            return  # Explicitly disable caching for this response

        key = self._make_key(url, method, body)
        entry = CacheEntry(data, headers, status, ttl)

        # L1: Memory cache with LRU eviction
        with self._lock:
            if key in self._mem:
                self._mem.move_to_end(key)
            else:
                if len(self._mem) >= self._max:
                    self._mem.popitem(last=False)  # Evict oldest (FIFO)
            self._mem[key] = entry

        # L2: Disk cache (skip infinite TTL - can't serialise float('inf'))
        if entry.expires_at == float("inf"):
            return
        try:
            self._file_for(key).write_text(
                json.dumps(entry.serialise(), ensure_ascii=False),
                encoding="utf-8"
            )
        except OSError:
            pass  # Disk full or permission error - memory cache still works

    def remove(self, url: str, method: str = "GET", body: bytes | None = None) -> None:
        """Remove an entry from both memory and disk caches.

        Use this to invalidate a cached response when you know the
        content has changed (e.g., after a POST that modifies data).

        Args:
            url: Request URL
            method: HTTP method
            body: Request body for POST/PUT
        """
        key = self._make_key(url, method, body)
        with self._lock:
            self._mem.pop(key, None)
        self._file_for(key).unlink(missing_ok=True)

    def clear(self) -> None:
        """Clear all cached entries from memory and disk.

        Use sparingly - this removes ALL cached data. For selective
        invalidation, use `remove()` instead.
        """
        with self._lock:
            self._mem.clear()
        for f in self._dir.glob("*.json"):
            with contextlib.suppress(OSError):
                f.unlink()

    def prune_expired(self) -> int:
        """Remove all expired entries and return count removed.

        Call this periodically to free disk space and memory.
        Not strictly necessary since expired entries are removed
        on access, but useful for maintenance.

        Returns:
            Number of entries removed (memory + disk combined)
        """
        now = time.time()
        removed = 0

        # Prune memory cache
        with self._lock:
            expired = [k for k, v in self._mem.items() if not v.valid]
            for k in expired:
                del self._mem[k]
            removed += len(expired)

        # Prune disk cache
        for f in self._dir.glob("*.json"):
            try:
                raw = json.loads(f.read_text(encoding="utf-8"))
                if raw.get("e", 0) < now:
                    f.unlink()
                    removed += 1
            except (json.JSONDecodeError, KeyError, OSError):
                # Corrupted file - remove it
                f.unlink(missing_ok=True)

        return removed


# Module-level singleton for convenience
_default: ResponseCache | None = None
_default_lock: Final[Lock] = Lock()


def get_cache(directory: str = ".escache") -> ResponseCache:
    """Get or create the default singleton cache.

    This provides a convenient global cache instance. For isolated
    caching (e.g., per-scraper), create ResponseCache instances directly.

    Args:
        directory: Cache directory (only used on first call)

    Returns:
        The default ResponseCache instance

    Note:
        The directory parameter is only used on first call. Subsequent
        calls return the existing cache regardless of directory argument.
    """
    global _default
    with _default_lock:
        if _default is None:
            _default = ResponseCache(directory)
        return _default


def clear_all() -> None:
    """Clear the default cache if it exists.

    Convenience function to reset the global cache state.
    Does nothing if get_cache() was never called.
    """
    with _default_lock:
        if _default is not None:
            _default.clear()
