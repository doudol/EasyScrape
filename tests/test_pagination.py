"""Comprehensive tests for easyscrape.pagination module."""

import pytest
from unittest.mock import MagicMock, patch
from easyscrape.pagination import (
    _increment_page_param,
    _find_next_link,
    paginate,
    paginate_param,
    paginate_offset,
    crawl,
)


# =============================================================================
# Helper Function Tests
# =============================================================================

class TestIncrementPageParam:
    """Tests for _increment_page_param helper."""

    def test_increment_existing_page(self):
        url = "https://example.com/search?page=3"
        result = _increment_page_param(url, "page", 1)
        assert "page=4" in result

    def test_increment_by_custom_amount(self):
        url = "https://example.com?page=5"
        result = _increment_page_param(url, "page", 5)
        assert "page=10" in result

    def test_add_page_when_missing(self):
        url = "https://example.com/search?q=test"
        result = _increment_page_param(url, "page", 1)
        assert "page=2" in result
        assert "q=test" in result

    def test_custom_param_name(self):
        url = "https://example.com?p=1"
        result = _increment_page_param(url, "p", 1)
        assert "p=2" in result

    def test_handles_non_numeric_value(self):
        url = "https://example.com?page=abc"
        result = _increment_page_param(url, "page", 1)
        # Falls back to 1, so result should be 2
        assert "page=2" in result

    def test_preserves_other_params(self):
        url = "https://example.com?q=test&page=1&sort=asc"
        result = _increment_page_param(url, "page", 1)
        assert "page=2" in result
        assert "q=test" in result
        assert "sort=asc" in result

    def test_no_query_string(self):
        url = "https://example.com/search"
        result = _increment_page_param(url, "page", 1)
        # Should add page=2 (1 + 1)
        assert "page=2" in result


class TestFindNextLink:
    """Tests for _find_next_link helper."""

    def test_returns_none_when_no_text(self):
        result = MagicMock()
        result.text = None
        assert _find_next_link(result) is None

    def test_returns_none_for_empty_text(self):
        result = MagicMock()
        result.text = ""
        assert _find_next_link(result) is None

    def test_finds_rel_next(self):
        result = MagicMock()
        result.text = '<html><body><a href="/page2" rel="next">Next</a></body></html>'
        result.final_url = "https://example.com/"
        
        # Mock css_list to return href
        result.extractor.css_list.return_value = ["/page2"]
        
        # Mock parser for fallback
        anchor = MagicMock()
        anchor.html = '<a href="/page2" rel="next">Next</a>'
        anchor.attributes = {"href": "/page2"}
        result.extractor.parser.css.return_value = [anchor]
        
        next_url = _find_next_link(result)
        assert next_url == "https://example.com/page2"

    def test_finds_next_class(self):
        result = MagicMock()
        result.text = '<html><a href="/page2" class="pagination-next">Next</a></html>'
        result.final_url = "https://example.com/"
        
        # Mock css_list to return href
        result.extractor.css_list.return_value = ["/page2"]
        
        # Mock parser for fallback
        anchor = MagicMock()
        anchor.html = '<a href="/page2" class="pagination-next">Next</a>'
        anchor.attributes = {"href": "/page2"}
        result.extractor.parser.css.return_value = [anchor]
        
        next_url = _find_next_link(result)
        assert next_url == "https://example.com/page2"

    def test_finds_next_text(self):
        result = MagicMock()
        result.text = '<html><a href="/page2">next</a></html>'
        result.final_url = "https://example.com/"
        
        # Mock css_list to return empty for common selectors, fall back to regex
        result.extractor.css_list.return_value = []
        
        # Mock parser for fallback
        anchor = MagicMock()
        anchor.html = '<a href="/page2">next</a>'
        anchor.attributes = {"href": "/page2"}
        result.extractor.parser.css.return_value = [anchor]
        
        next_url = _find_next_link(result)
        assert next_url == "https://example.com/page2"

    def test_handles_absolute_url(self):
        result = MagicMock()
        result.text = '<html><a href="https://other.com/page2" rel="next">Next</a></html>'
        result.final_url = "https://example.com/"
        
        # Mock css_list to return absolute href
        result.extractor.css_list.return_value = ["https://other.com/page2"]
        
        # Mock parser for fallback
        anchor = MagicMock()
        anchor.html = '<a href="https://other.com/page2" rel="next">Next</a>'
        anchor.attributes = {"href": "https://other.com/page2"}
        result.extractor.parser.css.return_value = [anchor]
        
        next_url = _find_next_link(result)
        assert next_url == "https://other.com/page2"

    def test_custom_patterns(self):
        result = MagicMock()
        result.text = '<html><a href="/page2" data-action="load-more">More</a></html>'
        result.final_url = "https://example.com/"
        
        # Mock css_list to return empty for common selectors
        result.extractor.css_list.return_value = []
        
        # Mock parser for fallback
        anchor = MagicMock()
        anchor.html = '<a href="/page2" data-action="load-more">More</a>'
        anchor.attributes = {"href": "/page2"}
        result.extractor.parser.css.return_value = [anchor]
        
        next_url = _find_next_link(result, patterns=[r'data-action=["\']load-more["\']'])
        assert next_url == "https://example.com/page2"

    def test_no_matching_links(self):
        result = MagicMock()
        result.text = '<html><a href="/about">About</a></html>'
        result.final_url = "https://example.com/"
        
        # Mock css_list to return empty
        result.extractor.css_list.return_value = []
        
        # Mock parser for fallback
        anchor = MagicMock()
        anchor.html = '<a href="/about">About</a>'
        anchor.attributes = {"href": "/about"}
        result.extractor.parser.css.return_value = [anchor]
        
        next_url = _find_next_link(result)
        assert next_url is None


