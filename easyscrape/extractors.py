"""Data extraction utilities for EasyScrape.

Provides CSS and XPath selectors for extracting data from HTML.

Example
-------
    from easyscrape.extractors import Extractor

    ext = Extractor(html, base_url="https://example.com")
    title = ext.css("h1")
    links = ext.links()
"""
from __future__ import annotations

import re
from typing import Any, Final, Literal, Sequence
from urllib.parse import urljoin, urlparse

try:
    from selectolax.parser import HTMLParser
except ImportError:
    HTMLParser = None  # type: ignore

try:
    from lxml import etree
except ImportError:
    etree = None  # type: ignore

from .exceptions import ExtractionError, SelectorError

__all__: Final[tuple[str, ...]] = (
    "Extractor",
    "SelectorType",
    "css",
    "css_list",
    "find_links",
    "find_images",
    "find_tables",
    "SelectorBuilder",
)

SelectorType = Literal["css", "xpath"]

# Regex for parsing pseudo-selectors
_PSEUDO_TEXT_RE = re.compile(r"::text$")
_PSEUDO_ATTR_RE = re.compile(r"::attr\(([^)]+)\)$")

# Safe URL schemes
_SAFE_SCHEMES = frozenset({"http", "https"})


class Extractor:
    """HTML data extractor with CSS and XPath support.

    Parameters
    ----------
    html : str
        The HTML content to extract from.
    base_url : str, optional
        Base URL for resolving relative links.

    Example
    -------
        ext = Extractor(html, base_url="https://example.com")
        title = ext.css("h1")
        prices = ext.css_list(".price")
    """

    __slots__ = ("_html", "_base_url", "_parser", "_lxml_tree")

    def __init__(self, html: str, base_url: str | None = None) -> None:
        self._html = html
        self._base_url = base_url
        self._parser: Any = None
        self._lxml_tree: Any = None

    @property
    def parser(self) -> Any:
        """Get or create the selectolax parser."""
        if self._parser is None:
            if HTMLParser is None:
                raise ImportError(
                    "selectolax is required for CSS extraction. "
                    "Install with: pip install selectolax"
                )
            self._parser = HTMLParser(self._html)
        return self._parser

    @property
    def lxml_tree(self) -> Any:
        """Get or create the lxml tree for XPath."""
        if self._lxml_tree is None:
            if etree is None:
                raise ImportError(
                    "lxml is required for XPath extraction. "
                    "Install with: pip install lxml"
                )
            self._lxml_tree = etree.HTML(self._html)
        return self._lxml_tree

    def css(self, selector: str, default: str | None = None) -> str:
        """Extract text using a CSS selector.

        Parameters
        ----------
        selector : str
            CSS selector, optionally with ::text or ::attr(name).
        default : str, optional
            Default value if selector doesn't match.

        Returns
        -------
        str
            Extracted text or default value.
        """
        # Handle ::attr() pseudo-selector
        attr_match = _PSEUDO_ATTR_RE.search(selector)
        if attr_match:
            attr_name = attr_match.group(1)
            base_selector = _PSEUDO_ATTR_RE.sub("", selector)
            node = self.parser.css_first(base_selector)
            if node is None:
                return default if default is not None else ""
            return node.attributes.get(attr_name, default if default is not None else "")

        # Handle ::text pseudo-selector
        if _PSEUDO_TEXT_RE.search(selector):
            base_selector = _PSEUDO_TEXT_RE.sub("", selector)
            node = self.parser.css_first(base_selector)
            if node is None:
                return default if default is not None else ""
            text = node.text(strip=True)
            return text if text else (default if default is not None else "")

        # Regular selector - extract text
        node = self.parser.css_first(selector)
        if node is None:
            return default if default is not None else ""

        text = node.text(strip=True)
        return text if text else (default if default is not None else "")

    def css_list(self, selector: str, attr: str | None = None) -> list[str]:
        """Extract list of texts using a CSS selector.

        Parameters
        ----------
        selector : str
            CSS selector.
        attr : str, optional
            Attribute to extract instead of text.

        Returns
        -------
        list[str]
            List of extracted texts or attribute values.
        """
        # Handle ::attr() pseudo-selector in selector string
        attr_match = _PSEUDO_ATTR_RE.search(selector)
        if attr_match:
            attr = attr_match.group(1)
            selector = _PSEUDO_ATTR_RE.sub("", selector)

        # Handle ::text pseudo-selector
        selector = _PSEUDO_TEXT_RE.sub("", selector)

        nodes = self.parser.css(selector)
        if not nodes:
            return []

        if attr:
            return [node.attributes.get(attr, "") for node in nodes if node.attributes.get(attr)]
        else:
            return [node.text(strip=True) for node in nodes if node.text(strip=True)]

    def xpath(self, expression: str, default: str | None = None) -> str:
        """Extract text using XPath.

        Parameters
        ----------
        expression : str
            XPath expression.
        default : str, optional
            Default value if expression doesn't match.

        Returns
        -------
        str
            Extracted text or default value.
        """
        results = self.lxml_tree.xpath(expression)
        if not results:
            return default if default is not None else ""

        result = results[0]
        if hasattr(result, "text"):
            return result.text or (default if default is not None else "")
        return str(result)

    def xpath_list(self, expression: str) -> list[str]:
        """Extract list of texts using XPath.

        Parameters
        ----------
        expression : str
            XPath expression.

        Returns
        -------
        list[str]
            List of extracted texts.
        """
        results = self.lxml_tree.xpath(expression)
        texts = []
        for r in results:
            if hasattr(r, "text") and r.text:
                texts.append(r.text)
            elif isinstance(r, str):
                texts.append(r)
        return texts

    def extract(
        self,
        schema: dict[str, str],
        stype: SelectorType = "css",
    ) -> dict[str, str]:
        """Extract multiple fields using a schema.

        Parameters
        ----------
        schema : dict[str, str]
            Mapping of field names to selectors.
        stype : str
            Selector type: 'css' or 'xpath'.

        Returns
        -------
        dict[str, str]
            Extracted data.
        """
        result = {}
        for name, selector in schema.items():
            if stype == "xpath":
                result[name] = self.xpath(selector)
            else:
                result[name] = self.css(selector)
        return result

    def extract_all(
        self,
        container: str,
        schema: dict[str, str],
        stype: SelectorType = "css",
    ) -> list[dict[str, str]]:
        """Extract multiple items using a container selector.

        Parameters
        ----------
        container : str
            CSS selector for container elements.
        schema : dict[str, str]
            Mapping of field names to selectors (relative to container).
        stype : str
            Selector type for schema selectors.

        Returns
        -------
        list[dict[str, str]]
            List of extracted items.
        """
        containers = self.parser.css(container)
        if not containers:
            return []

        items = []
        for container_node in containers:
            # Create a sub-extractor for this container
            container_html = container_node.html
            sub_ext = Extractor(container_html, base_url=self._base_url)
            item = sub_ext.extract(schema, stype)
            items.append(item)

        return items

    def links(self) -> list[str]:
        """Extract all links from the page.

        Returns
        -------
        list[str]
            List of absolute URLs.
        """
        hrefs = self.css_list("a::attr(href)")
        result = []
        for href in hrefs:
            if not href:
                continue
            # Make absolute
            if self._base_url:
                href = urljoin(self._base_url, href)
            result.append(href)
        return result

    def safe_links(self) -> list[str]:
        """Extract safe (http/https) links only.

        Filters out javascript:, mailto:, data:, and fragment-only links.

        Returns
        -------
        list[str]
            List of safe absolute URLs.
        """
        all_links = self.links()
        safe = []
        for link in all_links:
            # Skip fragment-only links
            if link.startswith("#"):
                continue
            # Parse and check scheme
            parsed = urlparse(link)
            if parsed.scheme in _SAFE_SCHEMES:
                # Also skip if the URL is just a fragment on the same page
                if parsed.fragment and not parsed.path and not parsed.query:
                    # This is like https://example.com#section - skip it
                    continue
                safe.append(link)
        return safe

    def images(self) -> list[str]:
        """Extract all image URLs.

        Returns
        -------
        list[str]
            List of absolute image URLs.
        """
        srcs = self.css_list("img::attr(src)")
        result = []
        for src in srcs:
            if not src:
                continue
            if self._base_url:
                src = urljoin(self._base_url, src)
            result.append(src)
        return result

    def title(self) -> str:
        """Extract the page title.

        Returns
        -------
        str
            The page title or empty string.
        """
        return self.css("title")

    def meta(self, name: str) -> str:
        """Extract a meta tag value.

        Parameters
        ----------
        name : str
            The meta tag name.

        Returns
        -------
        str
            The meta content or empty string.
        """
        # Try name attribute
        node = self.parser.css_first(f'meta[name="{name}"]')
        if node:
            return node.attributes.get("content", "")

        # Try property attribute (for Open Graph)
        node = self.parser.css_first(f'meta[property="{name}"]')
        if node:
            return node.attributes.get("content", "")

        return ""

    def og(self, property_name: str) -> str:
        """Extract an Open Graph meta tag.

        Parameters
        ----------
        property_name : str
            The OG property name (without 'og:' prefix).

        Returns
        -------
        str
            The meta content or empty string.
        """
        return self.meta(f"og:{property_name}")

    def tables(self) -> list[list[list[str]]]:
        """Extract all tables as lists of rows.

        Returns
        -------
        list[list[list[str]]]
            List of tables, each table is a list of rows,
            each row is a list of cell texts.
        """
        # Use lxml for more reliable table parsing
        if self._lxml_tree is None and etree is not None:
            self._lxml_tree = etree.HTML(self._html)

        if self._lxml_tree is not None:
            tables = []
            table_elements = self._lxml_tree.xpath("//table")
            for table in table_elements:
                rows = []
                for tr in table.xpath(".//tr"):
                    cells = []
                    for cell in tr.xpath(".//th | .//td"):
                        # Get text content, handling nested elements
                        text = "".join(cell.itertext()).strip()
                        cells.append(text)
                    if cells:
                        rows.append(cells)
                if rows:
                    tables.append(rows)
            return tables

        # Fallback to selectolax
        table_nodes = self.parser.css("table")
        tables = []

        for table in table_nodes:
            rows = []
            for tr in table.css("tr"):
                cells = []
                for cell in tr.css("th, td"):
                    cells.append(cell.text(strip=True) or "")
                if cells:
                    rows.append(cells)
            if rows:
                tables.append(rows)

        return tables

    def plain_text(self) -> str:
        """Extract all text content from the page.

        Returns
        -------
        str
            Plain text content.
        """
        body = self.parser.css_first("body")
        if body:
            return body.text(strip=True) or ""
        return self.parser.text(strip=True) or ""


