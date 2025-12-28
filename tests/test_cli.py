"""Comprehensive tests for easyscrape.cli module."""

import argparse
import json
import os
import sys
import pytest
from unittest.mock import MagicMock, patch

from easyscrape.cli import (
    _create_argument_parser,
    _build_config,
    _extract_data,
    _output_result,
    main,
    run_cli,
)


# =============================================================================
# Argument Parser Tests
# =============================================================================

class TestArgumentParser:
    """Tests for argument parser creation."""

    def test_parser_creation(self):
        parser = _create_argument_parser()
        assert parser is not None
        assert parser.prog == "easyscrape"

    def test_parse_url(self):
        parser = _create_argument_parser()
        args = parser.parse_args(["https://example.com"])
        assert args.url == "https://example.com"

    def test_parse_extract(self):
        parser = _create_argument_parser()
        args = parser.parse_args(["https://example.com", "-e", "title=h1"])
        # -e goes to extract_args, not selectors
        assert args.extract_args is not None
        assert "title=h1" in args.extract_args

    def test_parse_multiple_extract(self):
        parser = _create_argument_parser()
        args = parser.parse_args([
            "https://example.com",
            "-e", "title=h1", "-e", "price=.price"
        ])
        assert len(args.extract_args) == 2

    def test_parse_output(self):
        parser = _create_argument_parser()
        args = parser.parse_args(["https://example.com", "-o", "out.json"])
        assert args.output == "out.json"

    def test_parse_format(self):
        parser = _create_argument_parser()
        args = parser.parse_args(["https://example.com", "-f", "csv"])
        assert args.format == "csv"

    def test_parse_format_default_json(self):
        parser = _create_argument_parser()
        args = parser.parse_args(["https://example.com"])
        assert args.format == "json"

    def test_parse_links(self):
        parser = _create_argument_parser()
        args = parser.parse_args(["https://example.com", "--links"])
        assert args.links is True

    def test_parse_images(self):
        parser = _create_argument_parser()
        args = parser.parse_args(["https://example.com", "--images"])
        assert args.images is True

    def test_parse_meta(self):
        parser = _create_argument_parser()
        args = parser.parse_args(["https://example.com", "--meta"])
        assert args.meta is True

    def test_parse_text(self):
        parser = _create_argument_parser()
        args = parser.parse_args(["https://example.com", "--text"])
        assert args.text is True

    def test_parse_timeout(self):
        parser = _create_argument_parser()
        args = parser.parse_args(["https://example.com", "--timeout", "60"])
        assert args.timeout == 60.0

    def test_parse_timeout_default(self):
        parser = _create_argument_parser()
        args = parser.parse_args(["https://example.com"])
        assert args.timeout == 30

    def test_parse_js(self):
        parser = _create_argument_parser()
        args = parser.parse_args(["https://example.com", "--js"])
        assert args.js is True

    def test_parse_no_cache(self):
        parser = _create_argument_parser()
        args = parser.parse_args(["https://example.com", "--no-cache"])
        assert args.no_cache is True

    def test_parse_xpath_mode(self):
        parser = _create_argument_parser()
        args = parser.parse_args(["https://example.com", "-x"])
        assert args.xpath_mode is True

    def test_parse_container(self):
        parser = _create_argument_parser()
        args = parser.parse_args(["https://example.com", "-c", ".product"])
        assert args.container == ".product"

    def test_parse_user_agent(self):
        parser = _create_argument_parser()
        args = parser.parse_args(["https://example.com", "--user-agent", "MyBot/1.0"])
        assert args.user_agent == "MyBot/1.0"

    def test_parse_proxy(self):
        parser = _create_argument_parser()
        args = parser.parse_args(["https://example.com", "--proxy", "http://proxy:8080"])
        assert args.proxy == "http://proxy:8080"


# =============================================================================
# Build Config Tests
# =============================================================================

