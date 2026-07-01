"""Unit tests for extension discovery and build.gradle parsing — expanded with edge cases."""

from __future__ import annotations

import base64
import tempfile
from pathlib import Path

import pytest

from anime_ext_test.config import Config
from anime_ext_test.discovery import (
    check_api_key_requirement,
    discover_extensions,
    discover_languages,
    discover_theme_packages,
    filter_extensions,
    get_repo_commit,
    parse_build_gradle,
    try_decode_base64_url,
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
        assert meta is None

    def test_lang_and_name_propagated(self):
        path = FIXTURES_DIR / "legacy_build.gradle"
        meta = parse_build_gradle(path, "ja", "animenana")
        assert meta is not None
        assert meta.lang == "ja"
        assert meta.name == "animenana"

    def test_module_id_computed(self):
        path = FIXTURES_DIR / "legacy_build.gradle"
        meta = parse_build_gradle(path, "en", "allanime")
        assert meta is not None
        assert meta.module_id == "en.allanime"

    def test_ext_names_empty_for_non_factory(self):
        path = FIXTURES_DIR / "legacy_build.gradle"
        meta = parse_build_gradle(path, "en", "allanime")
        assert meta is not None
        assert meta.ext_factory_names == []

    def test_base_url_from_gradle(self):
        path = FIXTURES_DIR / "multisrc_build.gradle"
        meta = parse_build_gradle(path, "tr", "tranimeci")
        assert meta is not None
        assert meta.base_url == "https://tranimaci.com"

    def test_override_version_code_default_zero(self):
        path = FIXTURES_DIR / "legacy_build.gradle"
        meta = parse_build_gradle(path, "en", "allanime")
        assert meta is not None
        assert meta.override_version_code == 0

    def test_build_gradle_path_stored(self):
        path = FIXTURES_DIR / "legacy_build.gradle"
        meta = parse_build_gradle(path, "en", "allanime")
        assert meta is not None
        assert meta.build_gradle_path == str(path)

    def test_class_simple_name_populated(self):
        path = FIXTURES_DIR / "legacy_build.gradle"
        meta = parse_build_gradle(path, "en", "allanime")
        assert meta is not None
        assert meta.class_simple_name == "AllAnime"


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

    def test_no_src_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            extensions = discover_extensions(repo)
            assert extensions == []

    def test_skips_files_in_lang_dir(self):
        """Files (not directories) in src/lang/ should be skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "src" / "en").mkdir(parents=True)
            (repo / "src" / "en" / "readme.md").write_text("text")
            extensions = discover_extensions(repo)
            assert extensions == []

    def test_skips_ext_without_build_gradle(self):
        """Extension dirs without build.gradle or .kts are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            ext_dir = repo / "src" / "en" / "no_gradle"
            ext_dir.mkdir(parents=True)
            # No build.gradle file
            extensions = discover_extensions(repo)
            assert extensions == []

    def test_uses_build_gradle_kts_fallback(self):
        """If build.gradle doesn't exist but build.gradle.kts does, parse that."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            ext_dir = repo / "src" / "en" / "kts_ext"
            ext_dir.mkdir(parents=True)
            (ext_dir / "build.gradle.kts").write_text(
                "ext {\n    extName = 'KtsExt'\n    extClass = '.KtsExt'\n"
                "    extVersionCode = 1\n}\n\n"
                'apply plugin: "kei.plugins.extension.legacy"\n',
            )
            extensions = discover_extensions(repo)
            assert len(extensions) == 1
            assert extensions[0].ext_name == "KtsExt"


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

    def test_no_filters_returns_all(self):
        config = Config()
        exts = [
            ExtensionMeta(lang="en", name="a", ext_name="A", ext_class=".A", ext_version_code=1),
            ExtensionMeta(lang="ja", name="b", ext_name="B", ext_class=".B", ext_version_code=2),
        ]
        result = filter_extensions(exts, config)
        assert len(result) == 2

    def test_combined_language_and_extension_filter(self):
        config = Config(languages=["en"], extensions=["a"])
        exts = [
            ExtensionMeta(lang="en", name="a", ext_name="A", ext_class=".A", ext_version_code=1),
            ExtensionMeta(lang="en", name="b", ext_name="B", ext_class=".B", ext_version_code=2),
            ExtensionMeta(lang="ja", name="a", ext_name="A_ja", ext_class=".A", ext_version_code=3),
        ]
        result = filter_extensions(exts, config)
        assert len(result) == 1
        assert result[0].module_id == "en.a"

    def test_include_api_key_extensions_when_not_skipping(self):
        config = Config(skip_api_key_extensions=False)
        exts = [
            ExtensionMeta(lang="en", name="a", ext_name="A", ext_class=".A",
                           ext_version_code=1, requires_api_key=True),
        ]
        result = filter_extensions(exts, config)
        assert len(result) == 1

    def test_empty_input_returns_empty(self):
        config = Config()
        result = filter_extensions([], config)
        assert result == []


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

    def test_no_src_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            assert check_api_key_requirement(Path(tmpdir)) is False

    def test_custom_api_key_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ext_dir = Path(tmpdir)
            src = ext_dir / "src"
            src.mkdir()
            kt = src / "Test.kt"
            kt.write_text('val key = BuildConfig.CUSTOM_KEY\n')
            assert check_api_key_requirement(ext_dir, api_key_fields={"CUSTOM_KEY"}) is True

    def test_custom_api_key_fields_no_match(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ext_dir = Path(tmpdir)
            src = ext_dir / "src"
            src.mkdir()
            kt = src / "Test.kt"
            kt.write_text('val key = BuildConfig.TMDB_API\n')
            assert check_api_key_requirement(ext_dir, api_key_fields={"OTHER_KEY"}) is False


class TestTryDecodeBase64Url:
    """Test base64 URL decoding used in Kotlin source scanning."""

    def test_valid_https_base64(self):
        url = "https://example.com"
        encoded = base64.b64encode(url.encode()).decode()
        result = try_decode_base64_url(encoded)
        assert result == url

    def test_valid_http_base64(self):
        url = "http://anime.example.org"
        encoded = base64.b64encode(url.encode()).decode()
        result = try_decode_base64_url(encoded)
        assert result == url

    def test_non_url_base64(self):
        """Base64 that decodes to non-URL text returns None."""
        text = "this is not a url"
        encoded = base64.b64encode(text.encode()).decode()
        result = try_decode_base64_url(encoded)
        assert result is None

    def test_short_string_not_base64(self):
        """Strings shorter than 16 chars don't match the base64 regex."""
        result = try_decode_base64_url("aGVsbG8=")
        assert result is None

    def test_empty_string(self):
        result = try_decode_base64_url("")
        assert result is None

    def test_none_like_empty(self):
        result = try_decode_base64_url("   ")
        assert result is None

    def test_invalid_base64(self):
        """String that matches length but isn't valid base64 returns None."""
        result = try_decode_base64_url("!!!invalid-base64!!!but-long-enough-string")
        assert result is None


class TestDiscoverLanguages:
    def test_discovers_languages(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "src" / "en" / "ext1").mkdir(parents=True)
            (repo / "src" / "tr" / "ext2").mkdir(parents=True)
            langs = discover_languages(repo)
            assert "en" in langs
            assert "tr" in langs

    def test_empty_languages(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "src").mkdir()
            langs = discover_languages(repo)
            assert langs == []

    def test_skips_empty_lang_dirs(self):
        """Language dirs with no subdirectories are excluded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "src" / "en").mkdir(parents=True)
            # en/ dir exists but is empty
            langs = discover_languages(repo)
            assert langs == []

    def test_no_src_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            langs = discover_languages(Path(tmpdir))
            assert langs == []

    def test_returns_sorted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "src" / "ja" / "ext1").mkdir(parents=True)
            (repo / "src" / "en" / "ext2").mkdir(parents=True)
            (repo / "src" / "all" / "ext3").mkdir(parents=True)
            langs = discover_languages(repo)
            assert langs == sorted(langs)


class TestDiscoverThemePackages:
    def test_discovers_themes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            theme1 = repo / "lib-multisrc" / "dopeflix"
            theme1.mkdir(parents=True)
            (theme1 / "build.gradle.kts").write_text("plugins { id('kotlin') }")
            theme2 = repo / "lib-multisrc" / "animestream"
            theme2.mkdir(parents=True)
            (theme2 / "build.gradle.kts").write_text("plugins { id('kotlin') }")
            themes = discover_theme_packages(repo)
            assert "dopeflix" in themes
            assert "animestream" in themes

    def test_no_multisrc_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            themes = discover_theme_packages(Path(tmpdir))
            assert themes == []

    def test_skips_dirs_without_gradle_kts(self):
        """Theme dirs without build.gradle.kts are excluded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            theme = repo / "lib-multisrc" / "no_build_file"
            theme.mkdir(parents=True)
            # No build.gradle.kts
            themes = discover_theme_packages(Path(tmpdir))
            assert themes == []

    def test_skips_files_in_multisrc_dir(self):
        """Files (not dirs) in lib-multisrc/ are excluded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "lib-multisrc").mkdir()
            (repo / "lib-multisrc" / "README.md").write_text("text")
            themes = discover_theme_packages(Path(tmpdir))
            assert themes == []

    def test_returns_sorted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            for name in ["zoo", "alpha", "mid"]:
                d = repo / "lib-multisrc" / name
                d.mkdir(parents=True)
                (d / "build.gradle.kts").write_text("plugins {}")
            themes = discover_theme_packages(repo)
            assert themes == sorted(themes)


class TestGetRepoCommit:
    def test_returns_commit_from_git_repo(self):
        """Requires a real git repo — verifies commit hash format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            import subprocess
            subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True, check=True)
            (repo / "test.txt").write_text("hello")
            subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
            subprocess.run(["git", "commit", "-m", "init"], cwd=repo, capture_output=True, check=True)
            commit = get_repo_commit(repo)
            assert len(commit) >= 7  # Short hash format
