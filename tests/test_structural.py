"""Unit tests for structural test logic (no HTTP required)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from anime_ext_test.config import Config
from anime_ext_test.models import ExtensionMeta
from anime_ext_test.tests.structural import StructuralTest


@pytest.fixture
def config() -> Config:
    return Config()


@pytest.fixture
def structural(config: Config) -> StructuralTest:
    return StructuralTest(config)


def _ext(
    lang: str = "en",
    name: str = "allanime",
    ext_name: str = "AllAnime",
    ext_class: str = ".AllAnime",
    ext_version_code: int = 55,
    base_url: str = "https://allanime.com",
    theme_pkg: str | None = None,
    is_nsfw: bool = False,
    override_version_code: int = 0,
    requires_api_key: bool = False,
    build_gradle_path: str = "",
    ext_factory_names: list[str] | None = None,
    class_simple_name: str = "",
) -> ExtensionMeta:
    """Create an ExtensionMeta with sensible defaults."""
    return ExtensionMeta(
        lang=lang,
        name=name,
        ext_name=ext_name,
        ext_class=ext_class,
        ext_version_code=ext_version_code,
        base_url=base_url,
        theme_pkg=theme_pkg,
        is_nsfw=is_nsfw,
        override_version_code=override_version_code,
        requires_api_key=requires_api_key,
        build_gradle_path=build_gradle_path,
        ext_factory_names=ext_factory_names or [],
        class_simple_name=class_simple_name,
    )


class TestStructuralExtName:
    async def test_ext_name_present(self, structural: StructuralTest):
        ext = _ext(ext_name="AllAnime")
        result = await structural.run(ext)
        name_result = next(r for r in result if r.test_name == "structural:ext_name_present")
        assert name_result.status == "pass"

    async def test_ext_name_empty(self, structural: StructuralTest):
        ext = _ext(ext_name="")
        result = await structural.run(ext)
        name_result = next(r for r in result if r.test_name == "structural:ext_name_present")
        assert name_result.status == "fail"


class TestStructuralExtClassFormat:
    async def test_ext_class_starts_with_dot(self, structural: StructuralTest):
        ext = _ext(ext_class=".AllAnime")
        result = await structural.run(ext)
        class_result = next(r for r in result if r.test_name == "structural:ext_class_format")
        assert class_result.status == "pass"

    async def test_ext_class_no_dot(self, structural: StructuralTest):
        ext = _ext(ext_class="AllAnime")
        result = await structural.run(ext)
        class_result = next(r for r in result if r.test_name == "structural:ext_class_format")
        assert class_result.status == "fail"


class TestStructuralVersionCode:
    async def test_version_code_positive(self, structural: StructuralTest):
        ext = _ext(ext_version_code=55)
        result = await structural.run(ext)
        vc_result = next(r for r in result if r.test_name == "structural:ext_version_code_positive")
        assert vc_result.status == "pass"

    async def test_version_code_zero(self, structural: StructuralTest):
        ext = _ext(ext_version_code=0)
        result = await structural.run(ext)
        vc_result = next(r for r in result if r.test_name == "structural:ext_version_code_positive")
        assert vc_result.status == "skip"

    async def test_version_code_negative(self, structural: StructuralTest):
        ext = _ext(ext_version_code=-1)
        result = await structural.run(ext)
        vc_result = next(r for r in result if r.test_name == "structural:ext_version_code_positive")
        assert vc_result.status == "fail"


class TestStructuralBaseUrl:
    async def test_base_url_valid_https(self, structural: StructuralTest):
        ext = _ext(base_url="https://allanime.com")
        result = await structural.run(ext)
        url_result = next(r for r in result if r.test_name == "structural:base_url_valid")
        assert url_result.status == "pass"

    async def test_base_url_invalid_no_scheme(self, structural: StructuralTest):
        ext = _ext(base_url="allanime.com")
        result = await structural.run(ext)
        url_result = next(r for r in result if r.test_name == "structural:base_url_valid")
        assert url_result.status == "fail"

    async def test_base_url_missing_skipped(self, structural: StructuralTest):
        ext = _ext(base_url="")
        result = await structural.run(ext)
        url_result = next(r for r in result if r.test_name == "structural:base_url_valid")
        assert url_result.status == "skip"


class TestStructuralBuildGradleParseable:
    async def test_parseable(self, structural: StructuralTest):
        ext = _ext(ext_name="AllAnime", ext_class=".AllAnime")
        result = await structural.run(ext)
        bg_result = next(r for r in result if r.test_name == "structural:build_gradle_parseable")
        assert bg_result.status == "pass"


class TestStructuralFactoryConsistency:
    async def test_non_factory_skipped(self, structural: StructuralTest):
        ext = _ext(ext_class=".AllAnime")
        result = await structural.run(ext)
        factory_result = next(r for r in result if r.test_name == "structural:factory_class_consistency")
        assert factory_result.status == "skip"

    async def test_factory_base_class_checked(self, structural: StructuralTest):
        ext = _ext(ext_class=".JellyfinFactory")
        result = await structural.run(ext)
        factory_result = next(r for r in result if r.test_name == "structural:factory_class_consistency")
        # Will fail because the class file doesn't exist in this test context
        assert factory_result.status == "fail"


class TestStructuralRunWithRepo:
    async def test_full_run_with_repo(self, structural: StructuralTest):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            ext_dir = (
                repo / "src" / "en" / "allanime" / "src"
                / "eu" / "kanade" / "tachiyomi" / "animeextension"
                / "en" / "allanime"
            )
            ext_dir.mkdir(parents=True)
            (ext_dir / "AllAnime.kt").write_text("class AllAnime\n")
            build_gradle = repo / "src" / "en" / "allanime" / "build.gradle"
            build_gradle.write_text(
                "ext {\n    extName = 'AllAnime'\n    extClass = '.AllAnime'\n"
                "    extVersionCode = 55\n}\n\n"
                'apply plugin: "kei.plugins.extension.legacy"\n',
            )
            ext = _ext(build_gradle_path=str(build_gradle))
            results = await structural.run(ext)
            assert len(results) == 10  # 10 structural checks

            # Class file should exist in this context
            class_result = next(r for r in results if r.test_name == "structural:ext_class_exists")
            assert class_result.status == "pass"

            pkg_result = next(r for r in results if r.test_name == "structural:package_structure")
            assert pkg_result.status == "pass"
