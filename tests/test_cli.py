"""Unit tests for CLI argument parsing, Config construction, and logging setup."""

from __future__ import annotations

import logging

import pytest

from anime_ext_test.cli import build_parser, main, setup_logging
from anime_ext_test.config import Config


class TestBuildParser:
    """Verify the argument parser produces correct namespace objects."""

    def test_defaults(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.repo_url == "https://github.com/yuzono/anime-extensions.git"
        assert args.repo_branch == "master"
        assert args.no_clone is False
        assert args.repo_dir == ""
        assert args.languages == []
        assert args.extensions == []
        assert args.test_categories == []
        assert args.timeout == 30.0
        assert args.connect_timeout == 15.0
        assert args.max_concurrent == 20
        assert args.output_dir == "./reports"
        assert args.report_format == "both"
        assert args.include_api_key is False
        assert args.verbose == 0

    def test_custom_repo_url(self):
        parser = build_parser()
        args = parser.parse_args(["--repo-url", "https://example.com/repo.git"])
        assert args.repo_url == "https://example.com/repo.git"

    def test_no_clone_flag(self):
        parser = build_parser()
        args = parser.parse_args(["--no-clone", "--repo-dir", "/tmp/repo"])
        assert args.no_clone is True
        assert args.repo_dir == "/tmp/repo"

    def test_languages_flag(self):
        parser = build_parser()
        args = parser.parse_args(["--languages", "en", "tr", "ja"])
        assert args.languages == ["en", "tr", "ja"]

    def test_extensions_flag(self):
        parser = build_parser()
        args = parser.parse_args(["--extensions", "animepahe", "en.gogoanime"])
        assert args.extensions == ["animepahe", "en.gogoanime"]

    def test_categories_flag_maps_to_test_categories(self):
        parser = build_parser()
        args = parser.parse_args(["--categories", "structural", "connectivity"])
        assert args.test_categories == ["structural", "connectivity"]

    def test_timeout_flags(self):
        parser = build_parser()
        args = parser.parse_args(["--timeout", "60", "--connect-timeout", "30"])
        assert args.timeout == 60.0
        assert args.connect_timeout == 30.0

    def test_max_concurrent_flag(self):
        parser = build_parser()
        args = parser.parse_args(["--max-concurrent", "50"])
        assert args.max_concurrent == 50

    def test_output_dir_flag(self):
        parser = build_parser()
        args = parser.parse_args(["--output-dir", "/tmp/reports"])
        assert args.output_dir == "/tmp/reports"

    def test_format_choices(self):
        parser = build_parser()
        for choice in ["json", "markdown", "html", "both", "all"]:
            args = parser.parse_args(["--format", choice])
            assert args.report_format == choice

    def test_format_invalid(self):
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--format", "xml"])

    def test_verbose_single(self):
        parser = build_parser()
        args = parser.parse_args(["-v"])
        assert args.verbose == 1

    def test_verbose_double(self):
        parser = build_parser()
        args = parser.parse_args(["-vv"])
        assert args.verbose == 2

    def test_include_api_key_flag(self):
        parser = build_parser()
        args = parser.parse_args(["--include-api-key"])
        assert args.include_api_key is True

    def test_composite_args(self):
        parser = build_parser()
        args = parser.parse_args([
            "--languages", "en",
            "--categories", "structural",
            "--format", "all",
            "--max-concurrent", "10",
            "-vv",
        ])
        assert args.languages == ["en"]
        assert args.test_categories == ["structural"]
        assert args.report_format == "all"
        assert args.max_concurrent == 10
        assert args.verbose == 2


class TestSetupLogging:
    """Verify logging level mapping from verbosity counter."""

    def test_default_warning(self):
        setup_logging(0)
        assert logging.getLogger().level == logging.WARNING

    def test_verbose_info(self):
        setup_logging(1)
        assert logging.getLogger().level == logging.INFO

    def test_double_verbose_debug(self):
        setup_logging(2)
        assert logging.getLogger().level == logging.DEBUG

    def test_triple_verbose_still_debug(self):
        setup_logging(3)
        assert logging.getLogger().level == logging.DEBUG


class TestConfigConstructionFromArgs:
    """Verify Config is correctly built from parsed args (no actual test run)."""

    def test_config_from_defaults(self):
        parser = build_parser()
        args = parser.parse_args([])
        config = Config(
            repo_url=args.repo_url,
            repo_branch=args.repo_branch,
            no_clone=args.no_clone,
            repo_dir=args.repo_dir,
            languages=args.languages,
            extensions=args.extensions,
            test_categories=args.test_categories or [
                "structural", "connectivity", "popular",
                "search", "details", "episodes", "latest", "filters",
                "series_details", "episode_list", "video_streams",
                "pagination", "post_search",
            ],
            http_timeout=args.timeout,
            http_connect_timeout=args.connect_timeout,
            max_concurrent=args.max_concurrent,
            output_dir=args.output_dir,
            report_format=args.report_format,
            skip_api_key_extensions=not args.include_api_key,
        )
        assert config.repo_url == "https://github.com/yuzono/anime-extensions.git"
        assert config.report_format == "both"
        assert config.skip_api_key_extensions is True
        assert config.max_concurrent == 20

    def test_config_from_custom_args(self):
        parser = build_parser()
        args = parser.parse_args([
            "--languages", "en",
            "--format", "html",
            "--max-concurrent", "10",
            "--include-api-key",
        ])
        config = Config(
            repo_url=args.repo_url,
            repo_branch=args.repo_branch,
            no_clone=args.no_clone,
            repo_dir=args.repo_dir,
            languages=args.languages,
            extensions=args.extensions,
            test_categories=args.test_categories or [
                "structural", "connectivity", "popular",
                "search", "details", "episodes", "latest", "filters",
                "series_details", "episode_list", "video_streams",
                "pagination", "post_search",
            ],
            http_timeout=args.timeout,
            http_connect_timeout=args.connect_timeout,
            max_concurrent=args.max_concurrent,
            output_dir=args.output_dir,
            report_format=args.report_format,
            skip_api_key_extensions=not args.include_api_key,
        )
        assert config.languages == ["en"]
        assert config.report_format == "html"
        assert config.max_concurrent == 10
        assert config.skip_api_key_extensions is False


class TestMainExitCode:
    """main() should not actually run tests (network-dependent), but we can
    verify it correctly instantiates the parser without running."""

    def test_main_with_help_exits(self):
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0
