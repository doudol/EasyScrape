# Browser Mode

Handle JavaScript-rendered pages with browser automation.

## When to Use

Use browser mode when:

- Content is loaded via JavaScript
- Page requires interaction (clicks, scrolls)
- Site blocks non-browser requests
- You need screenshots

## Basic Usage

```python
import easyscrape as es

# Enable browser mode
result = es.scrape(
    "https://example.com",
    browser=True
)

# Works just like regular scraping
title = result.css("h1")
```

## Wait for Content

Wait for elements to appear:

```python
result = es.scrape(
    "https://example.com",
    browser=True,
    wait_for="div.content-loaded"
)
```

## JavaScript Execution

Run JavaScript on the page:

```python
result = es.scrape(
    "https://example.com",
    browser=True,
    js_script="window.scrollTo(0, document.body.scrollHeight)"
)
```

## Screenshots

Capture page screenshots:

```python
result = es.scrape(
    "https://example.com",
    browser=True,
    screenshot="page.png"
)
```

## Browser Options

```python
result = es.scrape(
    "https://example.com",
    browser=True,
    headless=True,      # Run without visible window (default)
    timeout=60,         # Page load timeout
    wait_for="h1",      # CSS selector to wait for
    js_script=None,     # JavaScript to execute
    screenshot=None,    # Path to save screenshot
)
```

## Async Browser

```python
import asyncio
import easyscrape as es

async def main():
    result = await es.async_scrape(
        "https://example.com",
        browser=True
    )
    print(result.title())

asyncio.run(main())
```

## Performance Tips

1. **Reuse sessions** - Browser startup is slow. Batch requests.
2. **Disable images** - Faster loads when you only need text.
3. **Use headless** - Always use headless mode in production.
4. **Set timeouts** - Prevent hangs on slow pages.

## Limitations

- Slower than HTTP requests (browser overhead)
- Higher memory usage
- Requires browser dependencies

For most sites, regular HTTP scraping is sufficient. Use browser mode only when needed.
