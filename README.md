# EasyScrape

[![PyPI](https://img.shields.io/pypi/v/easyscrape.svg)](https://pypi.org/project/easyscrape-py/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

**Fast, secure web scraping for Python.**

```python
from easyscrape import scrape

result = scrape("https://example.com")
print(result.css("h1"))  # "Example Domain"
```

## Features

- **Simple API**: One function to fetch and extract data
- **CSS & XPath**: Use familiar selectors
- **Built-in security**: SSRF protection, path traversal prevention
- **Automatic retries**: Exponential backoff on failures
- **Rate limiting**: Respect server limits
- **Caching**: Two-tier memory and disk cache
- **Async support**: High-performance concurrent scraping
- **JavaScript rendering**: Optional Playwright integration

## Installation

```bash
pip install easyscrape-py

# Optional: JavaScript rendering
pip install easyscrape-py[browser]
playwright install chromium

# Optional: Data export (Excel, Parquet)
pip install easyscrape-py[export]

# Everything
pip install easyscrape-py[all]
```

## Quick Start

### Basic Scraping

```python
from easyscrape import scrape

result = scrape("https://example.com")

# Extract single element
title = result.css("h1")

# Extract all matching elements
links = result.css_list("a", "href")

# Extract structured data
data = result.extract({
    "title": "h1",
    "description": "meta[name=description]::attr(content)",
})
```

### Multiple Items

```python
books = result.extract_all(".product", {
    "title": "h3 a::attr(title)",
    "price": ".price::text",
    "url": "a::attr(href)",
})
```

### Configuration

```python
from easyscrape import scrape, Config

config = Config(
    timeout=60.0,
    max_retries=5,
    rate_limit=1.0,  # 1 request/second
    cache_enabled=True,
)

result = scrape("https://example.com", config=config)
```

### Async Scraping

```python
import asyncio
from easyscrape import async_scrape_many

async def main():
    urls = [f"https://example.com/page/{i}" for i in range(100)]
    results = await async_scrape_many(urls)
    return [r.css("h1") for r in results if r.ok]

titles = asyncio.run(main())
```

### JavaScript Rendering

```python
config = Config(javascript=True)
result = scrape("https://spa-site.com", config=config)
```

## CLI

```bash
# Get all links
easyscrape https://example.com --links

# Extract specific fields
easyscrape https://example.com -e title=h1 -e desc=.description

# Extract multiple items to CSV
easyscrape https://example.com -e name=.name -c .product -o data.csv -f csv
```

## Error Handling

```python
from easyscrape import scrape
from easyscrape.exceptions import NetworkError, HTTPError, RateLimitHit

try:
    result = scrape(url)
except RateLimitHit:
    time.sleep(60)
    result = scrape(url)
except HTTPError as e:
    print(f"HTTP {e.status_code}")
except NetworkError as e:
    print(f"Network error: {e}")
```

## Security

EasyScrape includes built-in protections:

- **SSRF protection**: Blocks requests to localhost, private IPs, cloud metadata endpoints
- **Path traversal prevention**: Validates file paths in export functions
- **Safe defaults**: SSL verification enabled, redirect limits enforced

## Documentation

- [Tutorial](docs/TUTORIAL.md)
- [Examples](examples/)

## License

MIT
