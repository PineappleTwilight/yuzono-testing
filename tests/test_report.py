"""Unit tests for report generation."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path

from anime_ext_test.models import (
    ExtensionMeta,
    ExtensionReport,
    RunReport,
    RunSummary,
    TestResult,
)
from anime_ext_test.report.json_report import write_json_report, write_summary_json
from anime_ext_test.report.markdown_report import write_markdown_report
from anime_ext_test.report.summary import compute_summary


def _make_report() -> tuple[RunReport, RunSummary]:
    ext = ExtensionMeta(
        lang="en",
        name="allanime",
        ext_name="AllAnime",
        ext_class=".AllAnime",
        ext_version_code=55,
        base_url="https://allanime.com",
    )
    report = RunReport(
        run_id="testrun01",
        started_at=datetime(2026, 1, 1, 0, 0, 0),
        finished_at=datetime(2026, 1, 1, 0, 10, 0),
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
