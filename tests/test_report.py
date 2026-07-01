"""Unit tests for report generation — expanded with HTML report tests and edge cases."""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from anime_ext_test.models import (
    ExtensionMeta,
    ExtensionReport,
    RunReport,
    RunSummary,
    TestResult,
)
from anime_ext_test.report.html_report import write_html_report
from anime_ext_test.report.json_report import write_json_report, write_summary_json
from anime_ext_test.report.markdown_report import write_markdown_report
from anime_ext_test.report.summary import compute_summary


def _ext(
    lang: str = "en",
    name: str = "allanime",
    ext_name: str = "AllAnime",
    ext_class: str = ".AllAnime",
    ext_version_code: int = 55,
    base_url: str = "https://allanime.com",
    theme_pkg: str | None = None,
    is_nsfw: bool = False,
) -> ExtensionMeta:
    return ExtensionMeta(
        lang=lang,
        name=name,
        ext_name=ext_name,
        ext_class=ext_class,
        ext_version_code=ext_version_code,
        base_url=base_url,
        theme_pkg=theme_pkg,
        is_nsfw=is_nsfw,
    )


def _make_report() -> tuple[RunReport, RunSummary]:
    ext = _ext()
    report = RunReport(
        run_id="testrun01",
        started_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
        finished_at=datetime(2026, 1, 1, 0, 10, 0, tzinfo=UTC),
        repo_url="https://github.com/yuzono/anime-extensions.git",
        repo_commit="abc1234",
        extensions=[
            ExtensionReport(extension=ext, results=[
                TestResult(
                    test_name="structural:ext_name_present",
                    status="pass",
                    duration_ms=5.0,
                    message="extName='AllAnime'",
                ),
                TestResult(
                    test_name="structural:ext_class_format",
                    status="pass",
                    duration_ms=2.0,
                    message="extClass='.AllAnime'",
                ),
                TestResult(
                    test_name="connectivity:base_url_reachable",
                    status="pass",
                    duration_ms=150.0,
                    message="HTTP 200",
                ),
                TestResult(
                    test_name="popular:popular_page_load",
                    status="fail",
                    duration_ms=300.0,
                    message="HTTP 404",
                    detail="Not found",
                ),
                TestResult(
                    test_name="search:search_page_load",
                    status="skip",
                    duration_ms=0,
                    message="No search endpoint",
                ),
            ]),
        ],
    )
    summary = compute_summary(report)
    return report, summary


def _make_all_pass_report() -> tuple[RunReport, RunSummary]:
    ext = _ext()
    report = RunReport(
        run_id="allpass01",
        started_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
        finished_at=datetime(2026, 1, 1, 0, 5, 0, tzinfo=UTC),
        extensions=[
            ExtensionReport(extension=ext, results=[
                TestResult(test_name="structural:x", status="pass", duration_ms=5.0),
                TestResult(test_name="structural:y", status="pass", duration_ms=3.0),
            ]),
        ],
    )
    return report, compute_summary(report)


def _make_all_fail_report() -> tuple[RunReport, RunSummary]:
    ext = _ext()
    report = RunReport(
        run_id="allfail01",
        started_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
        finished_at=datetime(2026, 1, 1, 0, 5, 0, tzinfo=UTC),
        extensions=[
            ExtensionReport(extension=ext, results=[
                TestResult(test_name="structural:x", status="fail", duration_ms=5.0, message="broken", detail="err"),
                TestResult(test_name="structural:y", status="error", duration_ms=3.0, message="timeout"),
            ]),
        ],
    )
    return report, compute_summary(report)


def _make_empty_report() -> tuple[RunReport, RunSummary]:
    report = RunReport(
        run_id="empty01",
        started_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
        finished_at=datetime(2026, 1, 1, 0, 0, 1, tzinfo=UTC),
        extensions=[],
    )
    return report, compute_summary(report)


