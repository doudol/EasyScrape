"""Tests for data extraction."""
import pytest

from easyscrape.extractors import (
    Extractor,
    css,
    css_list,
    find_links,
    find_images,
    find_tables,
    SelectorBuilder,
)
from easyscrape.exceptions import SelectorError


class TestExtractor:
    """Tests for Extractor class."""

    def test_css_basic(self):
        """Test basic CSS extraction."""
        html = "<html><body><h1>Title</h1></body></html>"
        ext = Extractor(html)

        assert ext.css("h1") == "Title"

    def test_css_with_class(self):
        """Test CSS extraction with class selector."""
        html = '<html><p class="intro">Hello</p><p>World</p></html>'
        ext = Extractor(html)

        assert ext.css(".intro") == "Hello"
        assert ext.css("p") == "Hello"  # First match

    def test_css_with_id(self):
        """Test CSS extraction with ID selector."""
        html = '<html><div id="main">Content</div></html>'
        ext = Extractor(html)

        assert ext.css("#main") == "Content"

    def test_css_pseudo_text(self):
        """Test ::text pseudo-element."""
        html = "<html><p>  Spaced  Text  </p></html>"
        ext = Extractor(html)

        result = ext.css("p::text")
        assert "Spaced" in result

    def test_css_pseudo_attr(self):
        """Test ::attr() pseudo-element."""
        html = '<html><a href="/page" title="Link">Click</a></html>'
        ext = Extractor(html)

        assert ext.css("a::attr(href)") == "/page"
        assert ext.css("a::attr(title)") == "Link"

    def test_css_list(self):
        """Test CSS list extraction."""
        html = "<html><ul><li>A</li><li>B</li><li>C</li></ul></html>"
        ext = Extractor(html)

        items = ext.css_list("li")
        assert len(items) == 3
        assert items == ["A", "B", "C"]

    def test_css_list_attr(self):
        """Test CSS list extraction with attribute."""
        html = '<html><a href="/a">A</a><a href="/b">B</a></html>'
        ext = Extractor(html)

        hrefs = ext.css_list("a::attr(href)")
        assert hrefs == ["/a", "/b"]

    def test_css_default(self):
        """Test CSS extraction with default value."""
        html = "<html><p>Text</p></html>"
        ext = Extractor(html)

        # When selector not found, should return default
        result = ext.css(".missing", "default")
        assert result == "default"
        
        # Without default, returns empty string
        assert ext.css(".missing") == ""

    def test_extract_schema(self):
        """Test schema-based extraction."""
        html = """
        <html>
            <h1>Product Name</h1>
            <span class="price">$99.99</span>
            <p class="desc">Description here</p>
        </html>
        """
        ext = Extractor(html)

        data = ext.extract({
            "name": "h1",
            "price": ".price",
            "description": ".desc",
        })

        assert data["name"] == "Product Name"
        assert data["price"] == "$99.99"
        assert data["description"] == "Description here"

    def test_extract_all(self):
        """Test multiple item extraction."""
        html = """
        <html>
            <div class="product">
                <h3>Product 1</h3>
                <span class="price">$10</span>
            </div>
            <div class="product">
                <h3>Product 2</h3>
                <span class="price">$20</span>
            </div>
        </html>
        """
        ext = Extractor(html)

        products = ext.extract_all(".product", {
            "name": "h3",
            "price": ".price",
        })

        assert len(products) == 2
        assert products[0]["name"] == "Product 1"
        assert products[0]["price"] == "$10"
        assert products[1]["name"] == "Product 2"

    def test_links(self):
        """Test link extraction."""
        html = """
        <html>
            <a href="/page1">Link 1</a>
            <a href="https://other.com/page">Link 2</a>
        </html>
        """
        ext = Extractor(html, base_url="https://example.com")

        links = ext.links()
        assert "https://example.com/page1" in links
        assert "https://other.com/page" in links

    def test_safe_links(self):
        """Test safe link filtering."""
        html = """
        <html>
            <a href="/page">Safe</a>
            <a href="javascript:alert(1)">JS</a>
            <a href="data:text/html,<h1>Hi</h1>">Data</a>
            <a href="mailto:test@test.com">Mail</a>
            <a href="#section">Anchor</a>
        </html>
        """
        ext = Extractor(html, base_url="https://example.com")

        links = ext.safe_links()
        # Only http/https links without fragment-only
        assert len(links) == 1
        assert "page" in links[0]

    def test_images(self):
        """Test image extraction."""
        html = """
        <html>
            <img src="/img1.png">
            <img src="https://cdn.example.com/img2.jpg">
        </html>
        """
        ext = Extractor(html, base_url="https://example.com")

        images = ext.images()
        assert len(images) == 2
        assert "https://example.com/img1.png" in images

    def test_title(self):
        """Test title extraction."""
        html = "<html><head><title>Page Title</title></head></html>"
        ext = Extractor(html)

        assert ext.title() == "Page Title"

    def test_meta(self):
        """Test meta tag extraction."""
        html = """
        <html>
            <head>
                <meta name="description" content="Page description">
                <meta name="keywords" content="a, b, c">
            </head>
        </html>
        """
        ext = Extractor(html)

        assert ext.meta("description") == "Page description"
        assert ext.meta("keywords") == "a, b, c"
        assert ext.meta("missing") == ""

    def test_og(self):
        """Test Open Graph extraction."""
        html = """
        <html>
            <head>
                <meta property="og:title" content="OG Title">
                <meta property="og:image" content="https://example.com/img.png">
            </head>
        </html>
        """
        ext = Extractor(html)

        assert ext.og("title") == "OG Title"
        assert ext.og("image") == "https://example.com/img.png"

    def test_tables(self):
        """Test table extraction."""
        html = """
        <html>
            <table>
                <tr><th>Name</th><th>Age</th></tr>
                <tr><td>Alice</td><td>30</td></tr>
                <tr><td>Bob</td><td>25</td></tr>
            </table>
        </html>
        """
        ext = Extractor(html)

        tables = ext.tables()
        assert len(tables) == 1
        assert len(tables[0]) == 3  # 3 rows
        assert tables[0][0] == ["Name", "Age"]
        assert tables[0][1] == ["Alice", "30"]


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_css(self):
        """Test css() function."""
        html = "<html><h1>Title</h1></html>"
        assert css(html, "h1") == "Title"

    def test_css_list(self):
        """Test css_list() function."""
        html = "<html><li>A</li><li>B</li></html>"
        assert css_list(html, "li") == ["A", "B"]

    def test_find_links(self):
        """Test find_links() function."""
        html = '<html><a href="/page">Link</a></html>'
        links = find_links(html, base_url="https://example.com")
        assert "https://example.com/page" in links

    def test_find_images(self):
        """Test find_images() function."""
        html = '<html><img src="/img.png"></html>'
        images = find_images(html, base_url="https://example.com")
        assert "https://example.com/img.png" in images

    def test_find_tables(self):
        """Test find_tables() function."""
        html = "<html><table><tr><td>Cell</td></tr></table></html>"
        tables = find_tables(html)
        assert len(tables) == 1


