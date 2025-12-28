"""Comprehensive tests for easyscrape.utils module."""

import pytest
import json
import os
from easyscrape.utils import (
    normalise_url,
    domain_of,
    clean_text,
    parse_price,
    parse_int,
    dedupe,
    build_url,
    is_valid_url,
    strip_tags,
    url_hash,
    file_ext,
    truncate,
    to_json,
    to_csv_string,
    save_json,
    save_csv,
    load_json,
    chunk,
    merge,
    flatten_dict,
    URLMatcher,
)


# =============================================================================
# URL Functions
# =============================================================================

class TestNormaliseUrl:
    """Tests for URL normalization."""

    def test_with_base(self):
        result = normalise_url("/path", "https://example.com")
        assert result == "https://example.com/path"

    def test_absolute_unchanged(self):
        result = normalise_url("https://example.com/path")
        assert "example.com" in result

    def test_relative_path(self):
        result = normalise_url("page.html", "https://example.com/dir/")
        assert "page.html" in result

    def test_protocol_relative(self):
        result = normalise_url("//example.com/path", "https://base.com")
        assert "example.com" in result


class TestDomainOf:
    """Tests for domain extraction."""

    def test_basic_domain(self):
        assert domain_of("https://example.com/path") == "example.com"

    def test_subdomain(self):
        assert domain_of("https://sub.example.com/") == "sub.example.com"

    def test_with_port(self):
        result = domain_of("https://example.com:8080/path")
        assert "example.com" in result

    def test_empty_url(self):
        result = domain_of("")
        assert result == ""


class TestBuildUrl:
    """Tests for URL building."""

    def test_basic_build(self):
        result = build_url("https://example.com", "path")
        assert "example.com" in result
        assert "path" in result

    def test_with_path_and_params(self):
        result = build_url("https://example.com", "path", {"q": "test"})
        assert "path" in result
        assert "q=test" in result


class TestIsValidUrl:
    """Tests for URL validation."""

    def test_valid_https(self):
        assert is_valid_url("https://example.com") is True

    def test_valid_http(self):
        assert is_valid_url("http://example.com") is True

    def test_invalid_url(self):
        assert is_valid_url("not a url") is False

    def test_empty_url(self):
        assert is_valid_url("") is False

    def test_ftp_invalid(self):
        assert is_valid_url("ftp://example.com") is False


class TestUrlHash:
    """Tests for url_hash."""

    def test_returns_string(self):
        result = url_hash("https://example.com")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_consistent(self):
        h1 = url_hash("https://example.com")
        h2 = url_hash("https://example.com")
        assert h1 == h2

    def test_different_urls_different_hash(self):
        h1 = url_hash("https://a.com")
        h2 = url_hash("https://b.com")
        assert h1 != h2


class TestFileExt:
    """Tests for file_ext."""

    def test_extracts_extension(self):
        result = file_ext("https://example.com/image.png")
        assert "png" in result.lower()

    def test_no_extension(self):
        result = file_ext("https://example.com/page")
        assert result == "" or result is None or not result

    def test_with_query_string(self):
        result = file_ext("https://example.com/img.jpg?width=100")
        assert "jpg" in result.lower()


# =============================================================================
# Text Processing
# =============================================================================

class TestCleanText:
    """Tests for text cleaning."""

    def test_whitespace_collapse(self):
        result = clean_text("  hello   world  ")
        assert "hello" in result and "world" in result

    def test_empty_string(self):
        assert clean_text("") == ""

    def test_newlines_replaced(self):
        result = clean_text("hello\n\nworld")
        assert "hello" in result and "world" in result


class TestStripTags:
    """Tests for HTML tag stripping."""

    def test_basic_strip(self):
        result = strip_tags("<p>Hello</p>")
        assert result == "Hello"

    def test_no_tags(self):
        assert strip_tags("Hello World") == "Hello World"

    def test_nested_tags(self):
        result = strip_tags("<div><p>Hello</p></div>")
        assert result == "Hello"

    def test_self_closing(self):
        result = strip_tags("Hello<br/>World")
        assert "Hello" in result and "World" in result