# =============================================================================
# Generator Function Tests
# =============================================================================

class TestPaginate:
    """Tests for paginate generator."""

    def test_returns_generator(self):
        gen = paginate("https://example.com")
        assert hasattr(gen, "__iter__")
        assert hasattr(gen, "__next__")

    def test_max_pages_default(self):
        # Should use default max_pages=100
        gen = paginate("https://example.com")
        assert gen is not None

    @patch('easyscrape.pagination.scrape')
    def test_yields_results(self, mock_scrape):
        # First result with no next link
        result1 = MagicMock()
        result1.text = "<html></html>"
        result1.final_url = "https://example.com/"
        result1.extractor.css_list.return_value = []
        result1.extractor.parser.css.return_value = []
        mock_scrape.return_value = result1
        
        results = list(paginate("https://example.com", max_pages=1))
        assert len(results) == 1

    @patch('easyscrape.pagination.scrape')
    def test_stop_if_callback(self, mock_scrape):
        result = MagicMock()
        result.text = "<html></html>"
        result.final_url = "https://example.com/"
        result.extractor.css_list.return_value = []
        result.extractor.parser.css.return_value = []
        mock_scrape.return_value = result
        
        def stop_always(r):
            return True
        
        results = list(paginate("https://example.com", stop_if=stop_always))
        assert len(results) == 1

    @patch('easyscrape.pagination.scrape')
    def test_uses_next_selector(self, mock_scrape):
        result1 = MagicMock()
        result1.text = '<html><a class="next" href="/page2">Next</a></html>'
        result1.final_url = "https://example.com/page1"
        result1.extractor.css_list.return_value = ["/page2"]
        
        result2 = MagicMock()
        result2.text = '<html></html>'
        result2.final_url = "https://example.com/page2"
        result2.extractor.css_list.return_value = []
        
        mock_scrape.side_effect = [result1, result2]
        
        results = list(paginate(
            "https://example.com/page1",
            next_selector="a.next",
            max_pages=5
        ))
        assert len(results) == 2


class TestPaginateParam:
    """Tests for paginate_param generator."""

    def test_returns_generator(self):
        gen = paginate_param("https://example.com", param="page", start=1, end=3)
        assert hasattr(gen, "__iter__")
        assert hasattr(gen, "__next__")

    def test_default_params(self):
        gen = paginate_param("https://example.com/")
        assert gen is not None

    @patch('easyscrape.pagination.scrape')
    def test_iterates_page_range(self, mock_scrape):
        mock_scrape.return_value = MagicMock()
        
        results = list(paginate_param(
            "https://example.com",
            param="page",
            start=1,
            end=3
        ))
        assert len(results) == 3
        assert mock_scrape.call_count == 3

    @patch('easyscrape.pagination.scrape')
    def test_stop_if_callback(self, mock_scrape):
        mock_scrape.return_value = MagicMock()
        
        call_count = 0
        def stop_after_two(r):
            nonlocal call_count
            call_count += 1
            return call_count >= 2
        
        results = list(paginate_param(
            "https://example.com",
            start=1,
            end=10,
            stop_if=stop_after_two
        ))
        assert len(results) == 2

    @patch('easyscrape.pagination.scrape')
    def test_handles_scrape_exception(self, mock_scrape):
        mock_scrape.side_effect = Exception("Network error")
        
        results = list(paginate_param("https://example.com", start=1, end=5))
        assert len(results) == 0


