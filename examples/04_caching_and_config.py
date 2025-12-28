#!/usr/bin/env python3
"""Caching and configuration examples.

Run: python 04_caching_and_config.py
"""
import time

import easyscrape as es
from easyscrape import Config, ConfigBuilder


def caching_demo():
    """Demonstrate response caching."""
    config = Config(
        cache_enabled=True,
        cache_ttl=60,
    )

    url = "https://httpbin.org/uuid"

    # First request - cache miss
    start = time.time()
    result1 = es.scrape(url, config=config)
    time1 = time.time() - start
    print(f"  First request:  {time1*1000:.0f}ms (cache miss)")

    # Second request - cache hit
    start = time.time()
    result2 = es.scrape(url, config=config)
    time2 = time.time() - start
    print(f"  Second request: {time2*1000:.0f}ms (cache hit)")

    print(f"  Speedup: {time1/time2:.0f}x")


def config_presets():
    """Use configuration presets."""
    presets = [
        ("Default", Config()),
        ("Polite", Config.polite()),
        ("Aggressive", Config.aggressive()),
        ("Stealth", Config.stealth()),
        ("Development", Config.development()),
    ]

    for name, config in presets:
        print(f"\n  {name}:")
        print(f"    rate_limit: {config.rate_limit} req/s")
        print(f"    timeout: {config.timeout}s")
        print(f"    max_retries: {config.max_retries}")
        print(f"    respect_robots: {config.respect_robots}")


def config_builder():
    """Use the fluent config builder."""
    config = (
        ConfigBuilder()
        .timeout(60)
        .retries(5, delay=2.0, backoff=2.0)
        .rate_limit(2.0)
        .with_caching(ttl=3600)
        .verbose()
        .build()
    )

    print(f"  Built config:")
    print(f"    timeout: {config.timeout}s")
    print(f"    max_retries: {config.max_retries}")
    print(f"    cache_enabled: {config.cache_enabled}")
    print(f"    verbose: {config.verbose}")


def config_from_env():
    """Load config from environment variables."""
    import os

    # Set some env vars (in real code, these would be set externally)
    os.environ["EASYSCRAPE_TIMEOUT"] = "45"
    os.environ["EASYSCRAPE_CACHE_ENABLED"] = "true"

    config = Config.from_env()

    print(f"  From environment:")
    print(f"    timeout: {config.timeout}s")
    print(f"    cache_enabled: {config.cache_enabled}")

    # Clean up
    del os.environ["EASYSCRAPE_TIMEOUT"]
    del os.environ["EASYSCRAPE_CACHE_ENABLED"]


def main():
    print("=" * 60)
    print("  Caching and Configuration Examples")
    print("=" * 60)

    print("\n1. Response Caching")
    print("-" * 40)
    caching_demo()

    print("\n2. Configuration Presets")
    print("-" * 40)
    config_presets()

    print("\n3. Fluent Config Builder")
    print("-" * 40)
    config_builder()

    print("\n4. Config from Environment")
    print("-" * 40)
    config_from_env()


if __name__ == "__main__":
    main()
