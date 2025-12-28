# Quick Start

Get scraping in under 5 minutes.

## Installation

```bash
pip install easyscrape
```

## Your First Scrape

```python
import easyscrape as es

# Fetch a page
result = es.scrape("https://httpbin.org/html")

# Check the response
print(result.status_code)  # 200
print(len(result.text))    # Content length
```

## Extract Data

Use CSS selectors (same syntax as browser DevTools):

```python
# Single element
heading = result.css("h1")

# Multiple elements
paragraphs = result.css_all("p")

# With attributes
links = result.css_all("a[href]")
```

## Built-in Helpers

Common tasks have convenience methods:

```python
# Page title
result.title()

# Main content (strips boilerplate)
result.main_text()

# All links (filtered for safety)
result.safe_links()
```

## JSON APIs

Works seamlessly with JSON:

```python
result = es.scrape("https://api.example.com/data")
data = result.json()
```

## Next Steps

- [Tutorial](tutorial.md) - Complete learning guide
- [Configuration](configuration.md) - Customise behaviour
- [Async Guide](async.md) - Concurrent scraping
