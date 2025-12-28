#!/usr/bin/env python3
"""Cache support with ETag and conditional requests."""
import easyscrape as es


def main():
    url = "https://httpbin.org/etag/abc123"

    print("=== First Request ===")
    result = es.scrape(url)

    print(f"Status: {result.status_code}")
    print(f"ETag: {result.etag}")
    print(f"Last-Modified: {result.last_modified}")

    print("\n=== Conditional Request ===")
    new_result = es.scrape_if_changed(url, result)

    if new_result is None:
        print("Content unchanged (304)")
    else:
        print("Content changed")
        print(f"New ETag: {new_result.etag}")


if __name__ == "__main__":
    main()