# Convenience functions
def css(html: str, selector: str, default: str = "") -> str:
    """Extract text using CSS selector.

    Parameters
    ----------
    html : str
        HTML content.
    selector : str
        CSS selector.
    default : str
        Default value if not found.

    Returns
    -------
    str
        Extracted text.
    """
    return Extractor(html).css(selector, default)


def css_list(html: str, selector: str, attr: str | None = None) -> list[str]:
    """Extract list of texts using CSS selector.

    Parameters
    ----------
    html : str
        HTML content.
    selector : str
        CSS selector.
    attr : str, optional
        Attribute to extract.

    Returns
    -------
    list[str]
        List of extracted texts.
    """
    return Extractor(html).css_list(selector, attr)


def find_links(html: str, base_url: str | None = None) -> list[str]:
    """Find all links in HTML.

    Parameters
    ----------
    html : str
        HTML content.
    base_url : str, optional
        Base URL for resolving relative links.

    Returns
    -------
    list[str]
        List of URLs.
    """
    return Extractor(html, base_url=base_url).links()


def find_images(html: str, base_url: str | None = None) -> list[str]:
    """Find all images in HTML.

    Parameters
    ----------
    html : str
        HTML content.
    base_url : str, optional
        Base URL for resolving relative links.

    Returns
    -------
    list[str]
        List of image URLs.
    """
    return Extractor(html, base_url=base_url).images()


