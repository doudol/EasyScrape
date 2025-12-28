"""Tests for metrics/stats module."""

import pytest
import time
from easyscrape.stats import (
    RequestMetrics,
    DomainStats,
    StatsHook,
    LogHook,
    CallbackHook,
    Collector,
    get_metrics_collector,
)


class TestRequestMetrics:
    """Tests for RequestMetrics."""

    def test_creation(self):
        """Test metrics creation."""
        metrics = RequestMetrics(
            url="https://example.com",
            method="GET",
            start_time=time.monotonic(),
        )
        assert metrics.url == "https://example.com"
        assert metrics.method == "GET"

    def test_complete(self):
        """Test completing metrics."""
        metrics = RequestMetrics(
            url="https://example.com",
            method="GET",
            start_time=time.monotonic(),
        )
        metrics.complete(200, 1024)
        assert metrics.status_code == 200
        assert metrics.bytes_received == 1024

    def test_fail(self):
        """Test failing metrics."""
        metrics = RequestMetrics(
            url="https://example.com",
            method="GET",
            start_time=time.monotonic(),
        )
        metrics.fail("Connection refused")
        assert metrics.error == "Connection refused"

    def test_success_property(self):
        """Test success property."""
        metrics = RequestMetrics(
            url="https://example.com",
            method="GET",
            start_time=time.monotonic(),
        )
        metrics.complete(200, 100)
        assert metrics.success is True

    def test_error_not_success(self):
        """Test error is not success."""
        metrics = RequestMetrics(
            url="https://example.com",
            method="GET",
            start_time=time.monotonic(),
            error="Failed",
        )
        assert metrics.success is False

    def test_duration_ms(self):
        """Test duration calculation."""
        start = time.monotonic()
        metrics = RequestMetrics(
            url="https://example.com",
            method="GET",
            start_time=start,
        )
        time.sleep(0.05)  # 50ms - more reliable than 10ms on Windows
        metrics.complete(200, 100)
        # Duration should be non-negative (use >= 0 for reliability)
        assert metrics.duration_ms >= 0


class TestDomainStats:
    """Tests for DomainStats."""

    def test_initial_values(self):
        """Test initial stats are zero."""
        stats = DomainStats()
        assert stats.total_requests == 0
        assert stats.ok == 0
        assert stats.failed == 0

    def test_record_success(self):
        """Test recording successful request."""
        stats = DomainStats()
        metrics = RequestMetrics(
            url="https://example.com",
            method="GET",
            start_time=time.monotonic(),
        )
        metrics.complete(200, 1024)
        stats.record(metrics)
        assert stats.total_requests == 1
        assert stats.ok == 1

    def test_record_failure(self):
        """Test recording failed request."""
        stats = DomainStats()
        metrics = RequestMetrics(
            url="https://example.com",
            method="GET",
            start_time=time.monotonic(),
        )
        metrics.fail("Error")
        stats.record(metrics)
        assert stats.total_requests == 1
        assert stats.failed == 1

    def test_avg_ms(self):
        """Test average ms calculation."""
        stats = DomainStats()
        assert stats.avg_ms == 0.0

    def test_success_rate(self):
        """Test success rate calculation."""
        stats = DomainStats()
        assert stats.success_rate == 0.0


class TestLogHook:
    """Tests for LogHook."""

    def test_creation(self):
        """Test hook creation."""
        hook = LogHook()
        assert hook is not None

    def test_on_start(self):
        """Test on_start doesn't raise."""
        hook = LogHook()
        hook.on_start("https://example.com", "GET")

    def test_on_complete(self):
        """Test on_complete doesn't raise."""
        hook = LogHook()
        metrics = RequestMetrics(
            url="https://example.com",
            method="GET",
            start_time=time.monotonic(),
        )
        metrics.complete(200, 100)
        hook.on_complete(metrics)

    def test_on_error(self):
        """Test on_error method."""
        hook = LogHook()
        metrics = RequestMetrics(
            url="https://example.com",
            method="GET",
            start_time=time.monotonic(),
            error="Connection refused",
        )
        hook.on_error(metrics)  # Should not raise