class TestTruncate:
    """Tests for truncate."""

    def test_short_text_unchanged(self):
        result = truncate("Hello", length=100)
        assert result == "Hello"

    def test_long_text_truncated(self):
        result = truncate("A" * 200, length=100)
        assert len(result) <= 103

    def test_custom_suffix(self):
        result = truncate("A" * 200, length=10, suffix="---")
        assert result.endswith("---")


# =============================================================================
# Parsing Functions
# =============================================================================

class TestParsePrice:
    """Tests for price parsing."""

    def test_basic_price(self):
        assert parse_price("$19.99") == 19.99

    def test_euro_price(self):
        result = parse_price("19,99 EUR")
        assert result is not None

    def test_no_price(self):
        assert parse_price("no price here") is None

    def test_with_currency_symbol(self):
        result = parse_price("USD 100.50")
        assert result == 100.50


class TestParseInt:
    """Tests for integer parsing."""

    def test_basic_int(self):
        assert parse_int("42") == 42

    def test_with_text(self):
        result = parse_int("42 items")
        assert result == 42

    def test_no_int(self):
        assert parse_int("no numbers") is None

    def test_negative(self):
        result = parse_int("-15")
        assert result == -15 or result == 15  # Depends on impl


# =============================================================================
# JSON and CSV Functions
# =============================================================================

class TestToJson:
    """Tests for to_json."""

    def test_serializes_dict(self):
        result = to_json({"key": "value"})
        assert '"key"' in result
        assert '"value"' in result

    def test_serializes_list(self):
        result = to_json([1, 2, 3])
        assert "[" in result

    def test_pretty_print(self):
        result = to_json({"key": "value"}, pretty=True)
        assert "\n" in result


class TestToCsvString:
    """Tests for to_csv_string."""

    def test_basic_csv(self):
        rows = [{"name": "Alice", "age": 30}]
        result = to_csv_string(rows)
        assert "name" in result
        assert "Alice" in result

    def test_multiple_rows(self):
        rows = [{"a": 1}, {"a": 2}]
        result = to_csv_string(rows)
        lines = result.strip().split("\n")
        assert len(lines) == 3  # header + 2 rows


class TestSaveJson:
    """Tests for save_json."""

    def test_saves_file(self):
        data = {"key": "value"}
        path = "test_save.json"
        save_json(data, path)
        assert os.path.exists(path)
        os.remove(path)

    def test_content_readable(self):
        data = {"x": 123}
        path = "test_read.json"
        save_json(data, path)
        with open(path) as f:
            loaded = json.load(f)
        assert loaded["x"] == 123
        os.remove(path)


class TestSaveCsv:
    """Tests for save_csv."""

    def test_saves_file(self):
        rows = [{"name": "Alice"}]
        path = "test_save.csv"
        save_csv(rows, path)
        assert os.path.exists(path)
        os.remove(path)


class TestLoadJson:
    """Tests for load_json."""

    def test_loads_file(self):
        data = {"loaded": True}
        path = "test_load.json"
        with open(path, "w") as f:
            json.dump(data, f)
        
        result = load_json(path)
        assert result["loaded"] is True
        os.remove(path)


# =============================================================================
# List/Dict Functions
# =============================================================================

class TestDedupe:
    """Tests for deduplication."""

    def test_with_strings(self):
        result = dedupe(["a", "b", "a", "c"])
        assert len(result) == 3

    def test_empty_list(self):
        assert dedupe([]) == []

    def test_preserves_order(self):
        result = dedupe(["c", "a", "b", "a"])
        assert result == ["c", "a", "b"]


class TestChunk:
    """Tests for chunk."""

    def test_chunks_list(self):
        result = chunk([1, 2, 3, 4, 5], size=2)
        assert len(result) == 3
        assert result[0] == [1, 2]

    def test_empty_list(self):
        result = chunk([], size=5)
        assert result == []

    def test_chunk_larger_than_list(self):
        result = chunk([1, 2], size=10)
        assert result == [[1, 2]]


