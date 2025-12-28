# Configuration

Customise EasyScrape behaviour to match your needs.

## Basic Configuration

Pass options directly to `scrape()`:

```python
import easyscrape as es

result = es.scrape(
    "https://example.com",
    timeout=60,
    retries=5,
    headers={"Accept-Language": "en-GB"}
)
```

## Config Object

For reusable configuration, use the `Config` class:

```python
from easyscrape import Config

config = Config(
    timeout=60,
    retries=5,
    user_agent="MyResearchBot/1.0 (contact@example.com)",
    rate_limit=2.0,  # seconds between requests
)

# Use with any scrape
result = es.scrape("https://example.com", config=config)
```

## Available Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `timeout` | `float` | `30.0` | Request timeout in seconds |
| `retries` | `int` | `3` | Retry attempts for failed requests |
| `user_agent` | `str` | Auto | Custom User-Agent header |
| `rate_limit` | `float` | `0` | Minimum seconds between requests |
| `follow_redirects` | `bool` | `True` | Follow HTTP redirects |
| `verify_ssl` | `bool` | `True` | Verify SSL certificates |
| `proxy` | `str` | `None` | Proxy URL |

## Headers

Set custom headers:

```python
config = Config(
    headers={
        "Accept-Language": "en-GB,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "DNT": "1",
    }
)
```

## Proxies

Route requests through a proxy:

```python
config = Config(
    proxy="http://user:pass@proxy.example.com:8080"
)
```

## Rate Limiting

Be respectful to servers:

```python
config = Config(
    rate_limit=1.0  # Wait 1 second between requests
)

# Each call respects the rate limit
for url in urls:
    result = es.scrape(url, config=config)
```

## Environment Variables

Configuration can also be set via environment variables:

```bash
export EASYSCRAPE_TIMEOUT=60
export EASYSCRAPE_RETRIES=5
export EASYSCRAPE_USER_AGENT="MyBot/1.0"
```

Environment variables are overridden by explicit configuration.
