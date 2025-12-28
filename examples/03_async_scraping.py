"""Example 3: Async Scraping

This example shows how to scrape multiple URLs in parallel.
"""
import asyncio
from easyscrape import async_scrape
from easyscrape.async_core import async_scrape_many

async def main():
    # Single async request
    result = await async_scrape("https://example.com")
    print("Single result:", result.title())
    
    # Multiple URLs in parallel (10x faster than sequential)
    urls = [
        "https://example.com",
        "https://httpbin.org/html",
        "https://httpbin.org/json",
    ]
    
    results, errors = await async_scrape_many(urls, concurrency=3)
    
    print(f"\nGot {len(results)} results, {len(errors)} errors")
    for r in results:
        print(f"  - {r.url}: {r.status_code}")

if __name__ == "__main__":
    asyncio.run(main())
