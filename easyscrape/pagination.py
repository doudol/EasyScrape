"""
Pagination Detection and Handling Strategies
=============================================

This module provides strategies for navigating paginated content during
web scraping. Pagination is how websites split content across multiple
pages, and handling it correctly is essential for complete data extraction.

Pagination Patterns
-------------------
Websites use various pagination patterns:

1. **Link-based**: "Next" links with rel="next" or class="next"
2. **Parameter-based**: ?page=1, ?page=2, ?page=3
3. **Offset-based**: ?offset=0, ?offset=20, ?offset=40
4. **Cursor-based**: ?cursor=abc123 (not covered here - requires API knowledge)
5. **Infinite scroll**: JavaScript loads more content (use browser module)

Strategy Selection Guide
------------------------
Choose your strategy based on the website's pagination pattern:

- `paginate()`: Auto-detects "Next" links using heuristics
- `paginate_param()`: For ?page=N style pagination
- `paginate_offset()`: For ?offset=N style pagination
- `crawl()`: Follows all links (spider/crawler behaviour)

Generator Pattern
-----------------
All pagination functions are generators that yield ScrapeResult objects.
This enables:

- **Memory efficiency**: Only one page in memory at a time
- **Early termination**: Stop when you have enough data
- **Progress tracking**: Process results as they arrive

Example Usage
-------------
    from easyscrape.pagination import paginate, paginate_param

    # Auto-detect pagination links
    for page in paginate("https://blog.example.com/articles"):
        titles = page.css_all("h2.title")
        print(titles)

    # Explicit page parameter
    for page in paginate_param("https://shop.example.com/products", param="p"):
        products = page.extract_all(".product", {"name": "h3", "price": ".price"})
        save_products(products)

Stop Conditions
---------------
All pagination functions support a `stop_if` callback to terminate early:

    def has_old_articles(result):
        date = result.css(".date")
        return date and parse_date(date) < cutoff_date

    for page in paginate(url, stop_if=has_old_articles):
        process(page)
"""
from __future__ import annotations

import re
from collections import deque
from collections.abc import Generator
from typing import Callable, Final
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

from .config import Config
from .core import ScrapeResult, scrape
from .session import Session

__all__: Final[tuple[str, ...]] = (
    "paginate",
    "paginate_param",
    "paginate_offset",
    "crawl",
    # Aliases
    "Paginator",
    "PaginateByParam",
    "PaginateByOffset",
)


def _find_next_link(
    result: ScrapeResult,
    patterns: list[str] | None = None,
) -> str | None:
    """
    Detect "Next" pagination link using heuristic pattern matching.

    This function scans all anchor tags in the page looking for common
    indicators of "Next page" links. It uses regex patterns to match
    against the full anchor tag HTML.

    Detection Heuristics
    --------------------
    The default patterns detect:
    - rel="next" attribute (SEO standard)
    - class names containing "next"
    - aria-label containing "next" (accessibility)
    - Link text: "next", "next page", ">", ">>", ">"

    Parameters
    ----------
    result : ScrapeResult
        The scrape result to search for pagination links.
    patterns : Optional[List[str]]
        Custom regex patterns to use instead of defaults.
        Patterns are matched case-insensitively against anchor HTML.

    Returns
    -------
    Optional[str]
        The absolute URL of the next page, or None if not found.

    Notes
    -----
    This heuristic approach works for many sites but isn't perfect.
    For reliable pagination, use `paginate_param()` with the known
    parameter name, or provide a `next_selector` to `paginate()`.
    """
    # Ensure HTML is loaded
    if not result.text:
        return None

    # Try common CSS selectors first (faster and more reliable)
    common_selectors = [
        "a[rel='next']",
        "a[rel=next]",
        "li.next a",
        "a.next",
        ".pagination .next a",
        ".pager .next a",
        "a.pagination-next",
    ]
    
    for selector in common_selectors:
        try:
            links = result.extractor.css_list(selector, attr="href")
            if links and links[0]:
                href = links[0]
                if not href.startswith(("http://", "https://")):
                    href = urljoin(result.final_url, href)
                return href
        except Exception:
            continue

    # Fallback to regex pattern matching on anchor HTML
    default_patterns = [
        r'rel=["\']?next["\']?',
        r'class=["\'][^"\']*next[^"\']*["\']',
        r'aria-label=["\'][^"\']*next[^"\']*["\']',
        r'>next<',
        r'>next page<',
        r'>&gt;<',
        r'>»<',
        r'>›<',
        r'>→<',
    ]

    search_patterns = patterns or default_patterns

    # Use selectolax parser for anchor extraction (10x faster than BS4)
    for anchor in result.extractor.parser.css("a[href]"):
        # Get the HTML representation of anchor for pattern matching
        anchor_html = anchor.html or ""
        anchor_str = anchor_html.lower()
        for pattern in search_patterns:
            if re.search(pattern, anchor_str, re.IGNORECASE):
                href_attr = anchor.attributes.get("href")
                if href_attr:
                    href: str = href_attr
                    # Convert relative URLs to absolute
                    if not href.startswith(("http://", "https://")):
                        href = urljoin(result.final_url, href)
                    return href

    return None


