"""Logging utilities for EasyScrape.

This module provides logging configuration and context management
for structured logging throughout the library.

Example
-------
    from easyscrape.log import get_logger, LogContext

    logger = get_logger()
    with LogContext(url="https://example.com"):
        logger.info("Fetching page")
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Final

__all__: Final[tuple[str, ...]] = (
    "get_logger",
    "configure_logging",
    "enable_debug_logging",
    "disable_logging",
    "LogContext",
)


_LOGGER_NAME = "easyscrape"
_context_var: threading.local = threading.local()


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a logger instance.

    Parameters
    ----------
    name : str, optional
        Logger name. If None, uses the default EasyScrape logger.

    Returns
    -------
    logging.Logger
        The logger instance.
    """
    if name:
        return logging.getLogger(f"{_LOGGER_NAME}.{name}")
    return logging.getLogger(_LOGGER_NAME)


def configure_logging(
    level: int = logging.INFO,
    handler: logging.Handler | None = None,
    format_string: str | None = None,
) -> None:
    """Configure logging for EasyScrape.

    Parameters
    ----------
    level : int
        Logging level.
    handler : logging.Handler, optional
        Custom handler. If None, uses StreamHandler.
    format_string : str, optional
        Custom format string.
    """
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(level)

    # Remove existing handlers
    logger.handlers.clear()

    if handler is None:
        handler = logging.StreamHandler()

    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    handler.setFormatter(logging.Formatter(format_string))
    logger.addHandler(handler)


def enable_debug_logging() -> None:
    """Enable debug-level logging."""
    configure_logging(level=logging.DEBUG)


def disable_logging() -> None:
    """Disable all logging."""
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.CRITICAL + 1)
    logger.handlers.clear()


class LogContext:
    """Context manager for structured logging context.

    Adds contextual information to log messages within the context.

    Parameters
    ----------
    **kwargs
        Key-value pairs to add to the logging context.

    Example
    -------
        with LogContext(url="https://example.com", attempt="1"):
            logger.info("Fetching page")
            # Logs will include url and attempt context
    """

    def __init__(self, **kwargs: Any) -> None:
        self._context = kwargs
        self._previous: dict[str, Any] | None = None

    def __enter__(self) -> LogContext:
        self._previous = getattr(_context_var, "context", {}).copy()
        current = getattr(_context_var, "context", {})
        current.update(self._context)
        _context_var.context = current
        return self

    def __exit__(self, *args: Any) -> None:
        if self._previous is not None:
            _context_var.context = self._previous
        else:
            _context_var.context = {}

    @classmethod
    def get_context(cls) -> dict[str, Any]:
        """Get the current logging context.

        Returns
        -------
        dict
            Current context key-value pairs.
        """
        return getattr(_context_var, "context", {}).copy()

    @classmethod
    def format_context(cls) -> str:
        """Format the current context as a string.

        Returns
        -------
        str
            Formatted context string.
        """
        ctx = cls.get_context()
        if not ctx:
            return ""
        parts = [f"{k}={v}" for k, v in ctx.items()]
        return "[" + " ".join(parts) + "] "
