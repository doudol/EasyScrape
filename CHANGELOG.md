# Changelog

All notable changes to EasyScrape will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-12-21

### Added

- Core scraping functions (`scrape`, `scrape_many`, `post`, `download`)
- Async scraping (`async_scrape`, `async_scrape_many`)
- CSS and XPath extraction with selectolax
- Structured data extraction with `extract()` and `extract_all()`
- Built-in helpers: `title()`, `main_text()`, `safe_links()`, `safe_images()`, `json_ld()`
- ETag/conditional fetching with `scrape_if_changed()`
- Two-tier caching (memory + disk)
- Automatic retries with exponential backoff
- Rate limiting (per-domain throttling)
- Circuit breaker pattern for fault tolerance
- Proxy rotation (round-robin, random)
- User agent rotation
- JavaScript rendering via Playwright
- Stealth mode via curl_cffi
- Multiple export formats (JSON, CSV, JSONL, Excel, Parquet, SQLite)
- Pagination helpers
- robots.txt support
- CLI interface
- Comprehensive test suite

### Security

- SSRF protection blocks localhost, private networks, cloud metadata endpoints
- Path traversal prevention in file operations
- Dangerous URI filtering (javascript:, data:, file:)
- Safe defaults (SSL verification, redirect limits)

### Performance

- 90ms import time via lazy loading
- 10x faster HTML parsing than BeautifulSoup
- URL validation caching
- XPath expression caching
