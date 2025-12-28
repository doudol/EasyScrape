#!/usr/bin/env python3
"""Basic scraping example."""
from easyscrape import scrape

result = scrape("https://example.com")

print("Title:", result.title())
print("H1:", result.css("h1"))
print("Links:", result.safe_links())
print("Content:", result.main_text()[:200])
