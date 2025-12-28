"""Utility functions for EasyScrape.

This module provides common utility functions for URL manipulation,
text processing, data transformation, and file I/O.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from pathlib import Path
from typing import Any, Final
from urllib.parse import urljoin, urlparse, urlencode, urlunparse

from .exceptions import EasyScrapeError

__all__: Final[tuple[str, ...]] = (
    "normalise_url",
    "domain_of",
    "clean_text",
    "parse_price",
    "parse_int",
    "dedupe",
    "build_url",
    "is_valid_url",
    "strip_tags",
    "url_hash",
    "file_ext",
    "truncate",
    "to_json",
    "to_csv_string",
    "save_json",
    "save_csv",
    "load_json",
    "chunk",
    "merge",
    "flatten_dict",
    "URLMatcher",
    "_validate_file_path",
)


def normalise_url(url: str, base: str | None = None) -> str:
    """Normalise a URL, optionally resolving against a base.

    Parameters
    ----------
    url : str
        The URL to normalise.
    base : str, optional
        Base URL to resolve relative URLs against.

    Returns
    -------
    str
        The normalised URL.
    """
    if base:
        return urljoin(base, url)
    return url


def domain_of(url: str) -> str:
    """Extract the domain from a URL.

    Parameters
    ----------
    url : str
        The URL to extract from.

    Returns
    -------
    str
        The domain (hostname).
    """
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        return parsed.hostname or ""
    except Exception:
        return ""


def build_url(base: str, path: str, params: dict[str, str] | None = None) -> str:
    """Build a URL from components.

    Parameters
    ----------
    base : str
        Base URL.
    path : str
        Path to append.
    params : dict, optional
        Query parameters.

    Returns
    -------
    str
        The constructed URL.
    """
    url = urljoin(base, path)
    if params:
        parsed = urlparse(url)
        query = urlencode(params)
        url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            query,
            parsed.fragment,
        ))
    return url


def is_valid_url(url: str) -> bool:
    """Check if a URL is valid.

    Parameters
    ----------
    url : str
        The URL to check.

    Returns
    -------
    bool
        True if valid, False otherwise.
    """
    if not url:
        return False
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def url_hash(url: str) -> str:
    """Generate a hash for a URL.

    Parameters
    ----------
    url : str
        The URL to hash.

    Returns
    -------
    str
        SHA-256 hash of the URL (first 16 chars).
    """
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def file_ext(url: str) -> str:
    """Extract file extension from a URL.

    Parameters
    ----------
    url : str
        The URL to extract from.

    Returns
    -------
    str
        The file extension (without dot), or empty string.
    """
    try:
        parsed = urlparse(url)
        path = parsed.path
        if "." in path:
            ext = path.rsplit(".", 1)[-1]
            # Remove query string if accidentally included
            if "?" in ext:
                ext = ext.split("?")[0]
            return ext
    except Exception:
        pass
    return ""


def clean_text(text: str) -> str:
    """Clean and normalise text.

    Removes extra whitespace, newlines, and strips the text.

    Parameters
    ----------
    text : str
        The text to clean.

    Returns
    -------
    str
        The cleaned text.
    """
    if not text:
        return ""
    # Replace multiple whitespace with single space
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def strip_tags(html: str) -> str:
    """Remove HTML tags from text.

    Parameters
    ----------
    html : str
        HTML string to strip.

    Returns
    -------
    str
        Plain text without HTML tags.
    """
    return re.sub(r"<[^>]+>", "", html)


def truncate(text: str, length: int = 100, suffix: str = "...") -> str:
    """Truncate text to a maximum length.

    Parameters
    ----------
    text : str
        The text to truncate.
    length : int
        Maximum length before truncation.
    suffix : str
        Suffix to append when truncated.

    Returns
    -------
    str
        The truncated text.
    """
    if len(text) <= length:
        return text
    return text[:length] + suffix


def parse_price(text: str) -> float | None:
    """Extract a price from text.

    Parameters
    ----------
    text : str
        Text containing a price.

    Returns
    -------
    float or None
        The extracted price, or None if not found.
    """
    if not text:
        return None
    # Handle European format (comma as decimal)
    text = text.replace(",", ".")
    # Find numbers with optional decimal
    match = re.search(r"(\d+\.?\d*)", text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    return None


def parse_int(text: str) -> int | None:
    """Extract an integer from text.

    Parameters
    ----------
    text : str
        Text containing an integer.

    Returns
    -------
    int or None
        The extracted integer, or None if not found.
    """
    if not text:
        return None
    match = re.search(r"-?\d+", text)
    if match:
        try:
            return int(match.group())
        except ValueError:
            pass
    return None


def dedupe(items: list) -> list:
    """Remove duplicates while preserving order.

    Parameters
    ----------
    items : list
        List with potential duplicates.

    Returns
    -------
    list
        List with duplicates removed.
    """
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def chunk(items: list, size: int) -> list[list]:
    """Split a list into chunks of specified size.

    Parameters
    ----------
    items : list
        List to split.
    size : int
        Maximum chunk size.

    Returns
    -------
    list[list]
        List of chunks.
    """
    return [items[i:i + size] for i in range(0, len(items), size)]


def merge(*dicts: dict) -> dict:
    """Merge multiple dictionaries.

    Later dictionaries override earlier ones.

    Parameters
    ----------
    *dicts : dict
        Dictionaries to merge.

    Returns
    -------
    dict
        Merged dictionary.
    """
    result = {}
    for d in dicts:
        result.update(d)
    return result


def flatten_dict(d: dict, sep: str = ".", prefix: str = "") -> dict:
    """Flatten a nested dictionary.

    Parameters
    ----------
    d : dict
        Dictionary to flatten.
    sep : str
        Separator for nested keys.
    prefix : str
        Prefix for keys (used in recursion).

    Returns
    -------
    dict
        Flattened dictionary.
    """
    result = {}
    for key, value in d.items():
        new_key = f"{prefix}{sep}{key}" if prefix else key
        if isinstance(value, dict):
            result.update(flatten_dict(value, sep, new_key))
        else:
            result[new_key] = value
    return result


def to_json(data: Any, pretty: bool = False) -> str:
    """Convert data to JSON string.

    Parameters
    ----------
    data : Any
        Data to serialise.
    pretty : bool
        Use pretty printing.

    Returns
    -------
    str
        JSON string.
    """
    indent = 2 if pretty else None
    return json.dumps(data, indent=indent, ensure_ascii=False, default=str)


def to_csv_string(rows: list[dict], fieldnames: list[str] | None = None) -> str:
    """Convert list of dicts to CSV string.

    Parameters
    ----------
    rows : list[dict]
        Data rows.
    fieldnames : list[str], optional
        Column names. If None, uses keys from first row.

    Returns
    -------
    str
        CSV string.
    """
    if not rows:
        return ""
    fields = fieldnames or list(rows[0].keys())
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def save_json(data: Any, path: str | Path, pretty: bool = True) -> None:
    """Save data to a JSON file.

    Parameters
    ----------
    data : Any
        Data to save.
    path : str or Path
        Output file path.
    pretty : bool
        Use pretty printing.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = to_json(data, pretty=pretty)
    path.write_text(content, encoding="utf-8")


