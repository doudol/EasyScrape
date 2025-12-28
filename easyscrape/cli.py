"""Command-line interface for EasyScrape.

Provides a CLI for quick scraping tasks:

    easyscrape https://example.com --links
    easyscrape https://example.com -e title=h1 -e price=.price
    easyscrape https://example.com -c .product -e name=.name -o data.csv

"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Final

from .config import Config
from .core import scrape

__all__: Final[tuple[str, ...]] = (
    "main",
    "run_cli",
    "_create_argument_parser",
    "_build_config",
    "_extract_data",
    "_output_result",
)


def _create_argument_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="easyscrape",
        description="Fast, secure web scraping from the command line.",
    )

    parser.add_argument(
        "url",
        help="URL to scrape",
    )

    parser.add_argument(
        "selectors",
        nargs="*",
        help="CSS selectors or name=selector pairs",
    )

    parser.add_argument(
        "-e", "--extract",
        action="append",
        metavar="NAME=SELECTOR",
        dest="extract_args",
        help="Extract field (can be repeated)",
    )

    parser.add_argument(
        "-c", "--container",
        metavar="SELECTOR",
        help="Container selector for multiple items",
    )

    parser.add_argument(
        "--links",
        action="store_true",
        help="Extract all links",
    )

    parser.add_argument(
        "--images",
        action="store_true",
        help="Extract all image URLs",
    )

    parser.add_argument(
        "--meta",
        action="store_true",
        help="Extract meta tags",
    )

    parser.add_argument(
        "--text",
        action="store_true",
        help="Extract all text content",
    )

    parser.add_argument(
        "-x", "--xpath-mode",
        action="store_true",
        help="Use XPath instead of CSS selectors",
    )

    parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        help="Output file (default: stdout)",
    )

    parser.add_argument(
        "-f", "--format",
        choices=["json", "csv", "jsonl", "text"],
        default="json",
        help="Output format (default: json)",
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Request timeout in seconds",
    )

    parser.add_argument(
        "--user-agent",
        metavar="UA",
        help="Custom User-Agent string",
    )

    parser.add_argument(
        "--proxy",
        metavar="URL",
        help="Proxy URL",
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching",
    )

    parser.add_argument(
        "--js",
        action="store_true",
        help="Enable JavaScript rendering",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )

    return parser


def _build_config(args: argparse.Namespace) -> Config:
    """Build Config from parsed arguments."""
    headers = {}
    if args.user_agent:
        headers["User-Agent"] = args.user_agent

    proxies = []
    if args.proxy:
        proxies = [args.proxy]

    return Config(
        timeout=args.timeout,
        cache_enabled=not args.no_cache,
        javascript=args.js,
        headers=headers,
        proxies=proxies,
        verbose=args.verbose,
        rotate_ua=False if args.user_agent else False,
    )


def _parse_extractions(extract_args: list[str] | None, selectors: list[str] | None) -> dict[str, str]:
    """Parse extraction arguments into a mapping."""
    mapping = {}
    
    # Handle -e arguments
    if extract_args:
        for item in extract_args:
            if "=" in item:
                name, selector = item.split("=", 1)
                mapping[name.strip()] = selector.strip()
    
    # Handle positional selectors
    if selectors:
        for item in selectors:
            if "=" in item:
                name, selector = item.split("=", 1)
                mapping[name.strip()] = selector.strip()
            else:
                # Use selector as both name and selector
                mapping[item] = item

    return mapping


def _extract_data(result: Any, args: argparse.Namespace) -> Any:
    """Extract data from result based on arguments."""
    if args.text:
        return result.plain_text

    if args.links:
        return result.links()

    if args.images:
        return result.images()

    if args.meta:
        return result.meta()

    # Get selectors from both -e and positional args
    mapping = _parse_extractions(
        getattr(args, 'extract_args', None),
        getattr(args, 'selectors', None)
    )

    if not mapping:
        # Default: return raw HTML
        return result.text

    # Use XPath or CSS based on flag
    stype = "xpath" if args.xpath_mode else "css"

    if args.container:
        return result.extract_all(args.container, mapping, stype=stype)
    else:
        return result.extract(mapping, stype=stype)


def _output_result(data: Any, args: argparse.Namespace) -> None:
    """Output the extracted data."""
    output_format = args.format

    if output_format == "json":
        output = json.dumps(data, indent=2, ensure_ascii=False, default=str)
    elif output_format == "jsonl":
        if isinstance(data, list):
            output = "\n".join(json.dumps(item, ensure_ascii=False, default=str) for item in data)
        else:
            output = json.dumps(data, ensure_ascii=False, default=str)
    elif output_format == "csv":
        import csv
        import io

        if isinstance(data, list) and data and isinstance(data[0], dict):
            buffer = io.StringIO()
            writer = csv.DictWriter(buffer, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
            output = buffer.getvalue()
        elif isinstance(data, dict):
            buffer = io.StringIO()
            writer = csv.DictWriter(buffer, fieldnames=data.keys())
            writer.writeheader()
            writer.writerow(data)
            output = buffer.getvalue()
        else:
            output = str(data)
    else:  # text
        output = str(data)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            if args.verbose:
                print(f"Written to {args.output}", file=sys.stderr)
        except OSError as e:
            print(f"Error writing to {args.output}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output)


def run_cli(args: list[str] | None = None) -> int:
    """Run the CLI with given arguments.

    Parameters
    ----------
    args : list[str], optional
        Command-line arguments. If None, uses sys.argv.

    Returns
    -------
    int
        Exit code (0 for success).
    """
    parser = _create_argument_parser()
    parsed = parser.parse_args(args)

    if parsed.verbose:
        print(f"Scraping {parsed.url}...", file=sys.stderr)

    try:
        config = _build_config(parsed)
        result = scrape(parsed.url, config=config)

        data = _extract_data(result, parsed)
        _output_result(data, parsed)
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main() -> None:
    """Main entry point."""
    sys.exit(run_cli())


if __name__ == "__main__":
    main()
