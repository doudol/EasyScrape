"""Tests for log module."""

import pytest
import logging
from easyscrape.log import (
    get_logger,
    configure_logging,
    enable_debug_logging,
    disable_logging,
    LogContext,
)


class TestGetLogger:
    """Tests for get_logger."""

    def test_returns_logger(self):
        """Test returns logger."""
        logger = get_logger()
        assert isinstance(logger, logging.Logger)

    def test_with_name(self):
        """Test with custom name."""
        logger = get_logger("custom")
        assert isinstance(logger, logging.Logger)


class TestConfigureLogging:
    """Tests for configure_logging."""

    def test_configure(self):
        """Test configure doesn't raise."""
        configure_logging(level=logging.INFO)


class TestEnableDebugLogging:
    """Tests for enable_debug_logging."""

    def test_enable(self):
        """Test enable doesn't raise."""
        enable_debug_logging()


class TestDisableLogging:
    """Tests for disable_logging."""

    def test_disable(self):
        """Test disable doesn't raise."""
        disable_logging()


class TestLogContext:
    """Tests for LogContext."""

    def test_creation(self):
        """Test context creation."""
        ctx = LogContext()
        assert ctx is not None



class TestLogContextMethods:
    """Tests for LogContext class methods."""
    
    def test_context_manager(self):
        """Test LogContext as context manager."""
        with LogContext(url="https://test.com", attempt="1") as ctx:
            assert ctx is not None
            current = LogContext.get_context()
            assert current["url"] == "https://test.com"
            assert current["attempt"] == "1"
    
    def test_context_restored_after_exit(self):
        """Test context is restored after exit."""
        # Clear any existing context
        with LogContext():
            pass
        original = LogContext.get_context()
        with LogContext(key="value"):
            assert LogContext.get_context()["key"] == "value"
        # Should be restored
        assert "key" not in LogContext.get_context() or LogContext.get_context() == original
    
    def test_format_context_empty(self):
        """Test format_context with empty context."""
        # Clear context
        with LogContext():
            result = LogContext.format_context()
        # After exit, format should work
        formatted = LogContext.format_context()
        assert isinstance(formatted, str)
    
    def test_format_context_with_values(self):
        """Test format_context with values."""
        with LogContext(foo="bar", num="123"):
            result = LogContext.format_context()
            assert "foo=bar" in result
            assert "num=123" in result
            assert result.startswith("[")
            assert result.endswith("] ")
    
    def test_get_context_returns_copy(self):
        """Test get_context returns a copy."""
        with LogContext(test="value"):
            ctx = LogContext.get_context()
            ctx["new"] = "added"
            # Original should not be affected
            assert "new" not in LogContext.get_context() or LogContext.get_context().get("new") != "added"


class TestConfigureLoggingAdvanced:
    """Advanced tests for configure_logging."""
    
    def test_with_custom_handler(self):
        """Test with custom handler."""
        handler = logging.StreamHandler()
        configure_logging(level=logging.INFO, handler=handler)
    
    def test_with_custom_format(self):
        """Test with custom format string."""
        configure_logging(level=logging.INFO, format_string="%(message)s")
