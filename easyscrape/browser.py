"""Browser automation for JavaScript-rendered pages.

This module provides browser automation using Playwright for scraping
pages that require JavaScript execution.

Example
-------
    from easyscrape.browser import Browser, render_js

    # Quick render
    html = await render_js("https://example.com")

    # Full browser control
    async with Browser() as browser:
        page = await browser.goto("https://example.com")
        await page.click("button.load-more")
        html = await page.content()
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Final

from .config import Config
from .exceptions import BrowserError

__all__: Final[tuple[str, ...]] = (
    "Browser",
    "BrowserPage",
    "render_js",
    "_validate_output_path",
    "_MS_PER_SECOND",
    "_MAX_SCROLL_ITERATIONS",
    "_DEFAULT_VIEWPORT_WIDTH",
    "_DEFAULT_VIEWPORT_HEIGHT",
)


_MS_PER_SECOND: Final[int] = 1000
_MAX_SCROLL_ITERATIONS: Final[int] = 100
_DEFAULT_VIEWPORT_WIDTH: Final[int] = 1920
_DEFAULT_VIEWPORT_HEIGHT: Final[int] = 1080


def _validate_output_path(
    path: str,
    allowed_extensions: list[str],
    create_parents: bool = True,
) -> Path:
    """Validate and resolve an output file path.

    Parameters
    ----------
    path : str
        The path to validate.
    allowed_extensions : list[str]
        List of allowed file extensions.
    create_parents : bool
        Whether to create parent directories.

    Returns
    -------
    Path
        The validated path.

    Raises
    ------
    BrowserError
        If the path is invalid.
    """
    try:
        resolved = Path(path).resolve()
    except (OSError, ValueError) as e:
        raise BrowserError(f"Invalid output path: {e}") from e

    # Check extension
    ext = resolved.suffix.lower()
    allowed_lower = [e.lower() for e in allowed_extensions]
    if ext not in allowed_lower:
        raise BrowserError(
            f"Invalid file extension '{ext}'. Allowed: {allowed_extensions}"
        )

    # Check for path traversal
    cwd = Path.cwd().resolve()
    try:
        resolved.relative_to(cwd)
    except ValueError:
        raise BrowserError(
            f"Path traversal detected: '{path}' resolves outside working directory"
        ) from None

    # Create parent directories
    if create_parents:
        resolved.parent.mkdir(parents=True, exist_ok=True)

    return resolved


class BrowserPage:
    """Wrapper around a Playwright page with convenience methods.

    Parameters
    ----------
    page : Any
        The Playwright page object.
    url : str
        The page URL.
    """

    __slots__ = ("_page", "_url", "_content_cache")

    def __init__(self, page: Any, url: str) -> None:
        self._page = page
        self._url = url
        self._content_cache: str | None = None

    @property
    def url(self) -> str:
        """Get the page URL."""
        return self._url

    async def content(self) -> str:
        """Get the page HTML content.

        Returns
        -------
        str
            The page HTML.
        """
        if self._content_cache is None:
            self._content_cache = await self._page.content()
        return self._content_cache

    async def click(self, selector: str) -> None:
        """Click an element.

        Parameters
        ----------
        selector : str
            CSS selector for the element.
        """
        await self._page.click(selector)
        self._content_cache = None

    async def fill(self, selector: str, value: str) -> None:
        """Fill a form field.

        Parameters
        ----------
        selector : str
            CSS selector for the input.
        value : str
            Value to fill.
        """
        await self._page.fill(selector, value)
        self._content_cache = None

    async def wait_for(self, selector: str, timeout: float = 30.0) -> None:
        """Wait for an element to appear.

        Parameters
        ----------
        selector : str
            CSS selector to wait for.
        timeout : float
            Maximum wait time in seconds.
        """
        await self._page.wait_for_selector(
            selector,
            timeout=timeout * _MS_PER_SECOND,
        )

    async def evaluate(self, script: str) -> Any:
        """Execute JavaScript and return the result.

        Parameters
        ----------
        script : str
            JavaScript code to execute.

        Returns
        -------
        Any
            The result of the script.
        """
        return await self._page.evaluate(script)

    async def screenshot(
        self,
        path: str,
        full_page: bool = False,
    ) -> None:
        """Take a screenshot.

        Parameters
        ----------
        path : str
            Output file path.
        full_page : bool
            Capture the full scrollable page.
        """
        validated = _validate_output_path(path, [".png", ".jpg", ".jpeg"])
        await self._page.screenshot(path=str(validated), full_page=full_page)

    async def pdf(self, path: str) -> None:
        """Save the page as PDF.

        Parameters
        ----------
        path : str
            Output file path.
        """
        validated = _validate_output_path(path, [".pdf"])
        await self._page.pdf(path=str(validated))

    async def scroll_to_bottom(self, delay: float = 0.5) -> None:
        """Scroll to the bottom of the page.

        Parameters
        ----------
        delay : float
            Delay between scroll steps.
        """
        for _ in range(_MAX_SCROLL_ITERATIONS):
            prev_height = await self._page.evaluate("document.body.scrollHeight")
            await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(delay)
            new_height = await self._page.evaluate("document.body.scrollHeight")
            if new_height == prev_height:
                break
        self._content_cache = None

    async def close(self) -> None:
        """Close the page."""
        await self._page.close()


class Browser:
    """Browser automation wrapper.

    Parameters
    ----------
    config : Config, optional
        Scraping configuration.
    headless : bool
        Run browser in headless mode.
    """

    def __init__(
        self,
        config: Config | None = None,
        headless: bool = True,
    ) -> None:
        self._config = config or Config()
        self._headless = headless
        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None

    async def __aenter__(self) -> Browser:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def _ensure_started(self) -> None:
        """Ensure browser is started."""
        if self._browser is not None:
            return

        try:
            from playwright.async_api import async_playwright
        except ImportError as e:
            raise BrowserError(
                "Playwright not installed. Install with: pip install playwright && playwright install"
            ) from e

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self._headless)

        # Create context with options
        context_options: dict[str, Any] = {
            "viewport": {
                "width": _DEFAULT_VIEWPORT_WIDTH,
                "height": _DEFAULT_VIEWPORT_HEIGHT,
            },
        }

        if self._config.proxies:
            context_options["proxy"] = {"server": self._config.proxies[0]}

        self._context = await self._browser.new_context(**context_options)

    async def goto(
        self,
        url: str,
        wait_for: str | None = None,
        timeout: float | None = None,
    ) -> BrowserPage:
        """Navigate to a URL.

        Parameters
        ----------
        url : str
            URL to navigate to.
        wait_for : str, optional
            CSS selector to wait for after navigation.
        timeout : float, optional
            Navigation timeout in seconds.

        Returns
        -------
        BrowserPage
            The page wrapper.
        """
        await self._ensure_started()

        page = await self._context.new_page()
        timeout_ms = (timeout or self._config.timeout) * _MS_PER_SECOND

        try:
            await page.goto(url, timeout=timeout_ms)
        except Exception as e:
            await page.close()
            raise BrowserError(f"Navigation to {url} failed: {e}") from e

        if wait_for:
            try:
                await page.wait_for_selector(wait_for, timeout=timeout_ms)
            except Exception:
                pass  # Continue even if wait times out

        return BrowserPage(page, url)

    async def get_html(self, url: str, wait_for: str | None = None) -> str:
        """Get rendered HTML from a URL.

        Parameters
        ----------
        url : str
            URL to render.
        wait_for : str, optional
            CSS selector to wait for.

        Returns
        -------
        str
            The rendered HTML.
        """
        page = await self.goto(url, wait_for=wait_for)
        try:
            return await page.content()
        finally:
            await page.close()

    async def close(self) -> None:
        """Close the browser."""
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None


async def render_js(
    url: str,
    wait_for: str | None = None,
    config: Config | None = None,
) -> str:
    """Render a page with JavaScript and return HTML.

    Convenience function for one-off renders.

    Parameters
    ----------
    url : str
        URL to render.
    wait_for : str, optional
        CSS selector to wait for.
    config : Config, optional
        Scraping configuration.

    Returns
    -------
    str
        The rendered HTML.

    Example
    -------
        html = await render_js("https://example.com", wait_for=".content")
    """
    async with Browser(config=config) as browser:
        return await browser.get_html(url, wait_for=wait_for)
