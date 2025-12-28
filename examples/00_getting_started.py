#!/usr/bin/env python3
"""Getting started with EasyScrape.

Run: python 00_getting_started.py
"""
import easyscrape as es


def basic_fetch():
    """Fetch a page and check the response."""
    result = es.scrape("https://httpbin.org/html")

    print(f"Status: {result.status_code}")
    print(f"Content-Type: {result.headers.get('content-type', 'unknown')}")
    print(f"Size: {len(result.text):,} bytes")

    return result


def css_selectors(result):
    """Extract elements using CSS selectors."""
    heading = result.css("h1")
    print(f"Heading: {heading}")

    paragraphs = result.css_list("p")
    print(f"Paragraphs: {len(paragraphs)}")


def builtin_helpers(result):
    """Use convenience methods for common tasks."""
    print(f"Title: {result.title()}")

    main = result.main_text()[:100].replace("\n", " ")
    print(f"Main text: {main}...")

    links = result.safe_links()
    print(f"Safe links: {len(links)}")


def json_api():
    """Fetch and parse JSON."""
    result = es.scrape("https://httpbin.org/json")
    data = result.json()

    print(f"Keys: {list(data.keys())}")


def main():
    print("1. Basic Fetch")
    print("-" * 40)
    result = basic_fetch()

    print("\n2. CSS Selectors")
    print("-" * 40)
    css_selectors(result)

    print("\n3. Built-in Helpers")
    print("-" * 40)
    builtin_helpers(result)

    print("\n4. JSON API")
    print("-" * 40)
    json_api()


if __name__ == "__main__":
    main()
