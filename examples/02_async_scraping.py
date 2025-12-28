#!/usr/bin/env python3
"""Asynchronous scraping examples.

Run: python 02_async_scraping.py
"""
import asyncio
import time

import easyscrape as es
from easyscrape import async_scrape, async_scrape_many, Config


async def single_async():
    """Single async request."""
    result = await async_scrape("https://httpbin.org/delay/1")
    print(f"Status: {result.status_code}")


async def batch_async():
    """Batch async requests with progress."""
    urls = [
        f"https://httpbin.org/anything/{i}"
        for i in range(10)
    ]

    config = Config(
        concurrent_limit=5,
        rate_limit=10.0,
    )

    start = time.time()
    count = 0

    async for result in async_scrape_many(urls, config=config):
        count += 1
        print(f"  [{count}/{len(urls)}] {result.url} -> {result.status_code}")

    elapsed = time.time() - start
    print(f"\n  Completed {count} requests in {elapsed:.2f}s")
    print(f"  ({count/elapsed:.1f} requests/second)")


async def compare_sync_vs_async():
    """Compare sync vs async performance."""
    urls = [f"https://httpbin.org/delay/0.1" for _ in range(5)]

    # Sync (sequential)
    start = time.time()
    for url in urls:
        es.scrape(url)
    sync_time = time.time() - start

    # Async (concurrent)
    start = time.time()
    async for _ in async_scrape_many(urls, config=Config(concurrent_limit=5)):
        pass
    async_time = time.time() - start

    print(f"  Sync (sequential):  {sync_time:.2f}s")
    print(f"  Async (concurrent): {async_time:.2f}s")
    print(f"  Speedup: {sync_time/async_time:.1f}x")


def main():
    print("=" * 60)
    print("  Async Scraping Examples")
    print("=" * 60)

    print("\n1. Single Async Request")
    print("-" * 40)
    asyncio.run(single_async())

    print("\n2. Batch Async Requests")
    print("-" * 40)
    asyncio.run(batch_async())

    print("\n3. Sync vs Async Comparison")
    print("-" * 40)
    asyncio.run(compare_sync_vs_async())


if __name__ == "__main__":
    main()