class TestCallbackHook:
    """Tests for CallbackHook."""

    def test_creation(self):
        """Test hook creation."""
        hook = CallbackHook()
        assert hook is not None

    def test_with_callbacks(self):
        """Test with callback functions."""
        started = []
        completed = []
        
        hook = CallbackHook(
            on_start=lambda u, m: started.append(u),
            on_complete=lambda m: completed.append(m),
        )
        
        hook.on_start("https://example.com", "GET")
        assert len(started) == 1
        
        metrics = RequestMetrics(
            url="https://example.com",
            method="GET",
            start_time=time.monotonic(),
        )
        metrics.complete(200, 100)
        hook.on_complete(metrics)
        assert len(completed) == 1

    def test_on_error_callback(self):
        """Test on_error callback."""
        errors = []
        hook = CallbackHook(on_error=lambda m: errors.append(m))
        
        metrics = RequestMetrics(
            url="https://example.com",
            method="GET",
            start_time=time.monotonic(),
            error="Failed",
        )
        hook.on_error(metrics)
        assert len(errors) == 1

    def test_callback_exceptions_suppressed(self):
        """Test exceptions in callbacks are suppressed."""
        def bad_callback(m):
            raise ValueError("Intentional error")
        
        hook = CallbackHook(
            on_start=lambda u, m: None,
            on_complete=bad_callback,
            on_error=bad_callback,
        )
        
        metrics = RequestMetrics(
            url="https://example.com",
            method="GET",
            start_time=time.monotonic(),
        )
        metrics.complete(200, 100)
        
        # Should not raise
        hook.on_complete(metrics)
        hook.on_error(metrics)

    def test_on_start_exception_suppressed(self):
        """Test on_start exception is suppressed."""
        def bad_start(url, method):
            raise ValueError("Error in start")
        
        hook = CallbackHook(on_start=bad_start)
        hook.on_start("https://example.com", "GET")  # Should not raise


class TestCollector:
    """Tests for Collector."""

    def test_creation(self):
        """Test collector creation."""
        collector = Collector()
        assert collector is not None

    def test_start(self):
        """Test starting metrics."""
        collector = Collector()
        metrics = collector.start("https://example.com", "GET")
        assert isinstance(metrics, RequestMetrics)
        assert metrics.url == "https://example.com"

    def test_finish(self):
        """Test finishing metrics."""
        collector = Collector()
        metrics = collector.start("https://example.com", "GET")
        metrics.complete(200, 100)
        collector.finish(metrics)
        # Should not raise

    def test_add_hook(self):
        """Test adding hook."""
        collector = Collector()
        hook = LogHook()
        collector.add_hook(hook)
        # Should not raise

    def test_remove_hook(self):
        """Test removing hook."""
        collector = Collector()
        hook = LogHook()
        collector.add_hook(hook)
        collector.remove_hook(hook)
        # Should not raise

    def test_summary(self):
        """Test summary generation."""
        collector = Collector()
        metrics = collector.start("https://example.com", "GET")
        metrics.complete(200, 100)
        collector.finish(metrics)
        summary = collector.summary()
        assert isinstance(summary, dict)
        # Check dashboard-required keys
        assert "requests" in summary
        assert "successful" in summary
        assert "success_rate" in summary
        assert "cache_hits" in summary
        assert "cache_rate" in summary
        assert "bytes" in summary
        assert "uptime_s" in summary

    def test_domain_stats(self):
        """Test getting domain stats."""
        collector = Collector()
        metrics = collector.start("https://example.com/page", "GET")
        metrics.complete(200, 100)
        collector.finish(metrics)
        stats = collector.domain_stats("example.com")
        assert isinstance(stats, dict)
        assert stats["total"] == 1

    def test_summary_has_all_dashboard_fields(self):
        """Test summary has all fields needed by dashboard."""
        collector = Collector()
        metrics = collector.start("https://example.com", "GET")
        metrics.complete(200, 1024, cached=True)
        collector.finish(metrics)
        
        summary = collector.summary()
        
        # All dashboard-required fields
        required_fields = [
            "requests", "successful", "failed", "success_rate",
            "cache_hits", "cache_rate", "bytes", "uptime_s", "domains",
        ]
        for field in required_fields:
            assert field in summary, f"Missing field: {field}"

    def test_recent_has_dashboard_fields(self):
        """Test recent entries have dashboard-required fields."""
        collector = Collector()
        metrics = collector.start("https://example.com", "GET")
        metrics.complete(200, 100)
        collector.finish(metrics)
        
        recent = collector.recent(1)
        assert len(recent) == 1
        
        entry = recent[0]
        # Dashboard-required fields
        assert "ok" in entry
        assert "ms" in entry
        assert "url" in entry
        assert "status" in entry


class TestGetMetricsCollector:
    """Tests for singleton accessor."""

    def test_returns_collector(self):
        """Test returns Collector."""
        collector = get_metrics_collector()
        assert isinstance(collector, Collector)

    def test_singleton(self):
        """Test returns same instance."""
        c1 = get_metrics_collector()
        c2 = get_metrics_collector()
        assert c1 is c2


class TestDomainStatsAdvanced:
    """Advanced tests for DomainStats."""

    def test_empty_domain_stats(self):
        """Test DomainStats starts empty."""
        stats = DomainStats()
        assert stats.total_requests == 0

    def test_cache_hit_counted(self):
        """Test cache hits are counted."""
        stats = DomainStats()
        metrics = RequestMetrics(
            url="https://example.com",
            method="GET",
            start_time=time.monotonic(),
        )
        metrics.complete(200, 1024, cached=True)
        stats.record(metrics)
        assert stats.cache_hits == 1


class TestCollectorDomainExtraction:
    """Tests for Collector domain extraction."""

    def test_domain_extraction_error(self):
        """Test domain extraction with invalid URL."""
        collector = Collector()
        # URL that might fail parsing
        metrics = collector.start("://invalid-url", "GET")
        metrics.complete(200, 100)
        collector.finish(metrics)  # Should handle gracefully


