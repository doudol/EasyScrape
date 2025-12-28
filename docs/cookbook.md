# Cookbook

Real-world recipes for common scraping tasks.

## Scrape a List of URLs

```python
import easyscrape as es

urls = [
    "https://example.com/page1",
    "https://example.com/page2",
    "https://example.com/page3",
]

results = []
for url in urls:
    result = es.scrape(url)
    results.append({
        "url": url,
        "title": result.title(),
        "status": result.status_code,
    })
```

## Extract Table Data

```python
result = es.scrape("https://example.com/data-table")

# Get all table rows
rows = result.css_all("table tbody tr")

# Parse each row
data = []
for row in rows:
    cells = row.css_all("td")
    data.append({
        "name": cells[0] if cells else "",
        "value": cells[1] if len(cells) > 1 else "",
    })
```

## Handle Pagination

```python
import easyscrape as es

base_url = "https://example.com/products?page="
all_products = []

for page in range(1, 11):  # Pages 1-10
    result = es.scrape(f"{base_url}{page}")
    
    products = result.css_all("div.product h3")
    if not products:
        break  # No more pages
    
    all_products.extend(products)
    
print(f"Found {len(all_products)} products")
```

## Save Results to JSON

```python
import json
import easyscrape as es

result = es.scrape("https://api.example.com/data")
data = result.json()

with open("output.json", "w") as f:
    json.dump(data, f, indent=2)
```

## Save Results to CSV

```python
import csv
import easyscrape as es

result = es.scrape("https://example.com/products")
products = result.css_all("div.product")

with open("products.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Name", "Price"])
    
    for product in products:
        name = product.css("h3")
        price = product.css(".price")
        writer.writerow([name, price])
```

## Retry with Backoff

```python
import time
import easyscrape as es

def scrape_with_backoff(url: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            return es.scrape(url)
        except es.ScrapeError:
            if attempt < max_retries - 1:
                wait = 2 ** attempt  # 1, 2, 4 seconds
                time.sleep(wait)
            else:
                raise
```

## Check robots.txt

```python
from urllib.robotparser import RobotFileParser
import easyscrape as es

def can_scrape(url: str) -> bool:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    
    rp = RobotFileParser()
    rp.set_url(robots_url)
    rp.read()
    
    return rp.can_fetch("*", url)

# Check before scraping
url = "https://example.com/page"
if can_scrape(url):
    result = es.scrape(url)
```

## Session Persistence

```python
import easyscrape as es

# Create a session for multiple requests
with es.Session() as session:
    # Login
    session.scrape(
        "https://example.com/login",
        method="POST",
        data={"user": "me", "pass": "secret"}
    )
    
    # Subsequent requests maintain cookies
    dashboard = session.scrape("https://example.com/dashboard")
    profile = session.scrape("https://example.com/profile")
```

## Download Files

```python
import easyscrape as es

result = es.scrape("https://example.com/document.pdf")

with open("document.pdf", "wb") as f:
    f.write(result.content)
```

## Extract Metadata

```python
import easyscrape as es

result = es.scrape("https://example.com/article")

metadata = {
    "title": result.css("meta[property='og:title']", attr="content"),
    "description": result.css("meta[name='description']", attr="content"),
    "author": result.css("meta[name='author']", attr="content"),
    "published": result.css("time", attr="datetime"),
}
```
