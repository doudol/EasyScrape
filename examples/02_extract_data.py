"""Example 2: Structured Data Extraction

This example shows how to extract structured data from HTML.
"""
from easyscrape import scrape

# Scrape a page
result = scrape("https://httpbin.org/html")

# Extract single fields
title = result.css("h1")
print("Title:", title)

# Extract with mapping (multiple fields at once)
data = result.extract({
    "title": "h1",
    "paragraphs": "p",
})
print("Extracted:", data)

# Extract from JSON API
json_result = scrape("https://httpbin.org/json")
data = json_result.json()
print("JSON data:", data)