class TestJsonReport:
    def test_write_json_report(self):
        report, summary = _make_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = write_json_report(report, Path(tmpdir))
            assert out_path.exists()
            data = json.loads(out_path.read_text())
            assert data["run_id"] == "testrun01"
            assert len(data["extensions"]) == 1

    def test_write_summary_json(self):
        report, summary = _make_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = write_summary_json(summary, report, Path(tmpdir))
            assert out_path.exists()
            data = json.loads(out_path.read_text())
            assert data["total_extensions"] == 1
            assert data["passed"] == 3
            assert data["failed"] == 1

    def test_json_report_empty_extensions(self):
        report, summary = _make_empty_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = write_json_report(report, Path(tmpdir))
            data = json.loads(out_path.read_text())
            assert data["extensions"] == []

    def test_json_report_contains_results(self):
        report, summary = _make_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = write_json_report(report, Path(tmpdir))
            data = json.loads(out_path.read_text())
            results = data["extensions"][0]["results"]
            assert len(results) == 5

    def test_summary_json_has_by_language(self):
        report, summary = _make_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = write_summary_json(summary, report, Path(tmpdir))
            data = json.loads(out_path.read_text())
            assert "by_language" in data
            assert "en" in data["by_language"]


class TestMarkdownReport:
    def test_write_markdown_report(self):
        report, summary = _make_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = write_markdown_report(report, summary, Path(tmpdir))
            assert out_path.exists()
            content = out_path.read_text()
            assert "# Anime Extensions Test Report" in content
            assert "AllAnime" in content
            assert "Failed Extensions" in content
            assert "popular:popular_page_load" in content

    def test_markdown_has_language_table(self):
        report, summary = _make_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = write_markdown_report(report, summary, Path(tmpdir))
            content = out_path.read_text()
            assert "By Language" in content
            assert "en" in content

    def test_markdown_has_category_table(self):
        report, summary = _make_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = write_markdown_report(report, summary, Path(tmpdir))
            content = out_path.read_text()
            assert "By Test Category" in content

    def test_markdown_all_pass_no_failed_section(self):
        report, summary = _make_all_pass_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = write_markdown_report(report, summary, Path(tmpdir))
            content = out_path.read_text()
            assert "Failed Extensions" not in content

    def test_markdown_empty_report(self):
        report, summary = _make_empty_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = write_markdown_report(report, summary, Path(tmpdir))
            content = out_path.read_text()
            assert "0" in content

    def test_markdown_shows_extension_meta(self):
        report, summary = _make_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = write_markdown_report(report, summary, Path(tmpdir))
            content = out_path.read_text()
            assert "Lang:" in content
            assert "Theme:" in content
            assert "baseUrl:" in content


