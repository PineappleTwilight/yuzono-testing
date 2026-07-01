"""Layer 3: Video stream tests — verify video/stream endpoint responds (iframe, XHR, or skip)."""

from __future__ import annotations

import re
import time

import aiohttp

from anime_ext_test.http_client import (
    CloudflareError,
    PermanentError,
    RetryableError,
    fetch_html,
    fetch_json,
)
from anime_ext_test.models import ExtensionMeta, TestResult
from anime_ext_test.tests.registry import ExtensionTest, register_test
from anime_ext_test.theme_patterns import build_popular_url, get_theme_pattern


@register_test
class VideoStreamsTest(ExtensionTest):
    """Test video/stream discovery — iframe on episode page, XHR sources, or skip."""

    name = "video_streams"
    category = "video_streams"

    async def run(
        self,
        ext: ExtensionMeta,
        session: aiohttp.ClientSession | None = None,
    ) -> list[TestResult]:
        if session is None:
            return [self._error("video_stream_delivery", 0, "No HTTP session provided")]
        if not ext.base_url:
            return [self._skip("video_stream_delivery", 0, "No baseUrl defined")]
        if ext.requires_api_key:
            return [self._skip("video_stream_delivery", 0, "Requires API key")]

        if not ext.is_multisrc:
            return [self._skip("video_stream_delivery", 0, "Non-multisrc: use generic episode test")]

        pattern = get_theme_pattern(ext.theme_pkg or "")

        if pattern.video_delivery == "none":
            return [self._skip("video_stream_delivery", 0, "Theme video_delivery=none")]

        detail_url = await self._find_detail_url(ext, session)
        if not detail_url:
            return [self._skip("video_stream_delivery", 0, "Could not find a detail page URL")]

        episode_url = await self._find_episode_url(ext, session, detail_url)
        if not episode_url:
            return [self._skip("video_stream_delivery", 0, "Could not find an episode URL")]

        results: list[TestResult] = []

        if pattern.video_delivery == "iframe":
            results.append(await self._test_iframe(ext, session, episode_url))
        elif pattern.video_delivery == "xhr":
            results.append(await self._test_iframe(ext, session, episode_url))
            results.append(await self._test_xhr_sources(ext, session, episode_url))
        else:
            results.append(self._skip("video_stream_delivery", 0, f"Unknown video_delivery: {pattern.video_delivery}"))

        return results

    async def _test_iframe(
        self, ext: ExtensionMeta, session: aiohttp.ClientSession, episode_url: str,
    ) -> TestResult:
        start = time.monotonic()
        try:
            _data, soup = await fetch_html(session, episode_url, self.config)
            pattern = get_theme_pattern(ext.theme_pkg or "")
            selector = pattern.video_iframe_selector
            iframes = soup.select(selector)

            for iframe in iframes:
                src = iframe.get("src") or iframe.get("data-src") or iframe.get("data-lazy-src")
                if src and _is_video_source(src):
                    return self._pass(
                        "video_stream_iframe",
                        _ms(start),
                        f"Found video iframe src: {src[:80]}",
                    )

            if iframes:
                srcs = [iframe.get("src", "")[:40] for iframe in iframes[:3]]
                return self._fail(
                    "video_stream_iframe",
                    _ms(start),
                    "Found iframes but none point to video sources",
                    detail=f"selector: {selector}, srcs: {srcs}",
                )
            return self._fail(
                "video_stream_iframe",
                _ms(start),
                "No video iframes found on episode page",
                detail=f"selector: {selector}, URL: {episode_url}",
            )
        except RetryableError as exc:
            return self._fail("video_stream_iframe", _ms(start), f"Transient: {exc}")
        except PermanentError as exc:
            return self._fail("video_stream_iframe", _ms(start), f"HTTP error: {exc}")
        except CloudflareError as exc:
            return self._fail("video_stream_iframe", _ms(start), f"Cloudflare: {exc}")
        except Exception as exc:
            return self._error("video_stream_iframe", _ms(start), f"Unexpected: {exc}")

    async def _test_xhr_sources(
        self, ext: ExtensionMeta, session: aiohttp.ClientSession, episode_url: str,
    ) -> TestResult:
        start = time.monotonic()
        pattern = get_theme_pattern(ext.theme_pkg or "")

        if not pattern.video_xhr_path:
            return self._skip("video_stream_xhr", _ms(start), "No video XHR path defined for theme")

        base = ext.base_url.rstrip("/")
        episode_id = self._extract_episode_id(episode_url)

        if not episode_id:
            return self._skip("video_stream_xhr", _ms(start), "Could not extract episode ID from URL")

        xhr_url = base + pattern.video_xhr_path.replace("{id}", str(episode_id))
        headers = dict(pattern.xhr_headers) if pattern.xhr_headers else {}

        try:
            data, parsed = await fetch_json(session, xhr_url, self.config, headers=headers)
            if _has_video_sources(parsed):
                source_count = _count_video_sources(parsed)
                return self._pass(
                    "video_stream_xhr",
                    _ms(start),
                    f"XHR endpoint returned {source_count} video source(s)",
                )
            return self._fail(
                "video_stream_xhr",
                _ms(start),
                "XHR endpoint returned JSON but no video sources",
                detail=f"url: {xhr_url}",
            )
        except PermanentError as exc:
            return self._fail("video_stream_xhr", _ms(start), f"HTTP error: {exc}")
        except CloudflareError as exc:
            return self._fail("video_stream_xhr", _ms(start), f"Cloudflare: {exc}")
        except RetryableError as exc:
            return self._fail("video_stream_xhr", _ms(start), f"Transient: {exc}")
        except Exception as exc:
            return self._skip("video_stream_xhr", _ms(start), f"XHR video test skipped: {exc}")

    async def _find_detail_url(
        self, ext: ExtensionMeta, session: aiohttp.ClientSession,
    ) -> str | None:
        base = ext.base_url.rstrip("/")
        popular_url = build_popular_url(ext.base_url, ext.theme_pkg if ext.is_multisrc else None)

        try:
            _data, soup = await fetch_html(session, popular_url, self.config)
        except (RetryableError, PermanentError, CloudflareError, Exception):
            return None

        for link in soup.select("a[href]"):
            href = link.get("href", "")
            if self._is_detail_link(href, ext):
                if href.startswith("/"):
                    return base + href
                if href.startswith("http"):
                    return href
        return None

    async def _find_episode_url(
        self, ext: ExtensionMeta, session: aiohttp.ClientSession, detail_url: str,
    ) -> str | None:
        base = ext.base_url.rstrip("/")
        try:
            _data, soup = await fetch_html(session, detail_url, self.config)
        except (RetryableError, PermanentError, CloudflareError, Exception):
            return None

        pattern = get_theme_pattern(ext.theme_pkg or "")
        elements = soup.select(pattern.episode_selector)

        for el in elements:
            href = el.get("href", "")
            if href and _is_episode_link(href):
                if href.startswith("/"):
                    return base + href
                if href.startswith("http"):
                    return href
        return None

    @staticmethod
    def _is_detail_link(href: str, ext: ExtensionMeta) -> bool:
        if not href or href.startswith("#") or href.startswith("javascript:"):
            return False
        lower = href.lower()
        detail_patterns = [
            r"/anime/\w", r"/title/\w", r"/series/\w", r"/show/\w",
            r"/watch/\w", r"/drama/\w", r"/movie/\d", r"/film/\w",
            r"/video/\w",
        ]
        return any(re.search(p, lower) for p in detail_patterns)

    @staticmethod
    def _extract_episode_id(url: str) -> str | None:
        match = re.search(r"/(?:episode|ep|watch|video)/(\d+)", url)
        if match:
            return match.group(1)
        match = re.search(r"[?&](?:id|ep)=(\d+)", url)
        if match:
            return match.group(1)
        match = re.search(r"/(\d+)(?:/|$)", url)
        if match:
            return match.group(1)
        return None