def save_csv(rows: list[dict], path: str | Path, fieldnames: list[str] | None = None) -> None:
    """Save data to a CSV file.

    Parameters
    ----------
    rows : list[dict]
        Data rows.
    path : str or Path
        Output file path.
    fieldnames : list[str], optional
        Column names.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = to_csv_string(rows, fieldnames)
    path.write_text(content, encoding="utf-8")


def load_json(path: str | Path) -> Any:
    """Load data from a JSON file.

    Parameters
    ----------
    path : str or Path
        Input file path.

    Returns
    -------
    Any
        Loaded data.
    """
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_file_path(path: str, base_dir: str | None = None) -> Path:
    """Validate a file path to prevent directory traversal.

    Parameters
    ----------
    path : str
        The path to validate.
    base_dir : str, optional
        Base directory to resolve against.

    Returns
    -------
    Path
        The validated path.

    Raises
    ------
    EasyScrapeError
        If path traversal is detected.
    """
    if ".." in path:
        raise EasyScrapeError(f"Path traversal detected: {path}")
    
    base = Path(base_dir) if base_dir else Path.cwd()
    base = base.resolve()
    target = (base / path).resolve()
    
    try:
        target.relative_to(base)
    except ValueError:
        raise EasyScrapeError(f"Path traversal detected: {path}") from None
    
    return target


class URLMatcher:
    """URL pattern matcher.

    Parameters
    ----------
    patterns : list[str]
        Regex patterns to match against URLs.

    Example
    -------
        matcher = URLMatcher([r"/products/\d+"])
        matcher.matches("https://example.com/products/123")  # True
    """

    def __init__(self, patterns: list[str]) -> None:
        self._patterns = [re.compile(p) for p in patterns]

    def matches(self, url: str) -> bool:
        """Check if URL matches any pattern.

        Parameters
        ----------
        url : str
            URL to check.

        Returns
        -------
        bool
            True if any pattern matches.
        """
        for pattern in self._patterns:
            if pattern.search(url):
                return True
        return False
