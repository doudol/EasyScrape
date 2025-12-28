#!/usr/bin/env python3
"""
Example 09: Batch Scraping Multiple URLs

Demonstrates efficient batch scraping using async.
"""

import asyncio
import easyscrape as es

async def main():
    urls = [
        "https://httpbin.org/html",
        "https://httpbin.org/json", 
        "https://httpbin.org/robots.txt",
        "https://httpbin.org/headers",
    ]
    
    print(f"Scraping {len(urls)} URLs concurrently...")
    
    # Scrape all URLs concurrently
    results = await es.async_scrape_all(urls)
    
    print(f"\n=== Results ===")
    for url, result in zip(urls, results):
        status = result.status_code if result else "FAILED"
        size = len(result.text) if result else 0
        print(f"  {url}: {status} ({size} bytes)")


if __name__ == "__main__":
    asyncio.run(main())
