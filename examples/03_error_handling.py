#!/usr/bin/env python3
"""Error handling examples.

Run: python 03_error_handling.py
"""
import easyscrape as es
from easyscrape.exceptions import (
    EasyScrapeError,
    NetworkError,
    HTTPError,
    InvalidURLError,
    RequestTimeout,
    RateLimitHit,
    RetryExhausted,
)


def catch_all_errors():
    """Catch any EasyScrape error."""
    try:
        result = es.scrape("https://httpbin.org/status/500")
    except EasyScrapeError as e:
        print(f"  Caught: {type(e).__name__}: {e}")


def specific_errors():
    """Handle specific error types."""
    urls = [
        ("https://httpbin.org/status/404", "Not Found"),
        ("https://httpbin.org/status/500", "Server Error"),
        ("https://httpbin.org/delay/10", "Timeout"),
    ]

    config = es.Config(timeout=2.0, max_retries=1)

    for url, description in urls:
        print(f"\n  Testing: {description}")
        try:
            result = es.scrape(url, config=config)
            print(f"    Success: {result.status_code}")
        except RequestTimeout:
            print("    Caught: RequestTimeout")
        except HTTPError as e:
            print(f"    Caught: HTTPError (status={e.status_code})")
        except NetworkError as e:
            print(f"    Caught: NetworkError ({e})")
        except RetryExhausted as e:
            print(f"    Caught: RetryExhausted (attempts={e.attempts})")


def invalid_urls():
    """Handle invalid URLs."""
    bad_urls = [
        "not-a-url",
        "javascript:alert(1)",
        "http://localhost/admin",
        "http://169.254.169.254/metadata",
    ]

    for url in bad_urls:
        try:
            es.scrape(url)
        except InvalidURLError as e:
            print(f"  Blocked: {url[:30]}... ({e.reason})")


def graceful_degradation():
    """Continue scraping despite errors."""
    urls = [
        "https://httpbin.org/html",
        "https://httpbin.org/status/404",
        "https://httpbin.org/html",
        "https://httpbin.org/status/500",
        "https://httpbin.org/html",
    ]

    config = es.Config(max_retries=1)
    results = []
    errors = []

    for url in urls:
        try:
            result = es.scrape(url, config=config)
            if result.ok:
                results.append(result)
            else:
                errors.append((url, f"HTTP {result.status_code}"))
        except EasyScrapeError as e:
            errors.append((url, str(e)))

    print(f"  Successful: {len(results)}")
    print(f"  Failed: {len(errors)}")
    for url, error in errors:
        print(f"    - {url}: {error[:50]}")


def main():
    print("=" * 60)
    print("  Error Handling Examples")
    print("=" * 60)

    print("\n1. Catch All Errors")
    print("-" * 40)
    catch_all_errors()

    print("\n2. Specific Error Types")
    print("-" * 40)
    specific_errors()

    print("\n3. Invalid URLs (Security)")
    print("-" * 40)
    invalid_urls()

    print("\n4. Graceful Degradation")
    print("-" * 40)
    graceful_degradation()


if __name__ == "__main__":
    main()
