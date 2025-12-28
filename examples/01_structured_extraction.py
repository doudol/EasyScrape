#!/usr/bin/env python3
"""Structured data extraction examples.

Run: python 01_structured_extraction.py
"""
import easyscrape as es


def single_item():
    """Extract structured data from a single page."""
    result = es.scrape("https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html")

    book = result.extract({
        "title": "h1",
        "price": ".price_color",
        "availability": ".availability::text",
        "description": "#product_description + p",
    })

    print("Single Book:")
    for key, value in book.items():
        print(f"  {key}: {value[:50]}..." if len(str(value)) > 50 else f"  {key}: {value}")


def multiple_items():
    """Extract multiple items from a listing page."""
    result = es.scrape("https://books.toscrape.com")

    books = result.extract_all(".product_pod", {
        "title": "h3 a::attr(title)",
        "price": ".price_color::text",
        "rating": ".star-rating::attr(class)",
    })

    print(f"\nFound {len(books)} books:")
    for book in books[:5]:
        print(f"  - {book['title'][:40]}: {book['price']}")


def nested_extraction():
    """Extract with CSS pseudo-elements."""
    result = es.scrape("https://quotes.toscrape.com")

    quotes = result.extract_all(".quote", {
        "text": ".text::text",
        "author": ".author::text",
        "tags": ".tag::text",  # Gets first tag
    })

    print(f"\nFound {len(quotes)} quotes:")
    for quote in quotes[:3]:
        text = quote['text'][:50] + "..." if len(quote['text']) > 50 else quote['text']
        print(f"  \"{text}\" - {quote['author']}")


def main():
    print("=" * 60)
    print("  Structured Extraction Examples")
    print("=" * 60)

    print("\n1. Single Item Extraction")
    print("-" * 40)
    single_item()

    print("\n2. Multiple Items Extraction")
    print("-" * 40)
    multiple_items()

    print("\n3. Nested Extraction")
    print("-" * 40)
    nested_extraction()


if __name__ == "__main__":
    main()