def find_tables(html: str) -> list[list[list[str]]]:
    """Find all tables in HTML.

    Parameters
    ----------
    html : str
        HTML content.

    Returns
    -------
    list[list[list[str]]]
        List of tables.
    """
    return Extractor(html).tables()


class SelectorBuilder:
    """Fluent builder for CSS selectors.

    Example
    -------
        selector = (
            SelectorBuilder("div")
            .with_class("product")
            .child("h3")
            .text()
            .build()
        )
        # Result: "div.product > h3::text"
    """

    __slots__ = ("_parts",)

    def __init__(self, tag: str = "") -> None:
        self._parts: list[str] = [tag] if tag else []

    def with_class(self, class_name: str) -> SelectorBuilder:
        """Add a class selector."""
        if self._parts:
            self._parts[-1] += f".{class_name}"
        else:
            self._parts.append(f".{class_name}")
        return self

    def with_id(self, id_name: str) -> SelectorBuilder:
        """Add an ID selector."""
        if self._parts:
            self._parts[-1] += f"#{id_name}"
        else:
            self._parts.append(f"#{id_name}")
        return self

    def with_attr(self, name: str, value: str) -> SelectorBuilder:
        """Add an attribute selector."""
        if self._parts:
            self._parts[-1] += f'[{name}="{value}"]'
        else:
            self._parts.append(f'[{name}="{value}"]')
        return self

    def descendant(self, selector: str) -> SelectorBuilder:
        """Add a descendant selector."""
        self._parts.append(selector)
        return self

    def child(self, selector: str) -> SelectorBuilder:
        """Add a child selector."""
        if self._parts:
            self._parts[-1] += f" > {selector}"
        else:
            self._parts.append(f"> {selector}")
        return self

    def text(self) -> SelectorBuilder:
        """Add ::text pseudo-element."""
        if self._parts:
            self._parts[-1] += "::text"
        return self

    def attr(self, name: str) -> SelectorBuilder:
        """Add ::attr() pseudo-element."""
        if self._parts:
            self._parts[-1] += f"::attr({name})"
        return self

    def build(self) -> str:
        """Build the final selector string."""
        return " ".join(self._parts)