def _increment_page_param(url: str, param: str = "page", increment: int = 1) -> str:
    """
    Increment a numeric page parameter in a URL.

    This helper function parses the URL, finds the specified parameter,
    increments its value, and reconstructs the URL.

    Parameters
    ----------
    url : str
        The URL to modify.
    param : str
        The query parameter name to increment.
    increment : int
        Amount to add to the current value.

    Returns
    -------
    str
        The URL with the incremented parameter.

    Example
    -------
        >>> _increment_page_param("https://example.com?page=3", "page")
        "https://example.com?page=4"
    """
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)

    try:
        current = int(params.get(param, ["1"])[0])
    except ValueError:
        current = 1

    params[param] = [str(current + increment)]
    new_query = urlencode(params, doseq=True)

    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{new_query}"


def paginate(
    start_url: str,
    config: Config | None = None,
    max_pages: int = 100,
    next_selector: str | None = None,
    next_patterns: list[str] | None = None,
    stop_if: Callable[[ScrapeResult], bool] | None = None,
) -> Generator[ScrapeResult, None, None]:
    """
    Paginate through a website by following "Next" links.

    This function automatically detects and follows pagination links.
    It's the most flexible pagination strategy, working with various
    pagination patterns without requiring knowledge of URL structure.

    Detection Strategy
    ------------------
    1. If `next_selector` is provided, use it to find the next link
    2. Otherwise, use heuristic pattern matching to find "Next" links

    Duplicate Prevention
    --------------------
    The function maintains a set of visited URLs (normalised to lowercase,
    trailing slashes removed) to prevent infinite loops on sites with
    circular pagination links.

    Parameters
    ----------
    start_url : str
        The first page URL to scrape.
    config : Optional[Config]
        Scraping configuration. If None, uses defaults.
    max_pages : int, default=100
        Maximum number of pages to scrape (safety limit).
    next_selector : Optional[str]
        CSS selector for the "Next" link. If provided, extracts the
        href attribute from the matching element.
    next_patterns : Optional[List[str]]
        Custom regex patterns for detecting "Next" links.
    stop_if : Optional[Callable[[ScrapeResult], bool]]
        Callback that returns True to stop pagination. Called after
        each page is scraped.

    Yields
    ------
    ScrapeResult
        The scrape result for each page.

    Example
    -------
        # Auto-detect pagination
        for page in paginate("https://news.example.com"):
            articles = page.extract_all(".article", {"title": "h2"})
            save(articles)

        # With explicit selector
        for page in paginate(
            "https://blog.example.com",
            next_selector="a.pagination-next",
            max_pages=50
        ):
            process(page)

        # With stop condition
        def found_target(result):
            return "target-keyword" in result.text

        for page in paginate(url, stop_if=found_target):
            # Stops when target is found
            pass
    """
    cfg = config or Config()
    visited: set[str] = set()
    current_url = start_url
    page_count = 0

    while current_url and page_count < max_pages:
        # Normalise URL for duplicate detection
        normalised = current_url.rstrip("/").lower()
        if normalised in visited:
            break
        visited.add(normalised)

        try:
            result = scrape(current_url, cfg)
        except Exception:
            break

        yield result
        page_count += 1

        # Check stop condition
        if stop_if and stop_if(result):
            break

        # Find next page URL
        if next_selector:
            next_links = result.extractor.css_list(next_selector, attr="href")
            if next_links:
                next_href = next_links[0]
                if not next_href.startswith(("http://", "https://")):
                    next_href = urljoin(result.final_url, next_href)
                current_url = next_href
            else:
                break
        else:
            next_url = _find_next_link(result, next_patterns)
            if next_url:
                current_url = next_url
            else:
                break


