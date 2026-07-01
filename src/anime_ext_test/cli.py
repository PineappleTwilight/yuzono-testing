"""CLI entry point for the anime extensions testing suite."""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from anime_ext_test.config import Config
from anime_ext_test.models import RunSummary
from anime_ext_test.report.html_report import write_html_report
from anime_ext_test.report.json_report import write_json_report, write_summary_json
from anime_ext_test.report.markdown_report import write_markdown_report
from anime_ext_test.report.summary import compute_summary
from anime_ext_test.runner import run_all_tests


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="anime-ext-test",
        description="Automated testing suite for anime-extensions",
    )

    # Repository options
    repo_grp = parser.add_argument_group("Repository")
    repo_grp.add_argument(
        "--repo-url",
        default="https://github.com/yuzono/anime-extensions.git",
        help="Git repository URL to clone (default: yuzono/anime-extensions)",
    )
    repo_grp.add_argument(
        "--repo-branch",
        default="master",
        help="Branch to clone (default: master)",
    )
    repo_grp.add_argument(
        "--no-clone",
        action="store_true",
        help="Skip cloning; use --repo-dir instead",
    )
    repo_grp.add_argument(
        "--repo-dir",
        default="",
        help="Path to local repo (used with --no-clone or as clone target)",
    )

    # Filtering options
    filter_grp = parser.add_argument_group("Filtering")
    filter_grp.add_argument(
        "--languages",
        nargs="*",
        default=[],
        help="Only test extensions for these languages (e.g. en ja all)",
    )
    filter_grp.add_argument(
        "--extensions",
        nargs="*",
        default=[],
        help="Only test these extension names or module IDs (e.g. animepahe en.animepahe)",
    )
    filter_grp.add_argument(
        "--categories",
        nargs="*",
        default=[],
        dest="test_categories",
        help="Only run these test categories (e.g. structural connectivity popular)",
    )

    # HTTP options
    http_grp = parser.add_argument_group("HTTP")
    http_grp.add_argument("--timeout", type=float, default=30.0, help="Per-request timeout in seconds")
    http_grp.add_argument("--connect-timeout", type=float, default=15.0, help="Connect timeout in seconds")
    http_grp.add_argument("--max-concurrent", type=int, default=20, help="Max concurrent HTTP requests")

    # Output options
    out_grp = parser.add_argument_group("Output")
    out_grp.add_argument(
        "--output-dir",
        default="./reports",
        help="Directory to write report files (default: ./reports)",
    )
    out_grp.add_argument(
        "--format",
        choices=["json", "markdown", "html", "both", "all"],
        default="both",
        dest="report_format",
        help="Report format: json, markdown, html, both (json+markdown), "
             "all (json+markdown+html) (default: both)",
    )

    # Misc
    parser.add_argument("--include-api-key", action="store_true", help="Include extensions requiring API keys")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Increase log verbosity")

    return parser


def setup_logging(verbosity: int) -> None:
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    setup_logging(args.verbose)
    logger = logging.getLogger("anime_ext_test")

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

    logger.info("Starting test run with config: %s", config)

    # Run the async test suite
    report = asyncio.run(run_all_tests(config))

    # Compute summary
    summary = compute_summary(report)

    # Write reports
    output_dir = Path(config.output_dir)
    fmt = config.report_format

    if fmt in ("json", "both", "all"):
        json_path = write_json_report(report, output_dir)
        summary_path = write_summary_json(summary, report, output_dir)
        logger.info("JSON report: %s", json_path)
        logger.info("JSON summary: %s", summary_path)

    if fmt in ("markdown", "both", "all"):
        md_path = write_markdown_report(report, summary, output_dir)
        logger.info("Markdown report: %s", md_path)

    if fmt in ("html", "all"):
        html_path = write_html_report(report, summary, output_dir)
        logger.info("HTML report: %s", html_path)

    # Print console summary
    _print_summary(summary)

    # Exit code: 1 if any failures, 0 otherwise
    return 1 if summary.failed > 0 else 0


def _print_summary(summary: RunSummary) -> None:
    print("\n" + "=" * 60)
    print("  ANIME EXTENSIONS TEST SUMMARY")
    print("=" * 60)
    print(f"  Extensions:  {summary.total_extensions}")
    print(f"  Assertions:  {summary.total_tests}")
    print(f"  ✅ Passed:    {summary.passed}")
    print(f"  ❌ Failed:    {summary.failed}")
    print(f"  ⏭  Skipped:   {summary.skipped}")
    print(f"  ⚠  Errors:    {summary.errors}")
    print(f"  Duration:    {summary.duration_seconds}s")
    print("=" * 60)
    if summary.by_language:
        print("\n  By Language:")
        for lang in sorted(summary.by_language):
            s = summary.by_language[lang]
            print(f"    {lang}: {s['passed']}p/{s['failed']}f/{s['skipped']}s/{s['errors']}e")
    if summary.by_test_type:
        print("\n  By Category:")
        for cat in sorted(summary.by_test_type):
            s = summary.by_test_type[cat]
            print(f"    {cat}: {s['passed']}p/{s['failed']}f/{s['skipped']}s/{s['errors']}e")
    print()