def _is_video_source(src: str) -> bool:
    video_hosts = [
        "streamable", "voe", "okru", "filemoon", "streamtape",
        "mp4upload", "vidcdn", "streamsb", "doodstream",
        "xstreamcdn", "goload", "streaming", "vidstream",
        "player", "embed", "video", "cdn",
    ]
    lower = src.lower()
    return any(h in lower for h in video_hosts)


def _is_episode_link(href: str) -> bool:
    lower = (href or "").lower()
    indicators = ["episode", "ep-", "ep_", "/watch/", "/play/", "/video/"]
    return any(ind in lower for ind in indicators)


def _has_video_sources(parsed) -> bool:
    if isinstance(parsed, dict):
        for key in ("sources", "data", "result", "html", "items", "list"):
            val = parsed.get(key)
            if val:
                return True
        if "link" in parsed or "url" in parsed or "src" in parsed:
            return True
    return isinstance(parsed, list) or bool(isinstance(parsed, str) and len(parsed) > 50)


def _count_video_sources(parsed) -> int:
    if isinstance(parsed, dict):
        sources = parsed.get("sources")
        if isinstance(sources, list):
            return len(sources)
        data = parsed.get("data")
        if isinstance(data, list):
            return len(data)
    if isinstance(parsed, list):
        return len(parsed)
    return 0


def _ms(start: float) -> float:
    return round((time.monotonic() - start) * 1000, 1)
