"""Unit tests for theme patterns — defaults, THEME_URL_PATTERNS completeness, URL builders."""

from __future__ import annotations

import pytest

from anime_ext_test.theme_patterns import (
    THEME_URL_PATTERNS,
    ThemePattern,
    build_latest_url,
    build_popular_url,
    build_search_url,
    get_theme_pattern,
)


class TestThemePatternDefaults:
    """Verify ThemePattern dataclass default values."""

    def test_default_popular_path(self):
        p = ThemePattern()
        assert p.popular_path == "/"

    def test_default_search_method(self):
        p = ThemePattern()
        assert p.search_method == "GET"

    def test_default_episode_delivery(self):
        p = ThemePattern()
        assert p.episode_delivery == "inline"

    def test_default_video_delivery(self):
        p = ThemePattern()
        assert p.video_delivery == "iframe"

    def test_default_supports_filters(self):
        p = ThemePattern()
        assert p.supports_filters is True

    def test_default_supports_latest(self):
        p = ThemePattern()
        assert p.supports_latest is True

    def test_default_supports_episodes(self):
        p = ThemePattern()
        assert p.supports_episodes is True

    def test_default_is_js_rendered(self):
        p = ThemePattern()
        assert p.is_js_rendered is False

    def test_default_is_api_driven(self):
        p = ThemePattern()
        assert p.is_api_driven is False

    def test_default_xhr_headers_empty(self):
        p = ThemePattern()
        assert p.xhr_headers == {}

    def test_default_extra_headers_empty(self):
        p = ThemePattern()
        assert p.extra_headers == {}

    def test_default_search_query_param(self):
        p = ThemePattern()
        assert p.search_query_param == "q"

    def test_default_episode_xhr_path_none(self):
        p = ThemePattern()
        assert p.episode_xhr_path is None

    def test_default_video_xhr_path_none(self):
        p = ThemePattern()
        assert p.video_xhr_path is None

    def test_default_search_post_field_none(self):
        p = ThemePattern()
        assert p.search_post_field is None

    def test_default_related_selector_empty(self):
        p = ThemePattern()
        assert p.related_selector == ""


class TestThemeUrlPatternsRegistry:
    """Verify the THEME_URL_PATTERNS registry is complete and well-formed."""

    EXPECTED_THEMES = [
        "dooplay", "animestream", "wcotheme", "anikototheme",
        "datalifeengine", "dopeflix", "pelisplus", "zorotheme",
        "animekaitheme", "yflixtheme", "anilist",
    ]

    def test_all_expected_themes_present(self):
        for theme in self.EXPECTED_THEMES:
            assert theme in THEME_URL_PATTERNS, f"Missing theme: {theme}"

    def test_no_extra_themes(self):
        assert set(THEME_URL_PATTERNS.keys()) == set(self.EXPECTED_THEMES)

    def test_theme_count(self):
        assert len(THEME_URL_PATTERNS) == 11

    def test_each_pattern_is_theme_pattern(self):
        for key, pattern in THEME_URL_PATTERNS.items():
            assert isinstance(pattern, ThemePattern), f"{key} is not a ThemePattern"

    def test_each_theme_has_popular_path(self):
        for key, pattern in THEME_URL_PATTERNS.items():
            assert pattern.popular_path, f"{key} missing popular_path"

    def test_each_theme_has_search_path(self):
        for key, pattern in THEME_URL_PATTERNS.items():
            assert pattern.search_path is not None, f"{key} missing search_path"

    def test_post_themes_have_post_field(self):
        """Themes with search_method=POST must have search_post_field."""
        for key, pattern in THEME_URL_PATTERNS.items():
            if pattern.search_method == "POST":
                assert pattern.search_post_field is not None, (
                    f"{key} uses POST search but has no search_post_field"
                )

    def test_xhr_themes_have_xhr_path(self):
        """Themes with episode_delivery=xhr must have episode_xhr_path."""
        for key, pattern in THEME_URL_PATTERNS.items():
            if pattern.episode_delivery == "xhr":
                assert pattern.episode_xhr_path is not None, (
                    f"{key} uses XHR episode delivery but has no episode_xhr_path"
                )


class TestGetThemePattern:
    """get_theme_pattern returns matching pattern or default."""

    def test_known_theme(self):
        pattern = get_theme_pattern("dopeflix")
        assert pattern is THEME_URL_PATTERNS["dopeflix"]

    def test_unknown_theme_returns_default(self):
        pattern = get_theme_pattern("nonexistent_theme")
        assert pattern.popular_path == "/"
        assert pattern.search_method == "GET"

    def test_none_theme_returns_default(self):
        pattern = get_theme_pattern("")  # type: ignore[arg-type]
        assert isinstance(pattern, ThemePattern)