def paginate_param(
    base_url: str,
    param: str = "page",
    start: int = 1,
    end: int = 100,
    config: Config | None = None,
    stop_if: Callable[[ScrapeResult], bool] | None = None,
) -> Generator[ScrapeResult, None, None]:
    """
    Paginate using a numeric page parameter.

    This strategy is for websites that use URL parameters like:
    - https://example.com/products?page=1
    - https://example.com/search?p=2
    - https://example.com/list?pg=3

    The function iterates through page numbers from `start` to `end`,
    constructing URLs by setting the specified parameter.

    Parameters
    ----------
    base_url : str
        The base URL (may or may not include existing query parameters).
    param : str, default="page"
        The query parameter name for the page number.
    start : int, default=1
        The first page number.
    end : int, default=100
        The last page number (inclusive).
    config : Optional[Config]
        Scraping configuration.
    stop_if : Optional[Callable[[ScrapeResult], bool]]
        Callback to stop pagination early.

    Yields
    ------
    ScrapeResult
        The scrape result for each page.

    Example
    -------
        # Standard ?page=N pagination
        for page in paginate_param("https://shop.example.com/products"):
            items = page.extract_all(".item", {...})

        # Different parameter name, starting from page 0
        for page in paginate_param(
            "https://api.example.com/data",
            param="p",
            start=0,
            end=50
        ):
            process(page.json())
    """
    cfg = config or Config()

    for page_num in range(start, end + 1):
        # Construct URL with page parameter
        parsed = urlparse(base_url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        params[param] = [str(page_num)]
        new_query = urlencode(params, doseq=True)
        url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{new_query}"

        try:
            result = scrape(url, cfg)
        except Exception:
            break

        yield result

        if stop_if and stop_if(result):
            break


def paginate_offset(
    base_url: str,
    param: str = "offset",
    step: int = 20,
    start: int = 0,
    max_offset: int = 10000,
    config: Config | None = None,
    stop_if: Callable[[ScrapeResult], bool] | None = None,
) -> Generator[ScrapeResult, None, None]:
    """
    Paginate using an offset parameter.

    This strategy is for APIs and websites that use offset-based pagination:
    - https://example.com/api/items?offset=0 (items 1-20)
    - https://example.com/api/items?offset=20 (items 21-40)
    - https://example.com/api/items?offset=40 (items 41-60)

    Common with REST APIs where the offset represents the starting index
    and a separate `limit` parameter controls page size.

    Parameters
    ----------
    base_url : str
        The base URL.
    param : str, default="offset"
        The query parameter name for the offset.
    step : int, default=20
        The increment between pages (usually matches the page size).
    start : int, default=0
        The starting offset (usually 0).
    max_offset : int, default=10000
        Maximum offset to prevent runaway pagination.
    config : Optional[Config]
        Scraping configuration.
    stop_if : Optional[Callable[[ScrapeResult], bool]]
        Callback to stop pagination early. Commonly used to detect
        empty result pages.

    Yields
    ------
    ScrapeResult
        The scrape result for each page.

    Example
    -------
        def is_empty(result):
            data = result.json()
            return len(data.get("items", [])) == 0

        for page in paginate_offset(
            "https://api.example.com/items",
            param="start",
            step=50,
            stop_if=is_empty
        ):
            items = page.json()["items"]
            save_items(items)
    """
    cfg = config or Config()

    offset = start
    while offset <= max_offset:
        # Construct URL with offset parameter
        parsed = urlparse(base_url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        params[param] = [str(offset)]
        new_query = urlencode(params, doseq=True)
        url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{new_query}"

        try:
            result = scrape(url, cfg)
        except Exception:
            break

        yield result

        if stop_if and stop_if(result):
            break

        offset += step


def crawl(
    start_url: str,
    config: Config | None = None,
    max_pages: int = 100,
    same_domain: bool = True,
    link_pattern: str | None = None,
    stop_if: Callable[[ScrapeResult], bool] | None = None,
) -> Generator[ScrapeResult, None, None]:
    """
    Crawl a website by following all links (spider/web crawler).

    Unlike pagination functions that follow a linear sequence, crawl()
    explores the website by following links discovered on each page.
    This is useful for:

    - Sitemap generation
    - Full site archival
    - Discovery of all pages matching a pattern

    Algorithm: Breadth-First Search (BFS)
    -------------------------------------
    Uses a queue to explore pages level by level:
    1. Start with the seed URL in the queue
    2. Scrape the first URL in the queue
    3. Extract all links from the page
    4. Add unvisited links to the queue
    5. Repeat until queue is empty or max_pages reached

    BFS ensures pages closer to the start are crawled first, which is
    usually desirable (home page -> category pages -> detail pages).

    Parameters
    ----------
    start_url : str
        The seed URL to start crawling from.
    config : Optional[Config]
        Scraping configuration.
    max_pages : int, default=100
        Maximum pages to crawl (safety limit).
    same_domain : bool, default=True
        If True, only follow links on the same domain as start_url.
        Prevents crawling the entire internet.
    link_pattern : Optional[str]
        Regex pattern to filter links. Only matching links are followed.
        Example: r"/products/\\d+" to only crawl product pages.
    stop_if : Optional[Callable[[ScrapeResult], bool]]
        Callback to stop crawling early.

    Yields
    ------
    ScrapeResult
        The scrape result for each crawled page.

    Example
    -------
        # Crawl all product pages
        for page in crawl(
            "https://shop.example.com",
            link_pattern=r"/product/",
            max_pages=500
        ):
            product = page.extract({
                "name": "h1.product-name",
                "price": ".price-value",
            })
            save_product(product)

        # Full site crawl (be careful with large sites!)
        for page in crawl("https://small-site.com", max_pages=1000):
            archive(page.url, page.text)

    Notes
    -----
    Crawling can be aggressive on servers. Consider:
    - Using rate limiting via Config or ThrottleMiddleware
    - Respecting robots.txt (check with robots module)
    - Setting reasonable max_pages limits
    """
    cfg = config or Config()
    start_domain = urlparse(start_url).netloc
    visited: set[str] = set()
    queue: deque[str] = deque([start_url])
    page_count = 0

    while queue and page_count < max_pages:
        url = queue.popleft()

        # Normalise for duplicate detection
        normalised = url.rstrip("/").lower()
        if normalised in visited:
            continue
        visited.add(normalised)

        try:
            result = scrape(url, cfg)
        except Exception:
            continue

        yield result
        page_count += 1

        if stop_if and stop_if(result):
            break

        # Extract and filter new links
        new_links = result.links(link_pattern, absolute=True)
        for link in new_links:
            link_normalised = link.rstrip("/").lower()
            if link_normalised in visited:
                continue

            # Domain filter
            if same_domain and urlparse(link).netloc != start_domain:
                continue

            queue.append(link)


# These aliases improve API discoverability and match common naming expectations

Paginator = paginate  # Class-style alias for paginate function
PaginateByParam = paginate_param  # Verbose alias
PaginateByOffset = paginate_offset  # Verbose alias
