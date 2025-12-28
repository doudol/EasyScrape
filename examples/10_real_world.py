#!/usr/bin/env python3
"""Real-world scraping example."""
import easyscrape as es


def scrape_article(url: str) -> dict:
    """Extract article information."""
    result = es.scrape(url)

    return {
        "url": url,
        "title": result.title(),
        "content": result.main_text()[:500],
        "links": len(result.safe_links()),
        "images": len(result.safe_images()),
        "meta": result.meta(),
    }


def main():
    url = "https://httpbin.org/html"

    print("=== Scraping Article ===")
    article = scrape_article(url)

    print(f"Title: {article['title']}")
    print(f"Content: {article['content'][:200]}...")
    print(f"Links: {article['links']}")
    print(f"Images: {article['images']}")

    if article["meta"]:
        print(f"Meta tags: {list(article['meta'].keys())[:5]}")


if __name__ == "__main__":
    main()
