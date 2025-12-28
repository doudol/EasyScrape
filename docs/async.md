# Async Scraping

Scrape multiple URLs concurrently for maximum speed.

## Basic Async

```python
import asyncio
import easyscrape as es

async def main():
    result = await es.async_scrape("https://example.com")
    print(result.title())

asyncio.run(main())
```

## Concurrent Requests

Scrape multiple URLs in parallel:

```python
import asyncio
import easyscrape as es

async def scrape_all(urls: list[str]):
    tasks = [es.async_scrape(url) for url in urls]
    results = await asyncio.gather(*tasks)
    return results

urls = [
    "https://example.com/page1",
    "https://example.com/page2",
    "https://example.com/page3",
]

results = asyncio.run(scrape_all(urls))

for result in results:
    print(f"{result.url}: {result.title()}")
```

## Rate-Limited Concurrency

Control the number of simultaneous requests:

```python
import asyncio
import easyscrape as es

async def scrape_with_limit(urls: list[str], max_concurrent: int = 5):
    semaphore = asyncio.Semaphore(max_concurrent)

    async def limited_scrape(url: str):
        async with semaphore:
            return await es.async_scrape(url)

    tasks = [limited_scrape(url) for url in urls]
    return await asyncio.gather(*tasks)
```

## Error Handling

Handle failures gracefully:

```python
import asyncio
import easyscrape as es

async def safe_scrape(url: str):
    try:
        return await es.async_scrape(url)
    except es.ScrapeError as e:
        print(f"Failed: {url} - {e}")
        return None

async def main():
    urls = ["https://example.com", "https://invalid.example"]
    tasks = [safe_scrape(url) for url in urls]
    results = await asyncio.gather(*tasks)
    
    successful = [r for r in results if r is not None]
    print(f"Succeeded: {len(successful)}/{len(urls)}")
```

## With Async Config

```python
from easyscrape import Config

config = Config(timeout=10, retries=2)

async def main():
    result = await es.async_scrape(
        "https://example.com",
        config=config
    )
```

## Best Practices

1. **Limit concurrency** - Don't overwhelm servers. Use semaphores.
2. **Handle errors** - Network requests fail. Plan for it.
3. **Respect robots.txt** - Check before bulk scraping.
4. **Add delays** - Use `rate_limit` in config for politeness.
