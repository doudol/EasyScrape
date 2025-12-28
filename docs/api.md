# API Reference

Complete reference for the EasyScrape API.

## Core Functions

### `scrape()`

```python
es.scrape(url: str, **options) -> ScrapeResult
```

Fetch a URL and return a result object.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | required | The URL to fetch |
| `method` | `str` | `"GET"` | HTTP method |
| `headers` | `dict` | `None` | Custom headers |
| `timeout` | `float` | `30.0` | Request timeout in seconds |
| `retries` | `int` | `3` | Number of retry attempts |
| `follow_redirects` | `bool` | `True` | Follow HTTP redirects |

**Returns:** `ScrapeResult` object

**Example:**

```python
result = es.scrape(
    "https://example.com",
    timeout=10,
    headers={"Accept-Language": "en-GB"}
)
```

---

### `async_scrape()`

```python
await es.async_scrape(url: str, **options) -> ScrapeResult
```

Async version of `scrape()`. Same parameters.

**Example:**

```python
import asyncio
import easyscrape as es

async def main():
    result = await es.async_scrape("https://example.com")
    print(result.title())

asyncio.run(main())
```

---

## ScrapeResult

The result object returned by `scrape()` and `async_scrape()`.

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `status_code` | `int` | HTTP status code |
| `text` | `str` | Response body as text |
| `content` | `bytes` | Response body as bytes |
| `headers` | `dict` | Response headers |
| `url` | `str` | Final URL (after redirects) |

### Methods

#### `css(selector: str) -> str | None`

Extract the text of the first matching element.

```python
title = result.css("h1")
```

#### `css_all(selector: str) -> list[str]`

Extract text from all matching elements.

```python
items = result.css_all("li.item")
```

#### `json() -> dict | list`

Parse response as JSON.

```python
data = result.json()
```

#### `title() -> str | None`

Get the page title.

#### `main_text() -> str`

Extract main content, stripped of navigation and boilerplate.

#### `safe_links() -> list[str]`

Get all links, filtered to remove unsafe protocols.

---

## Configuration

### `Config`

```python
from easyscrape import Config

config = Config(
    timeout=60,
    retries=5,
    user_agent="MyBot/1.0"
)

result = es.scrape("https://example.com", config=config)
```

See [Configuration Guide](configuration.md) for details.