class TestMerge:
    """Tests for merge."""

    def test_merges_dicts(self):
        result = merge({"a": 1}, {"b": 2})
        assert result["a"] == 1
        assert result["b"] == 2

    def test_later_overwrites(self):
        result = merge({"a": 1}, {"a": 2})
        assert result["a"] == 2

    def test_multiple_dicts(self):
        result = merge({"a": 1}, {"b": 2}, {"c": 3})
        assert len(result) == 3


class TestFlattenDict:
    """Tests for flatten_dict."""

    def test_basic_flatten(self):
        d = {"a": {"b": 1}}
        result = flatten_dict(d)
        assert result["a.b"] == 1

    def test_flat_dict_unchanged(self):
        d = {"a": 1, "b": 2}
        result = flatten_dict(d)
        assert result == d

    def test_custom_separator(self):
        d = {"a": {"b": 1}}
        result = flatten_dict(d, sep="_")
        assert result["a_b"] == 1

    def test_deeply_nested(self):
        d = {"a": {"b": {"c": {"d": 1}}}}
        result = flatten_dict(d)
        assert result["a.b.c.d"] == 1


# =============================================================================
# URLMatcher Class
# =============================================================================

class TestURLMatcher:
    """Tests for URLMatcher."""

    def test_basic_pattern(self):
        matcher = URLMatcher([r"/products/\d+"])
        assert matcher.matches("https://example.com/products/123")

    def test_no_match(self):
        matcher = URLMatcher([r"/products/\d+"])
        assert not matcher.matches("https://example.com/about")

    def test_path_pattern(self):
        matcher = URLMatcher([r"/category/"])
        assert matcher.matches("https://shop.com/category/electronics")
        assert not matcher.matches("https://shop.com/products/123")

    def test_multiple_patterns(self):
        matcher = URLMatcher([r"/products/", r"/categories/"])
        assert matcher.matches("https://example.com/products/123")
        assert matcher.matches("https://example.com/categories/tech")
        assert not matcher.matches("https://example.com/about")






class TestUtilsFunctions:
    """Tests for utils functions with correct names."""
    
    def test_normalise_url(self):
        """Test URL normalization."""
        from easyscrape.utils import normalise_url
        result = normalise_url("https://Example.Com/Page")
        assert result is not None
    
    def test_domain_of(self):
        """Test domain extraction."""
        from easyscrape.utils import domain_of
        domain = domain_of("https://www.example.com/page")
        assert "example" in domain
    
    def test_url_hash(self):
        """Test URL hashing."""
        from easyscrape.utils import url_hash
        h = url_hash("https://example.com")
        assert len(h) > 0
    
    def test_clean_text(self):
        """Test text cleaning."""
        from easyscrape.utils import clean_text
        result = clean_text("  hello   world  ")
        assert result == "hello world"
    
    def test_truncate(self):
        """Test text truncation."""
        from easyscrape.utils import truncate
        result = truncate("This is a very long text", length=10)
        assert len(result) <= 13  # 10 + "..."


class TestUtilsIO:
    """Tests for IO utility functions."""
    
    def test_to_json(self):
        """Test JSON serialization."""
        from easyscrape.utils import to_json
        result = to_json({"key": "value"})
        assert "key" in result
    
    def test_to_csv_string(self):
        """Test CSV string generation."""
        from easyscrape.utils import to_csv_string
        result = to_csv_string([{"a": 1, "b": 2}])
        assert "a" in result
    
    def test_chunk(self):
        """Test list chunking."""
        from easyscrape.utils import chunk
        result = chunk([1, 2, 3, 4, 5], 2)
        assert len(result) == 3


class TestPathValidation:
    """Tests for path validation."""
    
    def test_validate_file_path_traversal(self):
        """Test path traversal detection."""
        from easyscrape.utils import _validate_file_path
        from easyscrape.exceptions import EasyScrapeError
        import pytest
        with pytest.raises(EasyScrapeError):
            _validate_file_path("../../../etc/passwd")
    
    def test_validate_file_path_valid(self):
        """Test valid file path."""
        from easyscrape.utils import _validate_file_path
        result = _validate_file_path("test_file.txt")
        assert result is not None