class TestSelectorBuilder:
    """Tests for SelectorBuilder class."""

    def test_basic_tag(self):
        """Test basic tag selector."""
        selector = SelectorBuilder("div").build()
        assert selector == "div"

    def test_with_class(self):
        """Test class selector."""
        selector = SelectorBuilder("div").with_class("container").build()
        assert selector == "div.container"

    def test_with_id(self):
        """Test ID selector."""
        selector = SelectorBuilder("div").with_id("main").build()
        assert selector == "div#main"

    def test_with_attr(self):
        """Test attribute selector."""
        selector = SelectorBuilder("input").with_attr("type", "text").build()
        assert selector == 'input[type="text"]'

    def test_descendant(self):
        """Test descendant selector."""
        selector = SelectorBuilder("div").descendant("p").build()
        assert selector == "div p"

    def test_child(self):
        """Test child selector."""
        selector = SelectorBuilder("ul").child("li").build()
        assert selector == "ul > li"

    def test_pseudo_text(self):
        """Test ::text pseudo-element."""
        selector = SelectorBuilder("p").text().build()
        assert selector == "p::text"

    def test_pseudo_attr(self):
        """Test ::attr() pseudo-element."""
        selector = SelectorBuilder("a").attr("href").build()
        assert selector == "a::attr(href)"

    def test_complex_selector(self):
        """Test complex selector building."""
        selector = (
            SelectorBuilder("div")
            .with_class("product")
            .child("h3")
            .attr("title")
            .build()
        )
        assert selector == "div.product > h3::attr(title)"
