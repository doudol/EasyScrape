# EasyScrape Tutorial

A comprehensive, step-by-step guide to mastering web scraping with EasyScrape.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Installation & Setup](#2-installation--setup)
3. [Your First Scraper](#3-your-first-scraper)
4. [CSS Selectors Deep Dive](#4-css-selectors-deep-dive)
5. [Structured Data Extraction](#5-structured-data-extraction)
6. [Configuration & Customisation](#6-configuration--customisation)
7. [Handling Pagination](#7-handling-pagination)
8. [JavaScript-Rendered Pages](#8-javascript-rendered-pages)
9. [Asynchronous Scraping](#9-asynchronous-scraping)
10. [Sessions & Authentication](#10-sessions--authentication)
11. [Error Handling](#11-error-handling)
12. [Data Export](#12-data-export)
13. [Best Practices](#13-best-practices)
14. [Real-World Project](#14-real-world-project)

---

## 1. Introduction

### What is Web Scraping?

Web scraping is the automated extraction of data from websites. Instead of manually copying information, you write code that:

1. **Fetches** web pages (like a browser)
2. **Parses** the HTML structure
3. **Extracts** the specific data you need
4. **Stores** it in a useful format (CSV, JSON, database)

### Why EasyScrape?

EasyScrape was designed with three principles:

1. **Simplicity**: Common tasks should be one-liners
2. **Safety**: Security features built-in, not bolted on
3. **Speed**: Async support for high-performance scraping

### Prerequisites

- Python 3.9 or higher
- Basic Python knowledge (variables, functions, loops)
- Understanding of HTML (tags, attributes, classes)

---

## 2. Installation & Setup

### Basic Installation

```bash
pip install easyscrape-py
```

### Verify Installation

```python
# test_install.py
import easyscrape
print(f"EasyScrape version: {easyscrape.__version__}")
print("Installation successful!")
```

Run it:

```bash
python test_install.py
# Output: EasyScrape version: 0.1.0
# Output: Installation successful!
```

### Optional Dependencies

```bash
# For JavaScript-rendered pages
pip install easyscrape[browser]

# For stealth mode (bypass bot detection)
pip install easyscrape[stealth]

# For Excel/Parquet export
pip install easyscrape[export]

# Everything
pip install easyscrape[all]
```

---

## 3. Your First Scraper

Let's scrape a real website step by step.

### Step 1: Import and Fetch

```python
from easyscrape import scrape

# Fetch a web page
result = scrape("https://example.com")
```

That's it! One line to fetch a page. The `result` object contains everything you need.

### Step 2: Check the Response

```python
# Did it work?
print(f"Status code: {result.status_code}")  # 200 = success
print(f"OK: {result.ok}")                     # True if status < 400
print(f"URL: {result.url}")                   # Final URL (after redirects)
```

### Step 3: View the Content

```python
# See the raw HTML
print(result.text[:500])  # First 500 characters

# Or just the title
print(f"Page title: {result.title()}")
```

### Step 4: Extract Data

```python
# Get specific elements
heading = result.css("h1")
print(f"Main heading: {heading}")

# Get a paragraph
paragraph = result.css("p")
print(f"First paragraph: {paragraph}")
```

### Complete Example

```python
"""
my_first_scraper.py - A complete beginner example
"""
from easyscrape import scrape

def main():
    # Fetch the page
    print("Fetching https://example.com...")
    result = scrape("https://example.com")
    
    # Check if successful
    if not result.ok:
        print(f"Error: {result.status_code}")
        return
    
    # Extract data
    title = result.title()
    heading = result.css("h1")
    paragraph = result.css("p")
    links = result.links()
    
    # Display results
    print(f"\nPage Title: {title}")
    print(f"Main Heading: {heading}")
    print(f"First Paragraph: {paragraph[:100]}...")
    print(f"Number of Links: {len(links)}")

if __name__ == "__main__":
    main()
```

---

## 4. CSS Selectors Deep Dive

CSS selectors are patterns that identify HTML elements. Master these to extract any data.

### Basic Selectors

| Selector | Meaning | Example |
|----------|---------|---------|
| `tag` | Element by tag name | `h1`, `p`, `div` |
| `.class` | Element by class | `.price`, `.title` |
| `#id` | Element by ID | `#header`, `#main` |
| `[attr]` | Element with attribute | `[href]`, `[src]` |
| `[attr=val]` | Attribute equals value | `[type="text"]` |

### Combinators

| Selector | Meaning | Example |
|----------|---------|---------|
| `A B` | B inside A (any level) | `div p` |
| `A > B` | B directly inside A | `ul > li` |
| `A + B` | B immediately after A | `h1 + p` |
| `A, B` | A or B | `h1, h2, h3` |

### Pseudo-Selectors (EasyScrape Extensions)

| Selector | Returns | Example |
|----------|---------|---------|
| `::text` | Text content | `p::text` |
| `::attr(name)` | Attribute value | `a::attr(href)` |
| `::html` | Inner HTML | `div::html` |

### Practical Examples

```python
from easyscrape import scrape

result = scrape("https://books.toscrape.com")

# Get all book titles (attribute value)
titles = result.css_list("h3 a::attr(title)")

# Get all prices (text content)
prices = result.css_list(".price_color::text")

# Get star ratings (class name contains rating)
ratings = result.css_list(".star-rating::attr(class)")

# Get book URLs (combine with base URL)
urls = result.css_list("h3 a::attr(href)")
full_urls = [result.urljoin(url) for url in urls]

# Print first 3 books
for i in range(3):
    print(f"{titles[i]}: {prices[i]}")
```

### Finding the Right Selector

1. **Open browser DevTools** (F12 or right-click > Inspect)
2. **Select the element** (Ctrl+Shift+C, then click)
3. **Look at the HTML** - note the tag, classes, and structure
4. **Build your selector** - start simple, add specificity if needed

**Pro tip**: In Chrome DevTools, right-click an element > Copy > Copy selector

---

## 5. Structured Data Extraction

Instead of extracting one field at a time, extract complete records.

### Single Item Extraction

```python
from easyscrape import scrape

result = scrape("https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html")

# Extract multiple fields at once
book = result.extract({
    "title": "h1",
    "price": ".price_color",
    "availability": ".availability::text",
    "description": "#product_description + p",
    "upc": "tr:nth-child(1) td",
})

print(book)
# {
#     "title": "A Light in the Attic",
#     "price": "GBP 51.77",
#     "availability": "In stock (22 available)",
#     "description": "It's hard to imagine a world without...",
#     "upc": "a897fe39b1053632"
# }
```

### Multiple Items Extraction

```python
from easyscrape import scrape

result = scrape("https://books.toscrape.com")

# Extract all books on the page
books = result.extract_all(".product_pod", {
    "title": "h3 a::attr(title)",
    "price": ".price_color::text",
    "rating": ".star-rating::attr(class)",
    "url": "h3 a::attr(href)",
})

print(f"Found {len(books)} books")
for book in books[:3]:
    print(f"  - {book['title']}: {book['price']}")
```

### Nested Extraction

```python
# For complex structures, use nested schemas
result = scrape("https://example.com/products")

products = result.extract_all(".product", {
    "name": ".name",
    "price": ".price",
    "specs": {
        "_selector": ".specifications",  # Container
        "weight": ".weight",
        "dimensions": ".dimensions",
    },
    "reviews": {
        "_selector": ".reviews .review",
        "_multiple": True,
        "author": ".author",
        "rating": ".rating",
    }
})
```

---

## 6. Configuration & Customisation

### Creating a Configuration

```python
from easyscrape import scrape, Config

config = Config(
    timeout=60.0,       # Wait longer for slow sites
    max_retries=5,      # Retry more times
    rate_limit=1.0,     # Be polite: 1 request/second
)

result = scrape("https://example.com", config=config)
```

### Common Configuration Patterns

#### Development Mode

```python
dev_config = Config(
    cache_enabled=True,   # Don't re-download pages
    cache_ttl=86400,      # Cache for 24 hours
    timeout=60.0,         # Patient timeouts
)
```

#### Production Mode

```python
prod_config = Config(
    max_retries=5,
    retry_delay=2.0,
    backoff_factor=2.0,   # 2s, 4s, 8s, 16s, 32s
    rate_limit=2.0,       # 2 requests/second
    rotate_ua=True,       # Vary User-Agent
    respect_robots=True,  # Honour robots.txt
)
```

#### Stealth Mode

```python
stealth_config = Config(
    use_stealth=True,     # TLS fingerprint bypass
    rotate_ua=True,       # Random User-Agent
    headers={
        "Accept-Language": "en-GB,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
    },
)
```

### Custom Headers

```python
config = Config(
    headers={
        "Authorization": "Bearer your-token",
        "X-Custom-Header": "value",
        "Referer": "https://google.com",
    }
)
```

### Using Proxies

```python
config = Config(
    proxies=[
        "http://user:pass@proxy1.com:8080",
        "http://user:pass@proxy2.com:8080",
    ],
    proxy_mode="round-robin",  # or "random"
)
```

---

## 7. Handling Pagination

Most websites split content across multiple pages. Here's how to handle them.

### Method 1: Follow "Next" Links

```python
from easyscrape import paginate

all_items = []

for page in paginate(
    "https://books.toscrape.com",
    next_selector=".next a",
    max_pages=10,
):
    items = page.css_list("h3 a::attr(title)")
    all_items.extend(items)
    print(f"Page {page.url}: {len(items)} items")

print(f"Total: {len(all_items)} items")
```

### Method 2: Parameter-Based Pagination

```python
from easyscrape import paginate_param

for page in paginate_param(
    "https://example.com/search",
    param="page",
    start=1,
    end=10,
):
    results = page.css_list(".result")
    print(f"Page {page}: {len(results)} results")
```

### Method 3: Offset-Based Pagination

```python
from easyscrape import paginate_offset

for page in paginate_offset(
    "https://example.com/api/items",
    offset_param="offset",
    limit_param="limit",
    limit=20,
    max_offset=200,
):
    items = page.json()["items"]
    print(f"Offset {page}: {len(items)} items")
```

### Method 4: Manual Control

```python
from easyscrape import scrape

page_num = 1
all_books = []

while True:
    url = f"https://books.toscrape.com/catalogue/page-{page_num}.html"
    result = scrape(url)
    
    if not result.ok:
        break  # No more pages
    
    books = result.css_list("h3 a::attr(title)")
    if not books:
        break  # Empty page
    
    all_books.extend(books)
    print(f"Page {page_num}: {len(books)} books")
    
    page_num += 1
    if page_num > 50:  # Safety limit
        break

print(f"Total: {len(all_books)} books")
```

---

## 8. JavaScript-Rendered Pages

Many modern websites use JavaScript to load content. EasyScrape handles this with Playwright.

### Installation

```bash
pip install easyscrape[browser]
playwright install chromium
```

### Basic Usage

```python
from easyscrape import scrape, Config

config = Config(javascript=True)
result = scrape("https://quotes.toscrape.com/js/", config=config)

quotes = result.css_list(".quote .text")
print(f"Found {len(quotes)} quotes")
```

### Wait for Content

```python
config = Config(
    javascript=True,
    js_wait=3.0,              # Wait 3 seconds after load
    js_wait_for=".quote",     # Or wait for this selector
)
```

### Advanced Browser Control

```python
from easyscrape import Browser

async def scrape_dynamic_page():
    async with Browser(headless=True) as browser:
        page = await browser.goto("https://example.com")
        
        # Wait for specific element
        await page.wait_for(".content-loaded")
        
        # Click a button
        await page.click("#load-more")
        
        # Wait for new content
        await page.wait(1.0)
        
        # Extract data
        items = await page.css_list(".item")
        return items
```

---

## 9. Asynchronous Scraping

For scraping many pages quickly, use async.

### Why Async?

```
Synchronous (100 pages, 1s each):  100 seconds
Asynchronous (100 pages, 10 concurrent): ~10 seconds
```

### Basic Async

```python
import asyncio
from easyscrape import async_scrape

async def main():
    result = await async_scrape("https://example.com")
    print(result.title())

asyncio.run(main())
```

### Scraping Many Pages

```python
import asyncio
from easyscrape import async_scrape_many, Config

async def scrape_all_books():
    urls = [
        f"https://books.toscrape.com/catalogue/page-{i}.html"
        for i in range(1, 51)
    ]
    
    config = Config(
        concurrent_limit=10,  # Max 10 at a time
        rate_limit=5.0,       # 5 requests/second
    )
    
    results = await async_scrape_many(urls, config=config)
    
    all_books = []
    for result in results:
        if result.ok:
            books = result.css_list("h3 a::attr(title)")
            all_books.extend(books)
    
    return all_books

books = asyncio.run(scrape_all_books())
print(f"Scraped {len(books)} books")
```

### With Progress Tracking

```python
import asyncio
from easyscrape import async_scrape, Config

async def scrape_with_progress(urls):
    config = Config(rate_limit=5.0)
    results = []
    
    for i, url in enumerate(urls, 1):
        result = await async_scrape(url, config=config)
        results.append(result)
        print(f"Progress: {i}/{len(urls)} ({100*i/len(urls):.1f}%)")
    
    return results
```

---

## 10. Sessions & Authentication

### Maintaining Cookies

```python
from easyscrape import Session

with Session() as session:
    # First request sets cookies
    session.get("https://example.com")
    
    # Subsequent requests include those cookies
    result = session.get("https://example.com/dashboard")
```

### Login Flow

```python
from easyscrape import Session

with Session() as session:
    # Step 1: Get the login page (may set CSRF token)
    login_page = session.get("https://example.com/login")
    
    # Step 2: Extract CSRF token if needed
    csrf = login_page.css("input[name='csrf']::attr(value)")
    
    # Step 3: Submit login form
    response = session.post(
        "https://example.com/login",
        data={
            "username": "myuser",
            "password": "mypass",
            "csrf": csrf,
        }
    )
    
    # Step 4: Check if login worked
    if "Welcome" in response.text:
        print("Login successful!")
        
        # Step 5: Access protected content
        profile = session.get("https://example.com/profile")
        print(profile.css(".user-name"))
```

---

## 11. Error Handling

### The Exception Hierarchy

```
EasyScrapeError (catch all)
+-- NetworkError (connection issues)
|   +-- RequestTimeout
+-- HTTPError (4xx, 5xx responses)
+-- InvalidURLError
+-- RateLimitHit (429 Too Many Requests)
+-- RetryExhausted
+-- ExtractionError
```

### Basic Error Handling

```python
from easyscrape import scrape
from easyscrape.exceptions import EasyScrapeError

try:
    result = scrape("https://example.com")
except EasyScrapeError as e:
    print(f"Scraping failed: {e}")
```

### Specific Error Handling

```python
from easyscrape import scrape
from easyscrape.exceptions import (
    NetworkError,
    HTTPError,
    RateLimitHit,
    RequestTimeout,
)

def safe_scrape(url):
    try:
        return scrape(url)
    except RateLimitHit:
        print("Rate limited! Waiting...")
        time.sleep(60)
        return scrape(url)  # Retry
    except RequestTimeout:
        print("Timeout - skipping")
        return None
    except HTTPError as e:
        print(f"HTTP {e.status_code}")
        return None
    except NetworkError as e:
        print(f"Network error: {e}")
        return None
```

---

## 12. Data Export

### Export to CSV

```python
from easyscrape import scrape, to_csv

result = scrape("https://books.toscrape.com")
books = result.extract_all(".product_pod", {
    "title": "h3 a::attr(title)",
    "price": ".price_color::text",
})

to_csv(books, "books.csv")
```

### Export to JSON

```python
from easyscrape import to_json

to_json(books, "books.json", indent=2)
```

### Export to Excel

```python
from easyscrape import to_excel

to_excel(books, "books.xlsx")
```

### Export to DataFrame

```python
from easyscrape import to_dataframe

df = to_dataframe(books)
print(df.head())
print(df.describe())
```

---

## 13. Best Practices

### 1. Rate Limiting

```python
# Always limit your request rate
config = Config(rate_limit=1.0)  # 1 request/second
```

### 2. Respect robots.txt

```python
config = Config(respect_robots=True)
```

### 3. Identify Yourself

```python
config = Config(
    headers={"User-Agent": "MyBot/1.0 (contact@example.com)"}
)
```

### 4. Handle Errors

```python
# Never let one error crash your whole scrape
for url in urls:
    try:
        result = scrape(url)
        process(result)
    except EasyScrapeError:
        continue
```

### 5. Cache During Development

```python
config = Config(cache_enabled=True, cache_ttl=86400)
```

### 6. Use Async for Large Jobs

```python
# 100 pages: 10x faster with async
await async_scrape_many(urls, config=Config(concurrent_limit=10))
```

---

## 14. Real-World Project

Let's build a complete book scraper that:

1. Scrapes all 50 pages of books.toscrape.com
2. Extracts title, price, rating, and availability
3. Handles errors gracefully
4. Exports to CSV and JSON

```python
"""
complete_book_scraper.py

A production-ready scraper for books.toscrape.com
"""

import asyncio
from easyscrape import (
    async_scrape_many,
    Config,
    to_csv,
    to_json,
)
from easyscrape.exceptions import EasyScrapeError


def create_urls(num_pages: int) -> list[str]:
    """Generate URLs for all pages."""
    return [
        f"https://books.toscrape.com/catalogue/page-{i}.html"
        for i in range(1, num_pages + 1)
    ]


def parse_rating(class_name: str) -> int:
    """Convert 'star-rating Three' to 3."""
    ratings = {
        "One": 1, "Two": 2, "Three": 3,
        "Four": 4, "Five": 5
    }
    for word, num in ratings.items():
        if word in class_name:
            return num
    return 0


def parse_price(price_str: str) -> float:
    """Convert 'GBP 51.77' to 51.77."""
    return float(price_str.replace("GBP ", "").replace("$", ""))


async def scrape_books(num_pages: int = 50) -> list[dict]:
    """Scrape all books from the website."""
    
    # Configuration
    config = Config(
        timeout=30.0,
        max_retries=3,
        rate_limit=5.0,
        concurrent_limit=10,
        cache_enabled=True,
        rotate_ua=True,
    )
    
    # Generate URLs
    urls = create_urls(num_pages)
    print(f"Scraping {len(urls)} pages...")
    
    # Fetch all pages
    try:
        results = await async_scrape_many(urls, config=config)
    except EasyScrapeError as e:
        print(f"Fatal error: {e}")
        return []
    
    # Parse results
    all_books = []
    errors = []
    
    for i, result in enumerate(results, 1):
        if not result.ok:
            errors.append({"page": i, "status": result.status_code})
            continue
        
        books = result.extract_all(".product_pod", {
            "title": "h3 a::attr(title)",
            "price": ".price_color::text",
            "rating": ".star-rating::attr(class)",
            "availability": ".availability::text",
            "url": "h3 a::attr(href)",
        })
        
        # Clean and transform data
        for book in books:
            book["price_numeric"] = parse_price(book["price"])
            book["rating_numeric"] = parse_rating(book["rating"])
            book["availability"] = book["availability"].strip()
            book["url"] = f"https://books.toscrape.com/catalogue/{book['url']}"
        
        all_books.extend(books)
        
        # Progress
        if i % 10 == 0:
            print(f"Processed {i}/{len(urls)} pages...")
    
    # Report
    print(f"\nComplete!")
    print(f"  Books scraped: {len(all_books)}")
    print(f"  Errors: {len(errors)}")
    
    if errors:
        print(f"  Failed pages: {[e['page'] for e in errors]}")
    
    return all_books


def export_data(books: list[dict]) -> None:
    """Export books to multiple formats."""
    
    # CSV
    to_csv(books, "output/books.csv")
    print("Exported to output/books.csv")
    
    # JSON
    to_json(books, "output/books.json", indent=2)
    print("Exported to output/books.json")
    
    # Summary
    if books:
        prices = [b["price_numeric"] for b in books]
        print(f"\nSummary:")
        print(f"  Total books: {len(books)}")
        print(f"  Price range: GBP {min(prices):.2f} - {max(prices):.2f}")
        print(f"  Average price: GBP {sum(prices)/len(prices):.2f}")


async def main():
    """Main entry point."""
    print("=" * 60)
    print("Book Scraper - books.toscrape.com")
    print("=" * 60)
    
    books = await scrape_books(num_pages=50)
    
    if books:
        export_data(books)
    else:
        print("No books scraped!")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Conclusion

You've learned:

- Basic scraping with `scrape()`
- CSS selectors for data extraction
- Structured data extraction with schemas
- Configuration and customisation
- Pagination handling
- JavaScript rendering
- Async scraping for speed
- Sessions and authentication
- Error handling
- Data export

### Next Steps

1. **Practice**: Scrape a website you're interested in
2. **Read**: Check the API Reference for all available methods
3. **Explore**: Try the Cookbook recipes for specific tasks
4. **Contribute**: Found a bug? Want a feature? Open an issue!

Happy scraping!
