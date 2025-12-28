#!/usr/bin/env python3
"""Configuration options."""
from easyscrape import scrape, Config

config = Config(
    timeout=30.0,
    max_retries=3,
    cache_enabled=True,
    cache_ttl=3600,
    rate_limit=1.0,
)

result = scrape("https://example.com", config)
print("With config:", result.title())

fresh_config = Config(cache_enabled=False)
result = scrape("https://example.com", fresh_config)
print("Fresh fetch:", result.title())
