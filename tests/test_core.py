"""Tests for core scraping functions."""
import pytest
import respx
from httpx import Response as HttpxResponse

from easyscrape import scrape, Config
from easyscrape.core import ScrapingResult, async_scrape
from easyscrape.exceptions import InvalidURLError, RobotsBlocked


class TestScrape:
    """Tests for the scrape() function."""

    @respx.mock
    def test_basic_scrape(self):
        """Test basic scraping."""
        respx.get("https://example.com").mock(
            return_value=HttpxResponse(200, text="<html><h1>Test</h1></html>")
        )

        result = scrape("https://example.com")

        assert result.status_code == 200
        assert result.ok is True
        assert "Test" in result.text

    @respx.mock
    def test_scrape_with_config(self):
        """Test scraping with custom config."""
        respx.get("https://example.com").mock(
            return_value=HttpxResponse(200, text="<html></html>")
        )

        config = Config(timeout=60.0)
        result = scrape("https://example.com", config=config)

        assert result.ok is True

    def test_scrape_invalid_url(self):
        """Test scraping with invalid URL."""
        with pytest.raises(InvalidURLError):
            scrape("not-a-valid-url")

    def test_scrape_blocked_url(self):
        """Test scraping blocked URLs."""
        with pytest.raises(InvalidURLError):
            scrape("http://localhost/admin")

        with pytest.raises(InvalidURLError):
            scrape("http://127.0.0.1/secret")

        with pytest.raises(InvalidURLError):
            scrape("http://169.254.169.254/metadata")


class TestScrapingResult:
    """Tests for ScrapingResult class."""

    @respx.mock
    def test_css_extraction(self):
        """Test CSS selector extraction."""
        html = "<html><body><h1>Title</h1><p class='intro'>Hello</p></body></html>"
        respx.get("https://example.com").mock(
            return_value=HttpxResponse(200, text=html)
        )

        result = scrape("https://example.com")

        assert result.css("h1") == "Title"
        assert result.css(".intro") == "Hello"
        assert result.css(".missing", "default") == "default"

    @respx.mock
    def test_css_list_extraction(self):
        """Test CSS list extraction."""
        html = "<html><ul><li>One</li><li>Two</li><li>Three</li></ul></html>"
        respx.get("https://example.com").mock(
            return_value=HttpxResponse(200, text=html)
        )

        result = scrape("https://example.com")
        items = result.css_list("li")

        assert len(items) == 3
        assert items[0] == "One"

    @respx.mock
    def test_extract_schema(self):
        """Test structured extraction."""
        html = '<html><h1>Product</h1><span class="price">$99</span></html>'
        respx.get("https://example.com").mock(
            return_value=HttpxResponse(200, text=html)
        )

        result = scrape("https://example.com")
        data = result.extract({
            "name": "h1",
            "price": ".price",
        })

        assert data["name"] == "Product"
        assert data["price"] == "$99"

    @respx.mock
    def test_extract_all(self):
        """Test multiple item extraction."""
        html = """
        <html>
            <div class="item"><h3>Item 1</h3><span>$10</span></div>
            <div class="item"><h3>Item 2</h3><span>$20</span></div>
        </html>
        """
        respx.get("https://example.com").mock(
            return_value=HttpxResponse(200, text=html)
        )

        result = scrape("https://example.com")
        items = result.extract_all(".item", {
            "name": "h3",
            "price": "span",
        })

        assert len(items) == 2
        assert items[0]["name"] == "Item 1"
        assert items[1]["price"] == "$20"

    @respx.mock
    def test_links_extraction(self):
        """Test link extraction."""
        html = '<html><a href="/page1">Link 1</a><a href="https://other.com">Link 2</a></html>'
        respx.get("https://example.com").mock(
            return_value=HttpxResponse(200, text=html)
        )

        result = scrape("https://example.com")
        links = result.links()

        assert len(links) == 2
        assert "https://example.com/page1" in links
        assert "https://other.com" in links

    @respx.mock
    def test_safe_links(self):
        """Test safe link extraction."""
        html = """
        <html>
            <a href="/page">Safe</a>
            <a href="javascript:alert(1)">Bad</a>
            <a href="mailto:test@test.com">Email</a>
        </html>
        """
        respx.get("https://example.com").mock(
            return_value=HttpxResponse(200, text=html)
        )

        result = scrape("https://example.com")
        links = result.safe_links()

        assert len(links) == 1
        assert "page" in links[0]

    @respx.mock
    def test_json_response(self):
        """Test JSON response parsing."""
        respx.get("https://api.example.com/data").mock(
            return_value=HttpxResponse(
                200,
                json={"name": "test", "value": 42},
            )
        )

        result = scrape("https://api.example.com/data")
        data = result.json()

        assert data["name"] == "test"
        assert data["value"] == 42


class TestAsyncScrape:
    """Tests for async_scrape() function."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_async_scrape(self):
        """Test async scraping."""
        respx.get("https://example.com").mock(
            return_value=HttpxResponse(200, text="<html><h1>Async</h1></html>")
        )

        result = await async_scrape("https://example.com")

        assert result.status_code == 200
        assert result.css("h1") == "Async"

    @pytest.mark.asyncio
    async def test_async_scrape_invalid_url(self):
        """Test async scraping with invalid URL."""
        with pytest.raises(InvalidURLError):
            await async_scrape("http://localhost")
