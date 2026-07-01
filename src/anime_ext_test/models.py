"""Pydantic data models for the testing suite."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class ExtensionMeta(BaseModel):
    """Metadata for a single extension, parsed from its build.gradle."""

    lang: str
    name: str  # directory name, e.g. "animepahe"
    ext_name: str  # extName from build.gradle, e.g. "AnimePahe"
    ext_class: str  # extClass from build.gradle, e.g. ".AnimePahe"
    ext_version_code: int
    theme_pkg: str | None = None  # e.g. "dopeflix" or None for legacy
    base_url: str = ""
    override_version_code: int = 0
    is_nsfw: bool = False
    requires_api_key: bool = False
    build_gradle_path: str = ""
    ext_factory_names: list[str] = Field(default_factory=list)
    # Class name without leading dot, used for file resolution
    class_simple_name: str = ""

    def model_post_init(self, __context: object) -> None:
        if not self.class_simple_name and self.ext_class:
            self.class_simple_name = self.ext_class.lstrip(".")

    @property
    def module_id(self) -> str:
        return f"{self.lang}.{self.name}"

    @property
    def is_multisrc(self) -> bool:
        return self.theme_pkg is not None


class TestResult(BaseModel):
    """Result of a single test assertion for a single extension."""

    __test__ = False

    test_name: str  # e.g. "structural:ext_class_format"
    status: Literal["pass", "fail", "skip", "error"]
    duration_ms: float = 0.0
    message: str = ""
    detail: str = ""  # Stack trace or response snippet on failure


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ExtensionReport(BaseModel):
    """Aggregated test results for a single extension."""

    extension: ExtensionMeta
    results: list[TestResult] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=_utcnow)
    finished_at: datetime | None = None

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == "pass")

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == "fail")

    @property
    def skipped(self) -> int:
        return sum(1 for r in self.results if r.status == "skip")

    @property
    def errored(self) -> int:
        return sum(1 for r in self.results if r.status == "error")

    @property
    def total(self) -> int:
        return len(self.results)


class RunReport(BaseModel):
    """Complete report for a single test run across all extensions."""

    run_id: str
    started_at: datetime = Field(default_factory=_utcnow)
    finished_at: datetime | None = None
    repo_url: str = ""
    repo_commit: str = ""
    extensions: list[ExtensionReport] = Field(default_factory=list)


class RunSummary(BaseModel):
    """Aggregated statistics from a test run."""

    total_extensions: int = 0
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    by_language: dict[str, dict[str, int]] = Field(default_factory=dict)
    by_test_type: dict[str, dict[str, int]] = Field(default_factory=dict)

    @classmethod
    def from_report(cls, report: RunReport) -> RunSummary:
        """Compute summary statistics from a full RunReport."""
        by_language: dict[str, dict[str, int]] = {}
        by_test_type: dict[str, dict[str, int]] = {}
        total_tests = 0
        passed = 0
        failed = 0
        skipped = 0
        errors = 0

        for ext_report in report.extensions:
            lang = ext_report.extension.lang
            lang_stats = by_language.setdefault(
                lang, {"passed": 0, "failed": 0, "skipped": 0, "errors": 0, "total": 0},
            )

            for result in ext_report.results:
                total_tests += 1
                lang_stats["total"] += 1
                cat = result.test_name.split(":")[0]
                cat_stats = by_test_type.setdefault(cat, {"passed": 0, "failed": 0, "skipped": 0, "errors": 0})

                if result.status == "pass":
                    passed += 1
                    lang_stats["passed"] += 1
                    cat_stats["passed"] += 1
                elif result.status == "fail":
                    failed += 1
                    lang_stats["failed"] += 1
                    cat_stats["failed"] += 1
                elif result.status == "skip":
                    skipped += 1
                    lang_stats["skipped"] += 1
                    cat_stats["skipped"] += 1
                elif result.status == "error":
                    errors += 1
                    lang_stats["errors"] += 1
                    cat_stats["errors"] += 1

        duration = 0.0
        if report.started_at and report.finished_at:
            duration = (report.finished_at - report.started_at).total_seconds()

        return cls(
            total_extensions=len(report.extensions),
            total_tests=total_tests,
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            duration_seconds=round(duration, 1),
            by_language=by_language,
            by_test_type=by_test_type,
        )
