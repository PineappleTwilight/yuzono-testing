"""Unit tests for Pydantic data models."""

from __future__ import annotations

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

    def test_module_id(self):
        ext = ExtensionMeta(
            lang="en", name="allanime", ext_name="AllAnime",
            ext_class=".AllAnime", ext_version_code=55,
        )
        assert ext.module_id == "en.allanime"

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