class TestBuildConfig:
    """Tests for _build_config function."""

    def test_basic_config(self):
        parser = _create_argument_parser()
        args = parser.parse_args(["https://example.com"])
        cfg = _build_config(args)
        
        assert cfg.timeout == 30
        assert cfg.cache_enabled is True
        assert cfg.javascript is False

    def test_config_timeout(self):
        parser = _create_argument_parser()
        args = parser.parse_args(["https://example.com", "--timeout", "60"])
        cfg = _build_config(args)
        
        assert cfg.timeout == 60

    def test_config_no_cache(self):
        parser = _create_argument_parser()
        args = parser.parse_args(["https://example.com", "--no-cache"])
        cfg = _build_config(args)
        
        assert cfg.cache_enabled is False

    def test_config_js(self):
        parser = _create_argument_parser()
        args = parser.parse_args(["https://example.com", "--js"])
        cfg = _build_config(args)
        
        assert cfg.javascript is True

    def test_config_user_agent(self):
        parser = _create_argument_parser()
        args = parser.parse_args(["https://example.com", "--user-agent", "CustomBot"])
        cfg = _build_config(args)
        
        assert cfg.headers["User-Agent"] == "CustomBot"
        assert cfg.rotate_ua is False

    def test_config_proxy(self):
        parser = _create_argument_parser()
        args = parser.parse_args(["https://example.com", "--proxy", "http://proxy:8080"])
        cfg = _build_config(args)
        
        assert "http://proxy:8080" in cfg.proxies


# =============================================================================
# Extract Data Tests
# =============================================================================

class TestExtractData:
    """Tests for _extract_data function."""

    def test_extract_text(self):
        result = MagicMock()
        result.plain_text = "Hello World"
        
        args = argparse.Namespace(
            text=True, links=False, images=False, meta=False,
            selectors=None, extract_args=None, container=None, xpath_mode=False
        )
        
        output = _extract_data(result, args)
        assert output == "Hello World"

    def test_extract_links(self):
        result = MagicMock()
        result.links.return_value = ["https://a.com", "https://b.com"]
        
        args = argparse.Namespace(
            text=False, links=True, images=False, meta=False,
            selectors=None, extract_args=None, container=None, xpath_mode=False
        )
        
        output = _extract_data(result, args)
        assert output == ["https://a.com", "https://b.com"]

    def test_extract_images(self):
        result = MagicMock()
        result.images.return_value = ["img1.jpg", "img2.png"]
        
        args = argparse.Namespace(
            text=False, links=False, images=True, meta=False,
            selectors=None, extract_args=None, container=None, xpath_mode=False
        )
        
        output = _extract_data(result, args)
        assert output == ["img1.jpg", "img2.png"]

    def test_extract_meta(self):
        result = MagicMock()
        result.meta.return_value = {"description": "A page", "keywords": "test"}
        
        args = argparse.Namespace(
            text=False, links=False, images=False, meta=True,
            selectors=None, extract_args=None, container=None, xpath_mode=False
        )
        
        output = _extract_data(result, args)
        assert output["description"] == "A page"

    def test_extract_selectors(self):
        result = MagicMock()
        result.extract.return_value = {"title": "Hello", "price": "$99"}
        
        args = argparse.Namespace(
            text=False, links=False, images=False, meta=False,
            selectors=["title=h1", "price=.price"],
            extract_args=None,
            container=None, xpath_mode=False
        )
        
        output = _extract_data(result, args)
        result.extract.assert_called_once()
        assert output["title"] == "Hello"

    def test_extract_selectors_with_container(self):
        result = MagicMock()
        result.extract_all.return_value = [{"name": "A"}, {"name": "B"}]
        
        args = argparse.Namespace(
            text=False, links=False, images=False, meta=False,
            selectors=["name=.name"],
            extract_args=None,
            container=".product", xpath_mode=False
        )
        
        output = _extract_data(result, args)
        result.extract_all.assert_called_once()
        assert len(output) == 2

    def test_extract_selectors_xpath(self):
        result = MagicMock()
        result.extract.return_value = {"title": "XPath Result"}
        
        args = argparse.Namespace(
            text=False, links=False, images=False, meta=False,
            selectors=["title=//h1"],
            extract_args=None,
            container=None, xpath_mode=True
        )
        
        output = _extract_data(result, args)
        # The implementation uses keyword arg stype='xpath'
        result.extract.assert_called_with({"title": "//h1"}, stype="xpath")

    def test_extract_default_html(self):
        result = MagicMock()
        result.text = "<html><body>Hello</body></html>"
        
        args = argparse.Namespace(
            text=False, links=False, images=False, meta=False,
            selectors=None, extract_args=None, container=None, xpath_mode=False
        )
        
        output = _extract_data(result, args)
        assert output == "<html><body>Hello</body></html>"


