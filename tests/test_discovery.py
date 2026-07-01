"""Unit tests for extension discovery and build.gradle parsing."""

from __future__ import annotations

import tempfile
from pathlib import Path

from anime_ext_test.config import Config
from anime_ext_test.discovery import (
    check_api_key_requirement,
    discover_extensions,
    filter_extensions,
    parse_build_gradle,
)
from anime_ext_test.models import ExtensionMeta

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "sample_build_gradles"


class TestParseBuildGradle:
    def test_legacy_extension(self):
        path = FIXTURES_DIR / "legacy_build.gradle"
        meta = parse_build_gradle(path, "en", "allanime")
        assert meta is not None
        assert meta.ext_name == "AllAnime"
        assert meta.ext_class == ".AllAnime"
        assert meta.ext_version_code == 55
        assert meta.theme_pkg is None
        assert meta.is_multisrc is False

    def test_multisrc_extension(self):
        path = FIXTURES_DIR / "multisrc_build.gradle"
        meta = parse_build_gradle(path, "tr", "tranimeci")
        assert meta is not None
        assert meta.ext_name == "TRAnimeCI"
        assert meta.ext_class == ".TRAnimeCI"
        assert meta.theme_pkg == "animestream"
        assert meta.base_url == "https://tranimaci.com"
        assert meta.override_version_code == 2
        assert meta.is_multisrc is True

    def test_factory_extension(self):
        path = FIXTURES_DIR / "factory_build.gradle"
        meta = parse_build_gradle(path, "all", "jellyfin")
        assert meta is not None
        assert meta.ext_class == ".JellyfinFactory"
        assert "Factory" in meta.ext_class
        assert len(meta.ext_factory_names) == 3
        assert "Jellyfin (1)" in meta.ext_factory_names

    def test_nsfw_extension(self):
        path = FIXTURES_DIR / "nsfw_build.gradle"
        meta = parse_build_gradle(path, "zh", "hanime1")
        assert meta is not None
        assert meta.is_nsfw is True

    def test_missing_ext_block(self):
        path = FIXTURES_DIR / "missing_ext_block.gradle"
        meta = parse_build_gradle(path, "en", "broken")
        assert meta is None

    def test_nonexistent_file(self):
        meta = parse_build_gradle(Path("/nonexistent/build.gradle"), "en", "nope")
        # Should raise or return None — file read will error
        assert meta is None


class TestDiscoverExtensions:
    def test_discovers_from_fixture_repo(self):
        """Create a temporary repo structure mimicking the real layout."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            # Create src/en/allanime/build.gradle
            ext_dir = repo / "src" / "en" / "allanime"
            ext_dir.mkdir(parents=True)
            (ext_dir / "build.gradle").write_text(
                "ext {\n    extName = 'AllAnime'\n    extClass = '.AllAnime'\n"
                "    extVersionCode = 55\n}\n\n"
                'apply plugin: "kei.plugins.extension.legacy"\n',
            )
            # Create src/tr/tranimeci/build.gradle (multisrc)
            ext_dir2 = repo / "src" / "tr" / "tranimeci"
            ext_dir2.mkdir(parents=True)
            (ext_dir2 / "build.gradle").write_text(
                "ext {\n    extName = 'TRAnimeCI'\n    extClass = '.TRAnimeCI'\n"
                "    themePkg = 'animestream'\n    baseUrl = 'https://tranimaci.com'\n"
                "    overrideVersionCode = 2\n}\n\n"
                'apply plugin: "kei.plugins.extension.legacy"\n',
            )

            extensions = discover_extensions(repo)
            assert len(extensions) == 2
            langs = {e.lang for e in extensions}
            assert "en" in langs
            assert "tr" in langs

    def test_empty_src_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            src = repo / "src"
            src.mkdir()
            extensions = discover_extensions(repo)
            assert extensions == []


class TestFilterExtensions:
    def test_filter_by_language(self):
        config = Config(languages=["en"])
        exts = [
            ExtensionMeta(lang="en", name="a", ext_name="A", ext_class=".A", ext_version_code=1),
            ExtensionMeta(lang="ja", name="b", ext_name="B", ext_class=".B", ext_version_code=2),
        ]
        result = filter_extensions(exts, config)
        assert len(result) == 1
        assert result[0].lang == "en"

    def test_filter_by_extension_name(self):
        config = Config(extensions=["allanime"])
        exts = [
            ExtensionMeta(lang="en", name="allanime", ext_name="AllAnime", ext_class=".A", ext_version_code=1),
            ExtensionMeta(lang="en", name="other", ext_name="Other", ext_class=".O", ext_version_code=2),
        ]
        result = filter_extensions(exts, config)
        assert len(result) == 1
        assert result[0].name == "allanime"

    def test_filter_by_module_id(self):
        config = Config(extensions=["en.allanime"])
        exts = [
            ExtensionMeta(lang="en", name="allanime", ext_name="AllAnime", ext_class=".A", ext_version_code=1),
        ]
        result = filter_extensions(exts, config)
        assert len(result) == 1

    def test_skip_api_key_extensions(self):
        config = Config(skip_api_key_extensions=True)
        exts = [
            ExtensionMeta(lang="en", name="a", ext_name="A", ext_class=".A",
                           ext_version_code=1, requires_api_key=False),
            ExtensionMeta(lang="en", name="b", ext_name="B", ext_class=".B",
                           ext_version_code=2, requires_api_key=True),
        ]
        result = filter_extensions(exts, config)
        assert len(result) == 1
        assert result[0].name == "a"


class TestCheckApiKeyRequirement:
    def test_no_api_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ext_dir = Path(tmpdir)
            src = ext_dir / "src"
            src.mkdir()
            kt = src / "Test.kt"
            kt.write_text("class Test : AnimeHttpSource()\n")
            assert check_api_key_requirement(ext_dir) is False

    def test_with_api_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ext_dir = Path(tmpdir)
            src = ext_dir / "src"
            src.mkdir()
            kt = src / "Test.kt"
            kt.write_text('val key = BuildConfig.TMDB_API\n')
            assert check_api_key_requirement(ext_dir) is True