class TestBuildPopularUrl:
    """build_popular_url constructs correct URLs per theme."""

    def test_no_theme(self):
        url = build_popular_url("https://example.com", None)
        assert url == "https://example.com/"

    def test_dopeflix_default_page(self):
        url = build_popular_url("https://example.com", "dopeflix")
        assert url == "https://example.com/home"

    def test_animestream_with_page(self):
        url = build_popular_url("https://example.com", "animestream", page=2)
        assert "/anime/" in url
        assert "page=2" in url

    def test_zorotheme_default(self):
        url = build_popular_url("https://example.com", "zorotheme")
        assert url == "https://example.com/most-popular"

    def test_anikototheme_default(self):
        url = build_popular_url("https://example.com", "anikototheme")
        assert url == "https://example.com/most-viewed"

    def test_wcotheme_default(self):
        url = build_popular_url("https://example.com", "wcotheme")
        assert url == "https://example.com/"

    def test_trailing_slash_stripped(self):
        url = build_popular_url("https://example.com/", "dopeflix")
        assert url == "https://example.com/home"


class TestBuildSearchUrl:
    """build_search_url constructs correct search URLs per theme."""

    def test_no_theme(self):
        url = build_search_url("https://example.com", None, "naruto")
        assert "search" in url
        assert "naruto" in url

    def test_dopeflix_search(self):
        url = build_search_url("https://example.com", "dopeflix", "one piece")
        assert "/filter" in url
        assert "keyword=" in url

    def test_zorotheme_search(self):
        url = build_search_url("https://example.com", "zorotheme", "dragon ball")
        assert "/search" in url
        assert "keyword=" in url

    def test_wcotheme_search(self):
        url = build_search_url("https://example.com", "wcotheme", "bleach")
        assert "/search" in url
        assert "catara=" in url

    def test_search_with_page(self):
        url = build_search_url("https://example.com", "dopeflix", "test", page=3)
        assert "page=3" in url

    def test_query_url_encoded(self):
        url = build_search_url("https://example.com", "zorotheme", "one piece")
        # "one piece" should be URL-encoded
        assert "one+piece" in url or "one%20piece" in url or "one%2Bpiece" in url


class TestBuildLatestUrl:
    """build_latest_url constructs correct latest URLs, or None if unsupported."""

    def test_no_theme(self):
        url = build_latest_url("https://example.com", None)
        assert url == "https://example.com/latest"

    def test_dopeflix_latest(self):
        url = build_latest_url("https://example.com", "dopeflix")
        assert url == "https://example.com/home/"

    def test_animestream_latest(self):
        url = build_latest_url("https://example.com", "animestream")
        assert url is not None and "order=update" in url

    def test_datalifeengine_returns_none(self):
        """datalifeengine does not support latest — should return None."""
        url = build_latest_url("https://example.com", "datalifeengine")
        assert url is None

    def test_pelisplus_returns_none(self):
        """pelisplus does not support latest — should return None."""
        url = build_latest_url("https://example.com", "pelisplus")
        assert url is None

    def test_zorotheme_latest(self):
        url = build_latest_url("https://example.com", "zorotheme")
        assert url is not None and "/top-airing" in url


class TestThemeSpecificPatterns:
    """Test unique properties of specific themes to ensure correctness."""

    def test_wcotheme_post_search(self):
        pattern = THEME_URL_PATTERNS["wcotheme"]
        assert pattern.search_method == "POST"
        assert pattern.search_post_field == "catara"
        assert "konuara" in pattern.search_post_extra

    def test_datalifeengine_post_search(self):
        pattern = THEME_URL_PATTERNS["datalifeengine"]
        assert pattern.search_method == "POST"
        assert pattern.search_post_field == "story"
        assert pattern.search_post_extra.get("do") == "search"

    def test_anilist_graphql(self):
        pattern = THEME_URL_PATTERNS["anilist"]
        assert pattern.is_api_driven is True
        assert pattern.is_js_rendered is True
        assert pattern.search_method == "graphql"
        assert pattern.episode_delivery == "graphql"

    def test_dopeflix_xhr_episode_delivery(self):
        pattern = THEME_URL_PATTERNS["dopeflix"]
        assert pattern.episode_delivery == "xhr"
        assert "/ajax/season/list/{id}" == pattern.episode_xhr_path
        assert pattern.video_delivery == "xhr"

    def test_datalifeengine_no_episodes_no_video(self):
        pattern = THEME_URL_PATTERNS["datalifeengine"]
        assert pattern.supports_latest is False
        assert pattern.supports_episodes is False
        assert pattern.episode_delivery == "none"
        assert pattern.video_delivery == "none"

    def test_anikototheme_xhr_headers(self):
        pattern = THEME_URL_PATTERNS["anikototheme"]
        assert "X-Requested-With" in pattern.xhr_headers
        assert pattern.episode_delivery == "xhr"
        assert pattern.video_delivery == "xhr"