# =============================================================================
# Output Result Tests
# =============================================================================

class TestOutputResult:
    """Tests for _output_result function."""

    def test_output_dict_to_stdout(self):
        args = argparse.Namespace(output=None, format="json", verbose=False)
        
        with patch.object(sys, 'stdout') as mock_stdout:
            mock_stdout.write = MagicMock()
            _output_result({"key": "value"}, args)
            mock_stdout.write.assert_called()

    def test_output_list_to_stdout(self):
        args = argparse.Namespace(output=None, format="json", verbose=False)
        
        with patch.object(sys, 'stdout') as mock_stdout:
            mock_stdout.write = MagicMock()
            _output_result(["a", "b", "c"], args)
            mock_stdout.write.assert_called()

    def test_output_string_to_stdout(self):
        args = argparse.Namespace(output=None, format="text", verbose=False)
        
        with patch.object(sys, 'stdout') as mock_stdout:
            mock_stdout.write = MagicMock()
            _output_result("Hello World", args)
            calls = [str(c) for c in mock_stdout.write.call_args_list]
            assert any("Hello World" in c for c in calls)

    def test_output_json_to_file(self, tmp_path):
        path = str(tmp_path / "test_output.json")
        
        args = argparse.Namespace(output=path, format="json", verbose=False)
        _output_result({"key": "value"}, args)
        
        with open(path, "r") as f:
            data = json.load(f)
        assert data["key"] == "value"

    def test_output_csv_to_file(self, tmp_path):
        path = str(tmp_path / "test_output.csv")
        
        args = argparse.Namespace(output=path, format="csv", verbose=False)
        _output_result([{"name": "A", "val": 1}, {"name": "B", "val": 2}], args)
        
        with open(path, "r") as f:
            content = f.read()
        assert "name" in content

    def test_output_text_to_file(self, tmp_path):
        path = str(tmp_path / "test_output.txt")
        
        args = argparse.Namespace(output=path, format="text", verbose=False)
        _output_result("Hello World", args)
        
        with open(path, "r") as f:
            content = f.read()
        assert "Hello World" in content

    def test_output_string_json_to_file(self, tmp_path):
        path = str(tmp_path / "test_output2.json")
        
        args = argparse.Namespace(output=path, format="json", verbose=False)
        _output_result("<html></html>", args)
        
        with open(path, "r") as f:
            content = f.read()
        assert "<html></html>" in content

    def test_output_io_error(self):
        args = argparse.Namespace(output="/nonexistent/path/file.txt", format="text", verbose=False)
        
        with pytest.raises(SystemExit) as exc_info:
            _output_result("data", args)
        assert exc_info.value.code == 1


# =============================================================================
# Main Function Tests
# =============================================================================

class TestMain:
    """Tests for main entry point."""

    @patch('easyscrape.cli.scrape')
    @patch.object(sys, 'argv', ['easyscrape', 'https://example.com', '--text'])
    def test_main_success(self, mock_scrape):
        result = MagicMock()
        result.plain_text = "Hello World"
        mock_scrape.return_value = result
        
        with patch.object(sys, 'stdout') as mock_stdout:
            mock_stdout.write = MagicMock()
            # main() calls sys.exit, so catch it
            with pytest.raises(SystemExit) as exc_info:
                main()
            # Exit code 0 means success
            assert exc_info.value.code == 0

    @patch('easyscrape.cli.scrape')
    @patch.object(sys, 'argv', ['easyscrape', 'https://example.com', '--links'])
    def test_main_extract_links(self, mock_scrape):
        result = MagicMock()
        result.links.return_value = ["https://a.com"]
        mock_scrape.return_value = result
        
        with patch.object(sys, 'stdout') as mock_stdout:
            mock_stdout.write = MagicMock()
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    @patch('easyscrape.cli.scrape')
    @patch.object(sys, 'argv', ['easyscrape', 'https://example.com'])
    def test_main_scrape_error(self, mock_scrape):
        mock_scrape.side_effect = Exception("Network error")
        
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1



class TestCliEdgeCases:
    """Edge case tests for CLI module."""
    
    def test_cli_main_exists(self):
        """Test main function exists."""
        from easyscrape.cli import main
        assert main is not None
    
    def test_build_config_exists(self):
        """Test _build_config function exists."""
        from easyscrape.cli import _build_config
        assert _build_config is not None