class TestPaginateOffset:
    """Tests for paginate_offset generator."""

    def test_returns_generator(self):
        gen = paginate_offset("https://example.com/api", step=10, max_offset=30)
        assert hasattr(gen, "__iter__")
        assert hasattr(gen, "__next__")

    def test_default_params(self):
        gen = paginate_offset("https://example.com/")
        assert gen is not None

    @patch('easyscrape.pagination.scrape')
    def test_iterates_offsets(self, mock_scrape):
        mock_scrape.return_value = MagicMock()
        
        results = list(paginate_offset(
            "https://example.com/api",
            step=10,
            start=0,
            max_offset=20
        ))
        # 0, 10, 20 = 3 pages
        assert len(results) == 3

    @patch('easyscrape.pagination.scrape')
    def test_stop_if_callback(self, mock_scrape):
        mock_scrape.return_value = MagicMock()
        
        def stop_always(r):
            return True
        
        results = list(paginate_offset(
            "https://example.com/api",
            max_offset=100,
            stop_if=stop_always
        ))
        assert len(results) == 1

    @patch('easyscrape.pagination.scrape')
    def test_custom_param_name(self, mock_scrape):
        mock_scrape.return_value = MagicMock()
        
        list(paginate_offset(
            "https://example.com/api",
            param="start",
            step=20,
            max_offset=20
        ))
        
        # Check that correct param was used
        calls = mock_scrape.call_args_list
        assert "start=0" in calls[0][0][0]
        assert "start=20" in calls[1][0][0]


class TestCrawl:
    """Tests for crawl generator."""

    def test_returns_generator(self):
        gen = crawl("https://example.com")
        assert hasattr(gen, "__iter__")
        assert hasattr(gen, "__next__")

    @patch('easyscrape.pagination.scrape')
    def test_respects_max_pages(self, mock_scrape):
        result = MagicMock()
        result.final_url = "https://example.com/"
        result.links.return_value = []
        mock_scrape.return_value = result
        
        results = list(crawl("https://example.com", max_pages=1))
        assert len(results) == 1

    @patch('easyscrape.pagination.scrape')
    def test_follows_links(self, mock_scrape):
        result1 = MagicMock()
        result1.final_url = "https://example.com/"
        result1.links.return_value = ["https://example.com/page2"]
        
        result2 = MagicMock()
        result2.final_url = "https://example.com/page2"
        result2.links.return_value = []
        
        mock_scrape.side_effect = [result1, result2]
        
        results = list(crawl("https://example.com", max_pages=10))
        assert len(results) == 2

    @patch('easyscrape.pagination.scrape')
    def test_same_domain_filter(self, mock_scrape):
        result = MagicMock()
        result.final_url = "https://example.com/"
        result.links.return_value = [
            "https://example.com/page2",
            "https://external.com/page"  # Should be filtered out
        ]
        
        result2 = MagicMock()
        result2.final_url = "https://example.com/page2"
        result2.links.return_value = []
        
        mock_scrape.side_effect = [result, result2]
        
        results = list(crawl("https://example.com", same_domain=True, max_pages=10))
        # Only 2 results because external.com is filtered
        assert len(results) == 2

    @patch('easyscrape.pagination.scrape')
    def test_stop_if_callback(self, mock_scrape):
        result = MagicMock()
        result.final_url = "https://example.com/"
        result.links.return_value = ["https://example.com/page2"]
        mock_scrape.return_value = result
        
        def stop_always(r):
            return True
        
        results = list(crawl("https://example.com", stop_if=stop_always))
        assert len(results) == 1

    @patch('easyscrape.pagination.scrape')
    def test_deduplicates_urls(self, mock_scrape):
        result = MagicMock()
        result.final_url = "https://example.com/"
        # Returns the same URL multiple times
        result.links.return_value = [
            "https://example.com/",
            "https://example.com",
            "https://EXAMPLE.COM/"
        ]
        mock_scrape.return_value = result
        
        results = list(crawl("https://example.com", max_pages=10))
        # Should only scrape once
        assert len(results) == 1

    @patch('easyscrape.pagination.scrape')
    def test_handles_scrape_exception(self, mock_scrape):
        mock_scrape.side_effect = Exception("Network error")
        
        results = list(crawl("https://example.com", max_pages=5))
        # Should handle exception and continue (return empty)
        assert len(results) == 0