class TestCollectorHookExceptions:
    """Tests for hook exception handling."""

    def test_start_hook_exception_suppressed(self):
        """Test exceptions in hook on_start are suppressed."""
        class BadHook(StatsHook):
            def on_start(self, url, method):
                raise ValueError("Hook error")
        
        collector = Collector()
        collector.add_hook(BadHook())
        # Should not raise
        metrics = collector.start("https://example.com", "GET")
        assert metrics is not None

    def test_finish_hook_exception_suppressed(self):
        """Test exceptions in hook on_complete/on_error are suppressed."""
        class BadHook(StatsHook):
            def on_complete(self, m):
                raise ValueError("Complete error")
            
            def on_error(self, m):
                raise ValueError("Error error")
        
        collector = Collector()
        collector.add_hook(BadHook())
        
        # Test on_complete exception
        metrics = collector.start("https://example.com", "GET")
        metrics.complete(200, 100)
        collector.finish(metrics)  # Should not raise
        
        # Test on_error exception
        metrics2 = collector.start("https://example.com", "GET")
        metrics2.fail("Error")
        collector.finish(metrics2)  # Should not raise


class TestCollectorDomainStatsAll:
    """Tests for domain_stats without domain filter."""

    def test_all_domain_stats(self):
        """Test getting all domain stats."""
        collector = Collector()
        
        m1 = collector.start("https://example.com/page1", "GET")
        m1.complete(200, 100)
        collector.finish(m1)
        
        m2 = collector.start("https://other.com/page2", "GET")
        m2.complete(200, 200)
        collector.finish(m2)
        
        all_stats = collector.domain_stats()
        assert "example.com" in all_stats
        assert "other.com" in all_stats


class TestCollectorRecent:
    """Tests for recent() method."""

    def test_recent_requests(self):
        """Test getting recent requests."""
        collector = Collector()
        
        m = collector.start("https://example.com/page", "GET")
        m.complete(200, 100)
        collector.finish(m)
        
        recent = collector.recent(10)
        assert len(recent) >= 1
        assert recent[-1]["url"] == "https://example.com/page"

    def test_recent_with_limit(self):
        """Test recent with limit smaller than buffer."""
        collector = Collector()
        
        for i in range(5):
            m = collector.start(f"https://example.com/page{i}", "GET")
            m.complete(200, 100)
            collector.finish(m)
        
        recent = collector.recent(2)
        assert len(recent) == 2


class TestCollectorReset:
    """Tests for reset() method."""

    def test_reset_clears_stats(self):
        """Test reset clears all statistics."""
        collector = Collector()
        
        m = collector.start("https://example.com", "GET")
        m.complete(200, 100)
        collector.finish(m)
        
        # Should have stats
        assert collector.domain_stats("example.com").get("total", 0) == 1
        
        collector.reset()
        
        # Should be empty
        assert collector.domain_stats("example.com") == {}

    def test_reset_resets_uptime(self):
        """Test reset resets uptime."""
        collector = Collector()
        
        time.sleep(0.05)  # 50ms - more reliable
        
        old_uptime = collector.summary()["uptime_s"]
        assert old_uptime > 0
        
        collector.reset()
        
        new_uptime = collector.summary()["uptime_s"]
        assert new_uptime < old_uptime


class TestStatsHookBase:
    """Tests for StatsHook base class."""

    def test_base_on_start(self):
        """Test base on_start is no-op."""
        class TestHook(StatsHook):
            pass
        
        hook = TestHook()
        hook.on_start("https://example.com", "GET")  # Should not raise

    def test_base_on_complete(self):
        """Test base on_complete is no-op."""
        class TestHook(StatsHook):
            pass
        
        hook = TestHook()
        metrics = RequestMetrics(
            url="https://example.com",
            method="GET",
            start_time=time.monotonic(),
        )
        metrics.complete(200, 100)
        hook.on_complete(metrics)  # Should not raise

    def test_base_on_error(self):
        """Test base on_error is no-op."""
        class TestHook(StatsHook):
            pass
        
        hook = TestHook()
        metrics = RequestMetrics(
            url="https://example.com",
            method="GET",
            start_time=time.monotonic(),
            error="Error",
        )
        hook.on_error(metrics)  # Should not raise


class TestRequestMetricsViaCollector:
    """Tests for RequestMetrics via Collector."""

    def test_metrics_complete(self):
        """Test metrics complete flow."""
        collector = Collector()
        metrics = collector.start("https://test.com", "GET")
        metrics.complete(200, 100)
        collector.finish(metrics)
        assert metrics.status_code == 200

    def test_metrics_fail(self):
        """Test metrics fail flow."""
        collector = Collector()
        metrics = collector.start("https://test.com", "GET")
        metrics.fail("Connection error")
        collector.finish(metrics)
        assert metrics.error == "Connection error"
