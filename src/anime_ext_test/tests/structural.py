"""Layer 1: Structural tests — validate build.gradle metadata without HTTP."""

from __future__ import annotations

import time
from pathlib import Path

import aiohttp

from anime_ext_test.models import ExtensionMeta, TestResult
from anime_ext_test.tests.registry import ExtensionTest, register_test


@register_test
class StructuralTest(ExtensionTest):
    """Validate extension metadata from build.gradle files."""

    name = "structural"
    category = "structural"

    async def run(
        self,
        ext: ExtensionMeta,
        session: aiohttp.ClientSession | None = None,
    ) -> list[TestResult]:
        results: list[TestResult] = []
        repo_dir = self._get_repo_dir(ext)

        results.append(self._test_ext_name_present(ext))
        results.append(self._test_ext_class_format(ext))
        results.append(self._test_ext_version_code_positive(ext))
        results.append(self._test_ext_class_exists(ext, repo_dir))
        results.append(self._test_base_url_valid(ext))
        results.append(self._test_theme_pkg_exists(ext, repo_dir))
        results.append(self._test_override_version_code(ext))
        results.append(self._test_build_gradle_parseable(ext))
        results.append(self._test_package_structure(ext, repo_dir))
        results.append(self._test_factory_class_consistency(ext, repo_dir))

        return results

    @staticmethod
    def _get_repo_dir(ext: ExtensionMeta) -> Path:
        build_gradle = Path(ext.build_gradle_path)
        return build_gradle.parent.parent.parent.parent

    def _test_ext_name_present(self, ext: ExtensionMeta) -> TestResult:
        start = time.monotonic()
        if ext.ext_name and len(ext.ext_name.strip()) > 0:
            return self._pass("ext_name_present", _ms(start), f"extName='{ext.ext_name}'")
        return self._fail("ext_name_present", _ms(start), "extName is empty or missing")

    def _test_ext_class_format(self, ext: ExtensionMeta) -> TestResult:
        start = time.monotonic()
        if ext.ext_class.startswith("."):
            return self._pass("ext_class_format", _ms(start), f"extClass='{ext.ext_class}'")
        return self._fail(
            "ext_class_format",
            _ms(start),
            f"extClass must start with '.', got '{ext.ext_class}'",
        )

    def _test_ext_version_code_positive(self, ext: ExtensionMeta) -> TestResult:
        start = time.monotonic()
        # extVersionCode=0 is acceptable when overrideVersionCode is explicitly set
        # (common in multisrc extensions where theme defines base version)
        if ext.ext_version_code > 0:
            return self._pass("ext_version_code_positive", _ms(start), f"extVersionCode={ext.ext_version_code}")
        if ext.ext_version_code == 0 and ext.override_version_code >= 0:
            return self._skip(
                "ext_version_code_positive",
                _ms(start),
                f"extVersionCode=0 with overrideVersionCode={ext.override_version_code}",
            )
        return self._fail(
            "ext_version_code_positive",
            _ms(start),
            f"extVersionCode must be > 0, got {ext.ext_version_code}",
        )

    def _test_ext_class_exists(self, ext: ExtensionMeta, repo_dir: Path) -> TestResult:
        start = time.monotonic()
        class_file = self._resolve_class_file(ext, repo_dir)
        if class_file is not None and class_file.is_file():
            return self._pass(
                "ext_class_exists", _ms(start),
                f"Found: {class_file.relative_to(repo_dir)}",
            )
        # Fallback: search anywhere under src/{lang}/{name}/ for the class file
        fallback = self._find_class_file_by_rglob(ext, repo_dir)
        if fallback is not None:
            return self._pass(
                "ext_class_exists", _ms(start),
                f"Found (non-standard path): {fallback.relative_to(repo_dir)}",
            )
        return self._fail(
            "ext_class_exists",
            _ms(start),
            f"Class file not found for extClass='{ext.ext_class}'",
            detail=f"Expected near: src/{ext.lang}/{ext.name}/src/",
        )

    def _test_base_url_valid(self, ext: ExtensionMeta) -> TestResult:
        start = time.monotonic()
        if not ext.base_url:
            return self._skip("base_url_valid", _ms(start), "No baseUrl in build.gradle")
        if ext.base_url.startswith("http://") or ext.base_url.startswith("https://"):
            return self._pass("base_url_valid", _ms(start), f"baseUrl='{ext.base_url}'")
        return self._fail(
            "base_url_valid",
            _ms(start),
            f"baseUrl must start with http:// or https://, got '{ext.base_url}'",
        )

    def _test_theme_pkg_exists(self, ext: ExtensionMeta, repo_dir: Path) -> TestResult:
        start = time.monotonic()
        if not ext.is_multisrc:
            return self._skip("theme_pkg_exists", _ms(start), "Not a multisrc extension")
        theme_pkg = ext.theme_pkg or ""
        theme_dir = repo_dir / "lib-multisrc" / theme_pkg
        if theme_dir.is_dir():
            return self._pass("theme_pkg_exists", _ms(start), f"lib-multisrc/{theme_pkg}/ exists")
        return self._fail(
            "theme_pkg_exists",
            _ms(start),
            f"lib-multisrc/{theme_pkg}/ directory does not exist",
        )

    def _test_override_version_code(self, ext: ExtensionMeta) -> TestResult:
        start = time.monotonic()
        if ext.override_version_code >= 0:
            return self._pass(
                "override_version_code_valid", _ms(start),
                f"overrideVersionCode={ext.override_version_code}",
            )
        return self._fail(
            "override_version_code_valid",
            _ms(start),
            f"overrideVersionCode must be >= 0, got {ext.override_version_code}",
        )

    def _test_build_gradle_parseable(self, ext: ExtensionMeta) -> TestResult:
        start = time.monotonic()
        if ext.ext_name and ext.ext_class:
            return self._pass("build_gradle_parseable", _ms(start), "ext block parsed successfully")
        return self._fail("build_gradle_parseable", _ms(start), "ext block could not be fully parsed")

    def _test_package_structure(self, ext: ExtensionMeta, repo_dir: Path) -> TestResult:
        start = time.monotonic()
        pkg_dir = (
            repo_dir / "src" / ext.lang / ext.name / "src"
            / "eu" / "kanade" / "tachiyomi" / "animeextension"
            / ext.lang / ext.name
        )
        if pkg_dir.is_dir():
            kt_files = list(pkg_dir.glob("*.kt"))
            if kt_files:
                return self._pass(
                    "package_structure", _ms(start),
                    f"Found {len(kt_files)} .kt file(s) in expected package dir",
                )
        src_dir = repo_dir / "src" / ext.lang / ext.name / "src"
        if src_dir.is_dir():
            kt_files = list(src_dir.rglob("*.kt"))
            if kt_files:
                return self._pass(
                    "package_structure", _ms(start),
                    f"Found {len(kt_files)} .kt file(s) under src/",
                )
        return self._fail(
            "package_structure",
            _ms(start),
            f"Expected package directory not found: {pkg_dir}",
        )

    def _test_factory_class_consistency(self, ext: ExtensionMeta, repo_dir: Path) -> TestResult:
        start = time.monotonic()
        if "Factory" not in ext.ext_class:
            return self._skip("factory_class_consistency", _ms(start), "Not a factory extension")
        base_class = ext.ext_class.replace("Factory", "")
        base_meta = ext.model_copy(update={"ext_class": base_class, "class_simple_name": base_class.lstrip(".")})
        class_file = self._resolve_class_file(base_meta, repo_dir)
        if class_file is not None and class_file.is_file():
            return self._pass("factory_class_consistency", _ms(start), f"Factory base class '{base_class}' exists")
        return self._fail(
            "factory_class_consistency",
            _ms(start),
            f"Factory base class '{base_class}' not found",
        )

    @staticmethod
    def _resolve_class_file(ext: ExtensionMeta, repo_dir: Path) -> Path | None:
        class_name = ext.ext_class.lstrip(".")
        if not class_name:
            return None
        pkg_dir = (
            repo_dir / "src" / ext.lang / ext.name / "src"
            / "eu" / "kanade" / "tachiyomi" / "animeextension"
            / ext.lang / ext.name
        )
        return pkg_dir / f"{class_name}.kt"

    @staticmethod
    def _find_class_file_by_rglob(ext: ExtensionMeta, repo_dir: Path) -> Path | None:
        class_name = ext.ext_class.lstrip(".")
        if not class_name:
            return None
        ext_src = repo_dir / "src" / ext.lang / ext.name / "src"
        if not ext_src.is_dir():
            return None
        for kt_file in ext_src.rglob(f"{class_name}.kt"):
            return kt_file
        return None


def _ms(start: float) -> float:
    return round((time.monotonic() - start) * 1000, 1)
