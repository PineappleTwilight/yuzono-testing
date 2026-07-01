"""Unit tests for Config dataclass — defaults, immutability, field validation."""

from __future__ import annotations

import pytest
from dataclasses import FrozenInstanceError

from anime_ext_test.config import Config


class TestConfigDefaults:
    """Verify all default values match the codebase contract."""

    def test_repo_url_default(self):
        cfg = Config()
        assert cfg.repo_url == "https://github.com/yuzono/anime-extensions.git"

    def test_repo_branch_default(self):
        cfg = Config()
        assert cfg.repo_branch == "master"

    def test_clone_dir_default(self):
        cfg = Config()
        assert cfg.clone_dir == "repo"

    def test_http_timeout_default(self):
        cfg = Config()
        assert cfg.http_timeout == 30.0

    def test_http_connect_timeout_default(self):
        cfg = Config()
        assert cfg.http_connect_timeout == 15.0

    def test_http_total_timeout_default(self):
        cfg = Config()
        assert cfg.http_total_timeout == 120.0

    def test_max_concurrent_default(self):
        cfg = Config()
        assert cfg.max_concurrent == 20

    def test_max_retries_default(self):
        cfg = Config()
        assert cfg.max_retries == 2

    def test_retry_backoff_default(self):
        cfg = Config()
        assert cfg.retry_backoff == 5.0

    def test_user_agent_contains_chrome(self):
        cfg = Config()
        assert "Chrome" in cfg.user_agent
        assert "Mobile" in cfg.user_agent

    def test_languages_default_empty(self):
        cfg = Config()
        assert cfg.languages == []

    def test_extensions_default_empty(self):
        cfg = Config()
        assert cfg.extensions == []

    def test_test_categories_default_all_13(self):
        cfg = Config()
        expected = [
            "structural", "connectivity", "popular", "search", "details",
            "episodes", "latest", "filters", "series_details",
            "episode_list", "video_streams", "pagination", "post_search",
        ]
        assert cfg.test_categories == expected

    def test_skip_api_key_extensions_default(self):
        cfg = Config()
        assert cfg.skip_api_key_extensions is True

    def test_api_key_build_configs_default(self):
        cfg = Config()
        assert "TMDB_API" in cfg.api_key_build_configs

    def test_output_dir_default(self):
        cfg = Config()
        assert cfg.output_dir == "./reports"

    def test_report_format_default(self):
        cfg = Config()
        assert cfg.report_format == "both"

    def test_no_clone_default(self):
        cfg = Config()
        assert cfg.no_clone is False

    def test_repo_dir_default(self):
        cfg = Config()
        assert cfg.repo_dir == ""


class TestConfigImmutability:
    """Config is frozen — all field assignments must raise."""

    def test_cannot_reassign_repo_url(self):
        cfg = Config()
        with pytest.raises(FrozenInstanceError):
            cfg.repo_url = "https://other.repo"  # type: ignore[misc]

    def test_cannot_reassign_max_concurrent(self):
        cfg = Config()
        with pytest.raises(FrozenInstanceError):
            cfg.max_concurrent = 99  # type: ignore[misc]

    def test_cannot_reassign_languages(self):
        cfg = Config()
        with pytest.raises(FrozenInstanceError):
            cfg.languages = ["fr"]  # type: ignore[misc]

    def test_cannot_reassign_skip_api_key(self):
        cfg = Config()
        with pytest.raises(FrozenInstanceError):
            cfg.skip_api_key_extensions = False  # type: ignore[misc]


class TestConfigCustomValues:
    """Config with explicit constructor args overrides defaults."""

    def test_custom_repo_url(self):
        cfg = Config(repo_url="https://github.com/other/repo.git")
        assert cfg.repo_url == "https://github.com/other/repo.git"

    def test_custom_languages(self):
        cfg = Config(languages=["en", "tr"])
        assert cfg.languages == ["en", "tr"]

    def test_custom_max_concurrent(self):
        cfg = Config(max_concurrent=50)
        assert cfg.max_concurrent == 50

    def test_custom_http_timeout(self):
        cfg = Config(http_timeout=60.0)
        assert cfg.http_timeout == 60.0

    def test_custom_report_format(self):
        cfg = Config(report_format="all")
        assert cfg.report_format == "all"

    def test_custom_test_categories(self):
        cfg = Config(test_categories=["structural", "connectivity"])
        assert cfg.test_categories == ["structural", "connectivity"]

    def test_no_clone_true(self):
        cfg = Config(no_clone=True, repo_dir="/tmp/my-repo")
        assert cfg.no_clone is True
        assert cfg.repo_dir == "/tmp/my-repo"


class TestConfigListFieldsAreIndependent:
    """Mutable default-factory fields must not leak between instances."""

    def test_languages_isolation(self):
        cfg1 = Config(languages=["en"])
        cfg2 = Config(languages=["tr"])
        assert cfg1.languages == ["en"]
        assert cfg2.languages == ["tr"]

    def test_extensions_isolation(self):
        cfg1 = Config(extensions=["a"])
        cfg2 = Config(extensions=["b"])
        assert cfg1.extensions == ["a"]
        assert cfg2.extensions == ["b"]

    def test_default_lists_are_empty_not_shared(self):
        cfg1 = Config()
        cfg2 = Config()
        assert cfg1.languages == []
        assert cfg2.languages == []
        # They are separate list instances
        assert cfg1.languages is not cfg2.languages


class TestConfigApiKeyBuildConfigs:
    """Verify api_key_build_configs set behavior."""

    def test_default_contains_tmdb(self):
        cfg = Config()
        assert "TMDB_API" in cfg.api_key_build_configs

    def test_custom_api_key_configs(self):
        cfg = Config(api_key_build_configs={"TMDB_API", "ANILIST_KEY"})
        assert "ANILIST_KEY" in cfg.api_key_build_configs
        assert "TMDB_API" in cfg.api_key_build_configs