class TestHtmlReport:
    def test_write_html_report(self):
        report, summary = _make_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = write_html_report(report, summary, Path(tmpdir))
            assert out_path.exists()
            content = out_path.read_text()
            assert "<!DOCTYPE html>" in content
            assert "testrun01" in content

    def test_html_contains_summary_cards(self):
        report, summary = _make_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = write_html_report(report, summary, Path(tmpdir))
            content = out_path.read_text()
            assert "summary-card" in content
            assert "Extensions" in content
            assert "Passed" in content
            assert "Failed" in content

    def test_html_contains_category_breakdown(self):
        report, summary = _make_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = write_html_report(report, summary, Path(tmpdir))
            content = out_path.read_text()
            assert "By Category" in content

    def test_html_contains_language_breakdown(self):
        report, summary = _make_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = write_html_report(report, summary, Path(tmpdir))
            content = out_path.read_text()
            assert "By Language" in content

    def test_html_contains_extension_cards(self):
        report, summary = _make_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = write_html_report(report, summary, Path(tmpdir))
            content = out_path.read_text()
            assert "ext-card" in content
            assert "en.allanime" in content

    def test_html_contains_filter_toolbar(self):
        report, summary = _make_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = write_html_report(report, summary, Path(tmpdir))
            content = out_path.read_text()
            assert "filter-btn" in content
            assert "Failed" in content
            assert "Clean" in content

    def test_html_contains_javascript(self):
        report, summary = _make_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = write_html_report(report, summary, Path(tmpdir))
            content = out_path.read_text()
            assert "<script>" in content
            assert "filterExtensions" in content
            assert "toggleCard" in content

    def test_html_self_contained_no_external_deps(self):
        report, summary = _make_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = write_html_report(report, summary, Path(tmpdir))
            content = out_path.read_text()
            assert '<link rel="stylesheet"' not in content
            assert '<script src=' not in content

    def test_html_health_dot_colors(self):
        report, summary = _make_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = write_html_report(report, summary, Path(tmpdir))
            content = out_path.read_text()
            assert "health-dot" in content

    def test_html_empty_report(self):
        report, summary = _make_empty_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = write_html_report(report, summary, Path(tmpdir))
            content = out_path.read_text()
            assert "<!DOCTYPE html>" in content

    def test_html_all_pass_report(self):
        report, summary = _make_all_pass_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = write_html_report(report, summary, Path(tmpdir))
            content = out_path.read_text()
            assert "&#x2705;" in content

    def test_html_all_fail_report(self):
        report, summary = _make_all_fail_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = write_html_report(report, summary, Path(tmpdir))
            content = out_path.read_text()
            assert "&#x274C;" in content

    def test_html_escapes_special_characters(self):
        """XSS protection: special chars in ext_name must be escaped."""
        ext = _ext(ext_name="<script>alert('xss')</script>")
        report = RunReport(
            run_id="xss01",
            extensions=[
                ExtensionReport(extension=ext, results=[
                    TestResult(test_name="t", status="pass"),
                ]),
            ],
        )
        summary = compute_summary(report)
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = write_html_report(report, summary, Path(tmpdir))
            content = out_path.read_text()
            assert "<script>alert" not in content
            assert "<script>" in content

    def test_html_multisrc_extension_shows_theme(self):
        ext = _ext(theme_pkg="dopeflix")
        report = RunReport(
            run_id="theme01",
            extensions=[
                ExtensionReport(extension=ext, results=[
                    TestResult(test_name="t", status="pass"),
                ]),
            ],
        )
        summary = compute_summary(report)
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = write_html_report(report, summary, Path(tmpdir))
            content = out_path.read_text()
            assert "dopeflix" in content

    def test_html_nsfw_extension_shows_flag(self):
        ext = _ext(is_nsfw=True)
        report = RunReport(
            run_id="nsfw01",
            extensions=[
                ExtensionReport(extension=ext, results=[
                    TestResult(test_name="t", status="pass"),
                ]),
            ],
        )
        summary = compute_summary(report)
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = write_html_report(report, summary, Path(tmpdir))
            content = out_path.read_text()
            assert "NSFW: True" in content

    def test_html_report_output_path(self):
        report, summary = _make_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = write_html_report(report, summary, Path(tmpdir))
            assert out_path.name == f"report-{report.run_id}.html"

    def test_html_creates_output_dir(self):
        report, summary = _make_report()
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = Path(tmpdir) / "nested" / "dir"
            out_path = write_html_report(report, summary, nested)
            assert out_path.exists()


class TestComputeSummary:
    def test_summary_counts(self):
        report, summary = _make_report()
        assert summary.total_extensions == 1
        assert summary.total_tests == 5
        assert summary.passed == 3
        assert summary.failed == 1
        assert summary.skipped == 1
        assert summary.errors == 0

    def test_summary_by_language(self):
        report, summary = _make_report()
        assert "en" in summary.by_language
        en_stats = summary.by_language["en"]
        assert en_stats["passed"] == 3
        assert en_stats["failed"] == 1

    def test_summary_by_test_type(self):
        report, summary = _make_report()
        assert "structural" in summary.by_test_type
        assert "connectivity" in summary.by_test_type
        assert "popular" in summary.by_test_type

    def test_summary_empty_report(self):
        report, summary = _make_empty_report()
        assert summary.total_extensions == 0
        assert summary.total_tests == 0
        assert summary.passed == 0
        assert summary.duration_seconds == 1.0

    def test_summary_all_pass(self):
        report, summary = _make_all_pass_report()
        assert summary.passed == 2
        assert summary.failed == 0

    def test_summary_all_fail(self):
        report, summary = _make_all_fail_report()
        assert summary.failed == 1
        assert summary.errors == 1
