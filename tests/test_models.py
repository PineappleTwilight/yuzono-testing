"""Unit tests for Pydantic data models — expanded with edge cases."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from anime_ext_test.models import ExtensionMeta, ExtensionReport, RunReport, RunSummary, TestResult


class TestExtensionMeta:
    def test_basic_creation(self):
        ext = ExtensionMeta(
            lang="en", name="allanime", ext_name="AllAnime",
            ext_class=".AllAnime", ext_version_code=55,
        )
        assert ext.lang == "en"
        assert ext.name == "allanime"
        assert ext.ext_name == "AllAnime"
        assert ext.ext_class == ".AllAnime"
        assert ext.ext_version_code == 55

    def test_class_simple_name_auto(self):
        ext = ExtensionMeta(
            lang="en", name="allanime", ext_name="AllAnime",
            ext_class=".AllAnime", ext_version_code=55,
        )
        assert ext.class_simple_name == "AllAnime"

    def test_class_simple_name_explicit(self):
        ext = ExtensionMeta(
            lang="en", name="allanime", ext_name="AllAnime",
            ext_class=".AllAnime", ext_version_code=55,
            class_simple_name="CustomName",
        )
        assert ext.class_simple_name == "CustomName"

    def test_class_simple_name_no_leading_dot(self):
        """When ext_class has no dot, class_simple_name equals ext_class."""
        ext = ExtensionMeta(
            lang="en", name="test", ext_name="Test",
            ext_class="NoDotClass", ext_version_code=1,
        )
        assert ext.class_simple_name == "NoDotClass"

    def test_module_id(self):
        ext = ExtensionMeta(
            lang="en", name="allanime", ext_name="AllAnime",
            ext_class=".AllAnime", ext_version_code=55,
        )
        assert ext.module_id == "en.allanime"

    def test_module_id_different_lang(self):
        ext = ExtensionMeta(
            lang="tr", name="tranimeci", ext_name="TRAnimeCI",
            ext_class=".TRAnimeCI", ext_version_code=2,
        )
        assert ext.module_id == "tr.tranimeci"

    def test_is_multisrc_true(self):
        ext = ExtensionMeta(
            lang="tr", name="tranimeci", ext_name="TRAnimeCI",
            ext_class=".TRAnimeCI", ext_version_code=2,
            theme_pkg="animestream",
        )
        assert ext.is_multisrc is True

    def test_is_multisrc_false(self):
        ext = ExtensionMeta(
            lang="en", name="allanime", ext_name="AllAnime",
            ext_class=".AllAnime", ext_version_code=55,
        )
        assert ext.is_multisrc is False

    def test_default_base_url_empty(self):
        ext = ExtensionMeta(
            lang="en", name="a", ext_name="A", ext_class=".A", ext_version_code=1,
        )
        assert ext.base_url == ""

    def test_default_is_nsfw_false(self):
        ext = ExtensionMeta(
            lang="en", name="a", ext_name="A", ext_class=".A", ext_version_code=1,
        )
        assert ext.is_nsfw is False

    def test_default_requires_api_key_false(self):
        ext = ExtensionMeta(
            lang="en", name="a", ext_name="A", ext_class=".A", ext_version_code=1,
        )
        assert ext.requires_api_key is False

    def test_default_ext_factory_names_empty(self):
        ext = ExtensionMeta(
            lang="en", name="a", ext_name="A", ext_class=".A", ext_version_code=1,
        )
        assert ext.ext_factory_names == []

    def test_override_version_code_default(self):
        ext = ExtensionMeta(
            lang="en", name="a", ext_name="A", ext_class=".A", ext_version_code=1,
        )
        assert ext.override_version_code == 0

    def test_nsfw_extension(self):
        ext = ExtensionMeta(
            lang="zh", name="hanime1", ext_name="Hanime1.me",
            ext_class=".Hanime1", ext_version_code=6,
            is_nsfw=True,
        )
        assert ext.is_nsfw is True

    def test_factory_extension_with_names(self):
        ext = ExtensionMeta(
            lang="all", name="jellyfin", ext_name="Jellyfin",
            ext_class=".JellyfinFactory", ext_version_code=30,
            ext_factory_names=["Jellyfin (1)", "Jellyfin (2)", "Jellyfin (3)"],
        )
        assert len(ext.ext_factory_names) == 3
        assert "Jellyfin (1)" in ext.ext_factory_names

    def test_model_serialization_roundtrip(self):
        """ExtensionMeta should survive JSON serialization roundtrip."""
        ext = ExtensionMeta(
            lang="en", name="allanime", ext_name="AllAnime",
            ext_class=".AllAnime", ext_version_code=55,
            base_url="https://allanime.com", theme_pkg="dopeflix",
        )
        data = ext.model_dump()
        restored = ExtensionMeta.model_validate(data)
        assert restored.lang == ext.lang
        assert restored.module_id == ext.module_id
        assert restored.is_multisrc is True

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            ExtensionMeta(lang="en")  # type: ignore[call-arg]


class TestTestResult:
    def test_pass_result(self):
        r = TestResult(test_name="structural:ext_name", status="pass", duration_ms=5.0, message="OK")
        assert r.status == "pass"
        assert r.test_name == "structural:ext_name"

    def test_fail_result(self):
        r = TestResult(test_name="connectivity:base_url", status="fail", message="HTTP 404")
        assert r.status == "fail"

    def test_skip_result(self):
        r = TestResult(test_name="popular:page_load", status="skip", message="No baseUrl")
        assert r.status == "skip"

    def test_error_result(self):
        r = TestResult(test_name="search:search_timeout", status="error", message="Timeout 30s")
        assert r.status == "error"

    def test_default_duration_ms(self):
        r = TestResult(test_name="test", status="pass")
        assert r.duration_ms == 0.0

    def test_default_message_empty(self):
        r = TestResult(test_name="test", status="pass")
        assert r.message == ""

    def test_default_detail_empty(self):
        r = TestResult(test_name="test", status="pass")
        assert r.detail == ""

    def test_fail_with_detail(self):
        r = TestResult(
            test_name="structural:base_url_valid",
            status="fail",
            message="Invalid URL",
            detail="no scheme in 'example.com'",
        )
        assert r.detail == "no scheme in 'example.com'"

    def test_invalid_status_raises(self):
        with pytest.raises(ValidationError):
            TestResult(test_name="test", status="unknown")  # type: ignore[call-arg]

    def test_valid_statuses_only(self):
        """Only pass, fail, skip, error are valid status values."""
        for status in ("pass", "fail", "skip", "error"):
            r = TestResult(test_name="test", status=status)
            assert r.status == status


class TestExtensionReport:
    def test_pass_fail_counts(self):
        ext = ExtensionMeta(
            lang="en", name="allanime", ext_name="AllAnime",
            ext_class=".AllAnime", ext_version_code=55,
        )
        report = ExtensionReport(extension=ext, results=[
            TestResult(test_name="a", status="pass"),
            TestResult(test_name="b", status="pass"),
            TestResult(test_name="c", status="fail"),
            TestResult(test_name="d", status="skip"),
            TestResult(test_name="e", status="error"),
        ])
        assert report.passed == 2
        assert report.failed == 1
        assert report.skipped == 1
        assert report.errored == 1
        assert report.total == 5

    def test_empty_report_zero_counts(self):
        ext = ExtensionMeta(
            lang="en", name="a", ext_name="A", ext_class=".A", ext_version_code=1,
        )
        report = ExtensionReport(extension=ext, results=[])
        assert report.passed == 0
        assert report.failed == 0
        assert report.skipped == 0
        assert report.errored == 0
        assert report.total == 0

    def test_all_pass(self):
        ext = ExtensionMeta(
            lang="en", name="a", ext_name="A", ext_class=".A", ext_version_code=1,
        )
        report = ExtensionReport(extension=ext, results=[
            TestResult(test_name=f"test_{i}", status="pass") for i in range(5)
        ])
        assert report.passed == 5
        assert report.failed == 0

    def test_all_fail(self):
        ext = ExtensionMeta(
            lang="en", name="a", ext_name="A", ext_class=".A", ext_version_code=1,
        )
        report = ExtensionReport(extension=ext, results=[
            TestResult(test_name=f"test_{i}", status="fail") for i in range(3)
        ])
        assert report.failed == 3
        assert report.passed == 0

    def test_default_started_at(self):
        ext = ExtensionMeta(
            lang="en", name="a", ext_name="A", ext_class=".A", ext_version_code=1,
        )
        report = ExtensionReport(extension=ext)
        assert report.started_at is not None

    def test_default_finished_at_none(self):
        ext = ExtensionMeta(
            lang="en", name="a", ext_name="A", ext_class=".A", ext_version_code=1,
        )
        report = ExtensionReport(extension=ext)
        assert report.finished_at is None

    def test_default_results_empty(self):
        ext = ExtensionMeta(
            lang="en", name="a", ext_name="A", ext_class=".A", ext_version_code=1,
        )
        report = ExtensionReport(extension=ext)
        assert report.results == []


class TestRunReport:
    def test_basic_creation(self):
        report = RunReport(run_id="abc123")
        assert report.run_id == "abc123"
        assert report.extensions == []

    def test_default_started_at(self):
        report = RunReport(run_id="test")
        assert report.started_at is not None

    def test_default_finished_at_none(self):
        report = RunReport(run_id="test")
        assert report.finished_at is None

    def test_with_extensions(self):
        ext = ExtensionMeta(
            lang="en", name="a", ext_name="A", ext_class=".A", ext_version_code=1,
        )
        report = RunReport(
            run_id="test",
            extensions=[ExtensionReport(extension=ext)],
        )
        assert len(report.extensions) == 1

    def test_empty_extensions(self):
        report = RunReport(run_id="test", extensions=[])
        assert len(report.extensions) == 0


class TestRunSummary:
    def test_from_report(self):
        ext = ExtensionMeta(
            lang="en", name="allanime", ext_name="AllAnime",
            ext_class=".AllAnime", ext_version_code=55,
        )
        report = RunReport(
            run_id="test123",
            extensions=[
                ExtensionReport(extension=ext, results=[
                    TestResult(test_name="structural:a", status="pass"),
                    TestResult(test_name="structural:b", status="fail"),
                    TestResult(test_name="connectivity:c", status="skip"),
                ]),
            ],
        )
        summary = RunSummary.from_report(report)
        assert summary.total_extensions == 1
        assert summary.total_tests == 3
        assert summary.passed == 1
        assert summary.failed == 1
        assert summary.skipped == 1

    def test_from_report_zero_extensions(self):
        report = RunReport(
            run_id="empty",
            started_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
            finished_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
        )
        summary = RunSummary.from_report(report)
        assert summary.total_extensions == 0
        assert summary.total_tests == 0
        assert summary.passed == 0
        assert summary.failed == 0
        assert summary.duration_seconds == 0.0
        assert summary.by_language == {}
        assert summary.by_test_type == {}

    def test_from_report_all_pass(self):
        ext = ExtensionMeta(
            lang="en", name="a", ext_name="A", ext_class=".A", ext_version_code=1,
        )
        report = RunReport(
            run_id="allpass",
            extensions=[
                ExtensionReport(extension=ext, results=[
                    TestResult(test_name="structural:x", status="pass"),
                    TestResult(test_name="structural:y", status="pass"),
                ]),
            ],
        )
        summary = RunSummary.from_report(report)
        assert summary.passed == 2
        assert summary.failed == 0
        assert summary.skipped == 0
        assert summary.errors == 0

    def test_from_report_all_fail(self):
        ext = ExtensionMeta(
            lang="en", name="a", ext_name="A", ext_class=".A", ext_version_code=1,
        )
        report = RunReport(
            run_id="allfail",
            extensions=[
                ExtensionReport(extension=ext, results=[
                    TestResult(test_name="structural:x", status="fail"),
                    TestResult(test_name="structural:y", status="fail"),
                ]),
            ],
        )
        summary = RunSummary.from_report(report)
        assert summary.failed == 2
        assert summary.passed == 0

    def test_from_report_multiple_extensions(self):
        ext1 = ExtensionMeta(
            lang="en", name="a", ext_name="A", ext_class=".A", ext_version_code=1,
        )
        ext2 = ExtensionMeta(
            lang="tr", name="b", ext_name="B", ext_class=".B", ext_version_code=2,
        )
        report = RunReport(
            run_id="multi",
            extensions=[
                ExtensionReport(extension=ext1, results=[
                    TestResult(test_name="structural:a", status="pass"),
                ]),
                ExtensionReport(extension=ext2, results=[
                    TestResult(test_name="structural:b", status="fail"),
                ]),
            ],
        )
        summary = RunSummary.from_report(report)
        assert summary.total_extensions == 2
        assert "en" in summary.by_language
        assert "tr" in summary.by_language
        assert summary.by_language["en"]["passed"] == 1
        assert summary.by_language["tr"]["failed"] == 1

    def test_from_report_category_breakdown(self):
        ext = ExtensionMeta(
            lang="en", name="a", ext_name="A", ext_class=".A", ext_version_code=1,
        )
        report = RunReport(
            run_id="cats",
            extensions=[
                ExtensionReport(extension=ext, results=[
                    TestResult(test_name="structural:x", status="pass"),
                    TestResult(test_name="connectivity:y", status="fail"),
                    TestResult(test_name="popular:z", status="skip"),
                ]),
            ],
        )
        summary = RunSummary.from_report(report)
        assert "structural" in summary.by_test_type
        assert "connectivity" in summary.by_test_type
        assert "popular" in summary.by_test_type
        assert summary.by_test_type["structural"]["passed"] == 1
        assert summary.by_test_type["connectivity"]["failed"] == 1

    def test_duration_seconds_calculation(self):
        ext = ExtensionMeta(
            lang="en", name="a", ext_name="A", ext_class=".A", ext_version_code=1,
        )
        report = RunReport(
            run_id="duration",
            started_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
            finished_at=datetime(2026, 1, 1, 0, 0, 42, tzinfo=UTC),
            extensions=[
                ExtensionReport(extension=ext, results=[
                    TestResult(test_name="t", status="pass"),
                ]),
            ],
        )
        summary = RunSummary.from_report(report)
        assert summary.duration_seconds == 42.0

    def test_from_report_error_status(self):
        ext = ExtensionMeta(
            lang="en", name="a", ext_name="A", ext_class=".A", ext_version_code=1,
        )
        report = RunReport(
            run_id="errors",
            extensions=[
                ExtensionReport(extension=ext, results=[
                    TestResult(test_name="t", status="error", message="Timeout"),
                ]),
            ],
        )
        summary = RunSummary.from_report(report)
        assert summary.errors == 1

    def test_serialization_roundtrip(self):
        ext = ExtensionMeta(
            lang="en", name="allanime", ext_name="AllAnime",
            ext_class=".AllAnime", ext_version_code=55,
            base_url="https://allanime.com",
        )
        report = RunReport(
            run_id="roundtrip",
            started_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
            finished_at=datetime(2026, 1, 1, 0, 5, 0, tzinfo=UTC),
            repo_url="https://github.com/test",
            repo_commit="abc123",
            extensions=[
                ExtensionReport(extension=ext, results=[
                    TestResult(test_name="structural:x", status="pass"),
                ]),
            ],
        )
        data = report.model_dump()
        restored = RunReport.model_validate(data)
        assert restored.run_id == "roundtrip"
        assert len(restored.extensions) == 1
