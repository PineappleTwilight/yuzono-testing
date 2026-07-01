"""URL path patterns for multisrc themes.

Derived from actual Kotlin source code in lib-multisrc/.
Each theme has known URL paths, CSS selectors, and API behavior
extracted from the ParsedAnimeHttpSource implementations.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ThemePattern:
    """URL pattern template for a multisrc theme."""

    popular_path: str = "/"
    popular_query_param: str | None = None
    search_path: str | None = None
    search_query_param: str = "q"
    latest_path: str | None = None
    details_selector: str = "body"
    episode_selector: str = "a"
    is_js_rendered: bool = False
    is_api_driven: bool = False
    extra_headers: dict[str, str] = field(default_factory=dict)
    search_is_query: bool = True
    popular_needs_navigation: bool = True
    # CSS selector for anime entry links on popular/latest pages
    popular_selector: str = "a[href]"
    # CSS selector for search result links
    search_selector: str = "a[href]"

    # Episode delivery: "inline" = HTML on detail page, "xhr" = AJAX endpoint, "graphql" = API, "none" = not supported
    episode_delivery: str = "inline"

    # XHR/AJAX episode endpoint template (relative to baseUrl).
    # {id} placeholder replaced with the anime ID extracted from detail page.
    # e.g. "/ajax/episode/list/{id}" for zorotheme
    episode_xhr_path: str | None = None

    # XHR headers required for AJAX endpoints
    xhr_headers: dict[str, str] = field(default_factory=dict)

    # Search method: "GET" (default), "POST" (form body), "graphql" (POST JSON)
    search_method: str = "GET"
    # POST form field name for search query (e.g. "story" for datalifeengine, "catara" for wcotheme)
    search_post_field: str | None = None
    # Extra POST form fields (e.g. {"do": "search", "subaction": "search"} for datalifeengine)
    search_post_extra: dict[str, str] = field(default_factory=dict)

    # Video/stream discovery: "iframe" = iframe on episode page, "xhr" = AJAX sources, "none" = not testable
    video_delivery: str = "iframe"

    # Video XHR path template (relative to baseUrl), e.g. "/ajax/episode/sources/{id}"
    video_xhr_path: str | None = None

    # CSS selector for video iframe on episode page
    video_iframe_selector: str = "iframe[src]"

    # Whether theme supports genre/filter pages (False = throws UnsupportedOperationException)
    supports_filters: bool = True

    # Whether theme supports latest updates (False = throws UnsupportedOperationException)
    supports_latest: bool = True

    # Whether theme supports episode lists (False = throws UnsupportedOperationException)
    supports_episodes: bool = True

    # Detail page data field selectors
    detail_title_selector: str = "h1, h2, .title, [itemprop='name']"
    detail_description_selector: str = ".description, .synopsis, [itemprop='description'], .desc, p, .summary"
    detail_thumbnail_selector: str = "img[src]"
    detail_genres_selector: str = ".genres a, [itemprop='genre'] a, .sgeneros a"
    detail_info_selector: str = ".info, .meta, .anisc-info, .detail, [itemprop], .attributes, .stats"

    # Related anime selector (empty = not supported)
    related_selector: str = ""


# Patterns extracted from lib-multisrc/ Kotlin source code.
# Key evidence for each pattern is documented inline.
THEME_URL_PATTERNS: dict[str, ThemePattern] = {
    # DooPlay.kt: popularAnimeRequest = GET(baseUrl), popularAnimeSelector = "article.w_item_a > a"
    # latestUpdatesSelector = searchAnimeSelector, searchAnimeSelector = "div.result-item div.image a"
    # searchAnimeRequest uses /?s= query for text search
    # episodeListSelector = "ul.episodios > li", seasons via "div#seasons > div"
    # videoListParse: throws UnsupportedOperationException
    "dooplay": ThemePattern(
        popular_path="/",
        search_path="/",
        search_query_param="s",
        search_is_query=True,
        latest_path="/",
        details_selector="div.sheader, div.data",
        episode_selector="ul.episodios > li a, div.episode a",
        popular_selector="article.w_item_a > a",
        search_selector="div.result-item div.image a",
        episode_delivery="inline",
        search_method="GET",
        video_delivery="none",
        supports_filters=True,
        supports_latest=True,
        supports_episodes=True,
        detail_title_selector="div.data > h1",
        detail_thumbnail_selector="div.poster > img",
        detail_genres_selector="div.data > div.sgeneros > a",
        detail_description_selector="div.wp-content, .entry-content",
        detail_info_selector="div#info, div.data",
    ),

    # AnimeStream.kt: popularAnimeRequest = GET("$animeListUrl/?page=$page&order=popular")
    # animeListUrl = "$baseUrl/anime", latestUpdatesRequest uses &order=update
    # searchAnimeRequest uses $animeListUrl/?page=$page&...&order=${params.order}
    # episodeListSelector = "div.eplister > ul > li > a"
    # animeDetailsSelector = "div.info-content, div.right ul.data"
    # video: mirrors via select.mirror > option or ul.mirror a[data-em], then Base64 decode
    "animestream": ThemePattern(
        popular_path="/anime/?order=popular",
        popular_query_param="page",
        search_path="/anime/",
        search_query_param="q",
        search_is_query=True,
        latest_path="/anime/?order=update",
        details_selector="div.info-content, div.right ul.data",
        episode_selector="div.eplister > ul > li > a",
        popular_selector="a[href]",
        episode_delivery="inline",
        search_method="GET",
        video_delivery="iframe",
        video_iframe_selector="select.mirror option, iframe[src]",
        supports_filters=True,
        supports_latest=True,
        supports_episodes=True,
        detail_title_selector="h1.entry-title",
        detail_thumbnail_selector="div.thumb > img, div.limage > img",
        detail_genres_selector="div.genxed > a, li:contains(Genre:) a",
        detail_description_selector=".entry-content[itemprop=description], .desc",
        detail_info_selector="div.info-content, div.right ul.data",
    ),

    # WcoTheme.kt: popularAnimeRequest = GET(baseUrl), popularAnimeSelector = "div#sidebar_right2 ul.items > li"
    # latestUpdatesSelector = "div.recent-release:contains(Recent Releases) + div > ul > li"
    # searchAnimeRequest uses POST /search with form body catara=&konuara=series
    # episodeListSelector = "div.cat-eps, div#episodeList a.dark-episode-item"
    "wcotheme": ThemePattern(
        popular_path="/",
        search_path="/search",
        search_query_param="catara",
        search_is_query=True,
        latest_path="/",
        details_selector="div.video-nav, div.anime-info",
        episode_selector="div.cat-eps a, div#episodeList a.dark-episode-item",
        popular_selector="div#sidebar_right2 ul.items > li a",
        search_selector="a[href]",
        episode_delivery="inline",
        search_method="POST",
        search_post_field="catara",
        search_post_extra={"konuara": "series"},
        video_delivery="iframe",
        video_iframe_selector="iframe[src]",
        supports_filters=True,
        supports_latest=True,
        supports_episodes=True,
        detail_title_selector="div.video-title a, div.header-tag h2 a, div.video-title h1",
        detail_thumbnail_selector="div#sidebar_cat img",
        detail_genres_selector="div#sidebar_cat > a",
        detail_description_selector="div#sidebar_cat p",
        detail_info_selector="div#sidebar_cat",
    ),

    # AnikotoTheme.kt: popularAnimeRequest GET /most-viewed?page=N
    # popularAnimeSelector = "div.ani.items > div.item"
    # latestUpdatesSelector = popularAnimeSelector
    # searchAnimeSelector = popularAnimeSelector
    # episodeListSelector = "div.episodes ul > li > a" (via XHR /ajax/episode/list/{id}?vrf=)
    # Video: XHR /ajax/server/list?servers=... (requires VRF encryption)
    "anikototheme": ThemePattern(
        popular_path="/most-viewed",
        popular_query_param="page",
        search_path="/filter",
        search_query_param="keyword",
        search_is_query=True,
        latest_path="/latest-updated",
        details_selector="div.anisc-detail, div.film-detail",
        episode_selector="div.episodes ul > li > a",
        popular_selector="div.ani.items > div.item a",
        search_selector="div.ani.items > div.item a",
        episode_delivery="xhr",
        episode_xhr_path="/ajax/episode/list/{id}",
        xhr_headers={"X-Requested-With": "XMLHttpRequest", "Accept": "application/json, text/javascript, */*; q=0.01"},
        search_method="GET",
        video_delivery="xhr",
        video_xhr_path="/ajax/server/list",
        supports_filters=True,
        supports_latest=True,
        supports_episodes=True,
        detail_title_selector="h1.title, h2.title",
        detail_thumbnail_selector="div.poster img",
        detail_genres_selector="div.bmeta div.meta > div a",
        detail_description_selector="div.synopsis > div.shorting > div.content",
        detail_info_selector="div.bmeta div.meta > div",
        related_selector="section:has(.stitle:contains(Related)) a.item",
    ),

    # DataLifeEngine.kt: popularAnimeSelector = "div#dle-content > div.mov"
    # latestUpdatesRequest: throws UnsupportedOperationException
    # searchAnimeRequest: POST /index.php?do=search with form body story=query
    # episodeList / videoList: not implemented
    "datalifeengine": ThemePattern(
        popular_path="/",
        search_path="/index.php?do=search",
        search_query_param="story",
        search_is_query=True,
        latest_path=None,
        details_selector="div#dle-content div.mov, div.fullstory",
        episode_selector="div.playlists a",
        popular_selector="div#dle-content > div.mov a",
        search_selector="div#dle-content > div.mov a",
        episode_delivery="none",
        search_method="POST",
        search_post_field="story",
        search_post_extra={"do": "search", "subaction": "search"},
        video_delivery="none",
        supports_filters=True,
        supports_latest=False,
        supports_episodes=False,
        detail_title_selector="div#dle-content h2, div.fullstory h1",
        detail_thumbnail_selector="div#dle-content img[src]",
        detail_genres_selector="span[itemprop=genre] a",
        detail_description_selector="span[itemprop=description]",
        detail_info_selector="div.mov-desc",
    ),

    # DopeFlix.kt: popularAnimeSelector based on sectionSelector("Movies"/"TV Shows")
    # filmSelector = "div.flw-item", trendingSelector uses "#trending-*"
    # search: /filter?... or /search/{query} (path segment)
    # Episodes via XHR: /ajax/season/list/{id} then /ajax/season/episodes/{seasonId}
    # Video via XHR: /ajax/episode/servers/{id} and /ajax/episode/sources/{id}
    "dopeflix": ThemePattern(
        popular_path="/home",
        search_path="/filter",
        search_query_param="keyword",
        search_is_query=True,
        latest_path="/home/",
        details_selector="div.detail_page-watch, div.mvi-content",
        episode_selector=".eps-item, .ss-item",
        popular_selector="div.flw-item a",
        search_selector="div.flw-item a",
        episode_delivery="xhr",
        episode_xhr_path="/ajax/season/list/{id}",
        xhr_headers={"X-Requested-With": "XMLHttpRequest", "Accept": "*/*"},
        search_method="GET",
        video_delivery="xhr",
        video_xhr_path="/ajax/episode/sources/{id}",
        supports_filters=True,
        supports_latest=True,
        supports_episodes=True,
        detail_title_selector="div.detail_page-watch h2, .film-name",
        detail_thumbnail_selector="div.film-poster img",
        detail_genres_selector="div.film-detail .elements a",
        detail_description_selector=".description",
        detail_info_selector="div.detail_page-infor",
    ),

    # PelisPlus.kt: supportsLatest=false, latestUpdates throws UnsupportedOperationException
    # searchAnimeSelector = popularAnimeSelector, episodeListSelector throws
    # videoList: 18 iframe extractors (Voe, Okru, Filemoon, etc.)
    "pelisplus": ThemePattern(
        popular_path="/",
        search_path="/search",
        search_query_param="q",
        search_is_query=True,
        latest_path=None,
        details_selector="div.mvi-content",
        episode_selector="ul.TpSvBk li a, div#episode_list a",
        popular_selector="a[href]",
        episode_delivery="none",
        search_method="GET",
        video_delivery="iframe",
        video_iframe_selector="iframe[src]",
        supports_filters=False,
        supports_latest=False,
        supports_episodes=False,
        detail_title_selector="div.mvi-content h1",
        detail_thumbnail_selector="div.mvi-content img",
        detail_genres_selector="div.mvi-content .genres a",
        detail_description_selector="div.mvi-content .description",
        detail_info_selector="div.mvi-content",
    ),

    # ZoroTheme.kt: popularAnimeRequest = GET("$baseUrl/most-popular?page=$page")
    # popularAnimeSelector = "div.flw-item", latestUpdatesRequest = GET("$baseUrl/top-airing?page=$page")
    # searchAnimeRequest uses /search?keyword=... or /filter with query params
    # Episode list via XHR: /ajax/episode/list/{id}
    # Video servers/sources via XHR
    "zorotheme": ThemePattern(
        popular_path="/most-popular",
        popular_query_param="page",
        search_path="/search",
        search_query_param="keyword",
        search_is_query=True,
        latest_path="/top-airing",
        details_selector="div.anisc-info",
        episode_selector="a.ep-item",
        popular_selector="div.flw-item a",
        search_selector="div.flw-item a",
        episode_delivery="xhr",
        episode_xhr_path="/ajax/episode/list/{id}",
        xhr_headers={"X-Requested-With": "XMLHttpRequest", "Accept": "*/*"},
        search_method="GET",
        video_delivery="xhr",
        video_xhr_path="/ajax/episode/sources?id={id}",
        supports_filters=True,
        supports_latest=True,
        supports_episodes=True,
        detail_title_selector="div.anisc-info h2, .film-name",
        detail_thumbnail_selector="div.anisc-poster img[src]",
        detail_genres_selector="div.anisc-info .genres a",
        detail_description_selector="div.anisc-info .description",
        detail_info_selector="div.anisc-info",
        related_selector=(
            ".block_area_sidebar .block_area-header:contains(Related Anime) "
            "+ .block_area-content ul > li a"
        ),
    ),

    # AnimeKaiTheme.kt: popularAnimeRequest = GET("$baseUrl/trending?page=$page")
    # popularAnimeSelector (abstract, but shared), latestUpdatesRequest = GET("$baseUrl/updates?page=$page")
    # searchAnimeRequest uses /browser?keyword=...
    # Episode list via XHR: /ajax/episodes/list?ani_id={id}&_={enc}
    # Video via XHR: /ajax/links/list?token=...&_=... then /ajax/links/view?id=...
    "animekaitheme": ThemePattern(
        popular_path="/trending",
        popular_query_param="page",
        search_path="/browser",
        search_query_param="keyword",
        search_is_query=True,
        latest_path="/updates",
        details_selector="div.anisc-detail, div[data-id]",
        episode_selector="div.eplist a",
        popular_selector="a.aitem",
        search_selector="a.aitem",
        episode_delivery="xhr",
        episode_xhr_path="/ajax/episodes/list",
        xhr_headers={"X-Requested-With": "XMLHttpRequest", "Accept": "application/json, text/javascript, */*; q=0.01"},
        search_method="GET",
        video_delivery="xhr",
        video_xhr_path="/ajax/links/view",
        supports_filters=True,
        supports_latest=True,
        supports_episodes=True,
        detail_title_selector="div.anisc-detail h2, .film-name",
        detail_thumbnail_selector="div.anisc-poster img",
        detail_genres_selector="div.anisc-info .genres a",
        detail_description_selector="div.anisc-info .description",
        detail_info_selector="div.anisc-info",
        related_selector="#related-anime .aitem-col a.aitem",
    ),

    # YFlixTheme.kt (extends AnimeHttpSource, not ParsedAnimeHttpSource)
    # popularAnimeRequest = GET("$baseUrl/browser?sort=trending&page=$page")
    # latestUpdatesRequest = GET("$baseUrl/browser?page=$page")
    # searchAnimeRequest uses /browser?keyword=...&page=...
    # moviesSelector = "div.film-section div.item", parseAnimesPage selects "a.poster"
    # Episode list via XHR: /ajax/episodes/list?id={contentId}&_={encryptedId}
    # Video via XHR: /ajax/links/list?eid=... then /ajax/links/view?id=...
    "yflixtheme": ThemePattern(
        popular_path="/browser",
        popular_query_param="page",
        search_path="/browser",
        search_query_param="keyword",
        search_is_query=True,
        latest_path="/browser",
        details_selector="h1.title, ul.mics, div.detail",
        episode_selector="ul.episodes li a",
        popular_selector="div.film-section div.item a.poster",
        search_selector="div.film-section div.item a.poster",
        episode_delivery="xhr",
        episode_xhr_path="/ajax/episodes/list",
        xhr_headers={"Accept": "application/json, text/javascript, */*; q=0.01", "X-Requested-With": "XMLHttpRequest"},
        search_method="GET",
        video_delivery="xhr",
        video_xhr_path="/ajax/links/view",
        supports_filters=True,
        supports_latest=True,
        supports_episodes=True,
        detail_title_selector="h1.title",
        detail_thumbnail_selector="div.poster img",
        detail_genres_selector="ul.mics li:has(a[href*=genre]) a",
        detail_description_selector=".description",
        detail_info_selector="ul.mics",
    ),

    # AniList is API-driven (GraphQL at graphql.anilist.co)
    # All data via POST /graphql with JSON body {query, variables}
    # No HTML scraping — every endpoint is a GraphQL query
    "anilist": ThemePattern(
        popular_path="/",
        search_path="/",
        search_query_param="q",
        search_is_query=True,
        latest_path="/",
        is_api_driven=True,
        is_js_rendered=True,
        details_selector="body",
        episode_selector="a",
        popular_selector="a[href]",
        search_selector="a[href]",
        episode_delivery="graphql",
        search_method="graphql",
        search_post_field="query",
        video_delivery="none",
        supports_filters=True,
        supports_latest=True,
        supports_episodes=True,
    ),
}


def get_theme_pattern(theme_pkg: str) -> ThemePattern:
    """Return the ThemePattern for a given theme package, or a default."""
    return THEME_URL_PATTERNS.get(theme_pkg, ThemePattern())


def build_popular_url(base_url: str, theme_pkg: str | None, page: int = 1) -> str:
    """Build the popular anime URL for a theme."""
    base = base_url.rstrip("/")
    if not theme_pkg:
        return base + "/"
    pattern = get_theme_pattern(theme_pkg)
    url = base + pattern.popular_path
    if pattern.popular_query_param and page > 1:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}{pattern.popular_query_param}={page}"
    return url


def build_search_url(base_url: str, theme_pkg: str | None, query: str, page: int = 1) -> str:
    """Build the search URL for a theme."""
    from urllib.parse import quote_plus

    base = base_url.rstrip("/")
    encoded = quote_plus(query)
    if not theme_pkg:
        return base + f"/search?q={encoded}"
    pattern = get_theme_pattern(theme_pkg)
    if not pattern.search_path:
        return base + f"/search?q={encoded}"
    url = base + pattern.search_path
    sep = "&" if "?" in url else "?"
    url = f"{url}{sep}{pattern.search_query_param}={encoded}"
    if page > 1:
        url = f"{url}&page={page}"
    return url


def build_latest_url(base_url: str, theme_pkg: str | None, page: int = 1) -> str | None:
    """Build the latest updates URL for a theme, or None if not supported."""
    base = base_url.rstrip("/")
    if not theme_pkg:
        return base + "/latest"
    pattern = get_theme_pattern(theme_pkg)
    if not pattern.latest_path:
        return None
    url = base + pattern.latest_path
    if pattern.popular_query_param and page > 1:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}{pattern.popular_query_param}={page}"
    return url
