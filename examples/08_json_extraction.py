#!/usr/bin/env python3
"""
Example 08: JSON and Structured Data Extraction

Demonstrates extracting JSON-LD and other structured data from pages.
"""

import easyscrape as es
import json

def main():
    # Scrape a page with JSON-LD structured data
    result = es.scrape("https://www.imdb.com/title/tt0111161/")
    
    # Extract JSON-LD (commonly used for SEO structured data)
    json_ld = result.json_ld()
    
    if json_ld:
        print("=== JSON-LD Structured Data ===")
        print(json.dumps(json_ld, indent=2)[:1000])
    else:
        print("No JSON-LD found on this page")
    
    # Extract meta tags
    print("\n=== Meta Tags ===")
    meta = result.meta()
    for key, value in list(meta.items())[:5]:
        print(f"  {key}: {value[:50]}..." if len(value) > 50 else f"  {key}: {value}")
    
    # For API endpoints returning JSON directly
    print("\n=== Direct JSON API ===")
    api_result = es.scrape("https://httpbin.org/json")
    data = api_result.json()
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
