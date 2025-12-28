#!/usr/bin/env python3
"""
Example 06: Error Handling

Demonstrates proper error handling patterns with easyscrape.
"""

import easyscrape as es

def main():
    # Handle various error scenarios
    
    # 1. Invalid URL
    print("=== Testing Invalid URL ===")
    try:
        result = es.scrape("not-a-valid-url")
    except Exception as e:
        print(f"Caught error: {type(e).__name__}: {e}")
    
    # 2. Non-existent domain
    print("\n=== Testing Non-existent Domain ===")
    try:
        result = es.scrape("https://this-domain-definitely-does-not-exist-12345.com")
    except Exception as e:
        print(f"Caught error: {type(e).__name__}: {e}")
    
    # 3. HTTP error status (404)
    print("\n=== Testing 404 Response ===")
    result = es.scrape("https://httpbin.org/status/404")
    print(f"Status code: {result.status_code}")
    print(f"Is success: {result.status_code == 200}")
    
    # 4. Timeout handling
    print("\n=== Testing with Custom Timeout ===")
    config = es.Config(timeout=5.0)
    try:
        # This endpoint delays response by 10 seconds, our timeout is 5
        result = es.scrape("https://httpbin.org/delay/10", config=config)
    except Exception as e:
        print(f"Timeout caught: {type(e).__name__}")


if __name__ == "__main__":
    main()
