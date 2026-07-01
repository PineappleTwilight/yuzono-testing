"""Layer 3: Anime details tests — verify animeDetails returns structured info."""

from __future__ import annotations

import re
import time

import aiohttp

from anime_ext_test.http_client import (
    CloudflareError,
    PermanentError,
    RetryableError,
    fetch_html,
)
from anime_ext_test.models import ExtensionMeta, TestResult
from anime_ext_test.tests.registry import ExtensionTest, register_test
from anime_ext_test.theme_patterns import build_popular_url, get_theme_pattern


@register_test
class DetailsTest(ExtensionTest):
    """Test that an anime detail page loads and has expected content."""

    name = "details"
    category = "details"

    async def run(
        self,
        ext: ExtensionMeta,
        session: aiohttp.ClientSession | None = None,
    ) -> list[TestResult]:
        if session is None:
            return [self._error("detail_page_load", 0, "No HTTP session provided")]
        if not ext.base_url:
            return [self._skip("detail_page_load", 0, "No baseUrl defined")]
        if ext.requires_api_key:
            return [self._skip("detail_page_load", 0, "Requires API key")]

        results: list[TestResult] = []

        # First, find a detail URL from the popular page
        detail_url = await self._find_detail_url(ext, session)
        if not detail_url:
            results.append(self._skip("detail_page_load", 0, "Could not find a detail page URL"))
            results.append(self._skip("detail_has_content", 0, "No detail URL found"))
            return results

        results.append(await self._test_detail_load(ext, session, detail_url))
        if results[-1].status == "pass":
            results.append(await self._test_detail_content(ext, session, detail_url))

        return results

    async def _find_detail_url(
        self, ext: ExtensionMeta, session: aiohttp.ClientSession,
    ) -> str | None:
        base = ext.base_url.rstrip("/")
        popular_url = build_popular_url(ext.base_url, ext.theme_pkg if ext.is_multisrc else None)

        try:
            _data, soup = await fetch_html(session, popular_url, self.config)
        except (RetryableError, PermanentError, CloudflareError, Exception):
            return None

        anime_links = soup.select("a[href]")
        for link in anime_links:
            href = link.get("href", "")
            if self._is_detail_link(href, ext):
                if href.startswith("/"):
                    return base + href
                if href.startswith("http"):
                    return href
        return None

    async def _test_detail_load(
        self, ext: ExtensionMeta, session: aiohttp.ClientSession, url: str,
    ) -> TestResult:
        start = time.monotonic()
        try:
            data, _soup = await fetch_html(session, url, self.config)
            if 200 <= data.status < 300:
                return self._pass("detail_page_load", _ms(start), f"HTTP {data.status}")
            return self._fail("detail_page_load", _ms(start), f"HTTP {data.status}")
        except RetryableError as exc:
            return self._fail("detail_page_load", _ms(start), f"Transient: {exc}")
        except PermanentError as exc:
            return self._fail("detail_page_load", _ms(start), f"HTTP error: {exc}")
        except CloudflareError as exc:
            return self._fail("detail_page_load", _ms(start), f"Cloudflare: {exc}")
        except Exception as exc:
            return self._error("detail_page_load", _ms(start), f"Unexpected: {exc}")

    async def _test_detail_content(
        self, ext: ExtensionMeta, session: aiohttp.ClientSession, url: str,
    ) -> TestResult:
        start = time.monotonic()
        try:
            _data, soup = await fetch_html(session, url, self.config)

            if ext.is_multisrc:
                pattern = get_theme_pattern(ext.theme_pkg or "")
                title_sel = pattern.detail_title_selector
                desc_sel = pattern.detail_description_selector
                thumb_sel = pattern.detail_thumbnail_selector
                genres_sel = pattern.detail_genres_selector
            else:
                title_sel = "h1, h2, h3, .title, [itemprop='name']"
                desc_sel = ".description, .synopsis, [itemprop='description'], .desc, p, .summary"
                thumb_sel = "img[src]"
                genres_sel = ".genres a, [itemprop='genre'] a, .sgeneros a"

            has_title = bool(soup.select(title_sel))
            has_desc = bool(soup.select(desc_sel))
            has_thumb = bool(soup.select(thumb_sel))
            has_genres = bool(soup.select(genres_sel))

            score = sum([has_title, has_desc, has_thumb, has_genres])
            found = []
            if has_title:
                found.append("title")
            if has_desc:
                found.append("description")
            if has_thumb:
                found.append("thumbnail")
            if has_genres:
                found.append("genres")

            if score >= 2:
                return self._pass(
                    "detail_has_content",
                    _ms(start),
                    f"Detail page has {score}/4 fields: {', '.join(found)}",
                )
            if score == 1:
                return self._pass(
                    "detail_has_content",
                    _ms(start),
                    f"Detail page has minimal content (1 field: {found[0]})",
                )
            return self._fail(
                "detail_has_content",
                _ms(start),
                "Detail page lacks expected content fields",
                detail=f"URL: {url}, title_sel: {title_sel}, desc_sel: {desc_sel}",
            )
        except (RetryableError, PermanentError, CloudflareError) as exc:
            return self._fail("detail_has_content", _ms(start), f"Fetch error: {exc}")
        except Exception as exc:
            return self._error("detail_has_content", _ms(start), f"Unexpected: {exc}")

    @staticmethod
    def _is_detail_link(href: str, ext: ExtensionMeta) -> bool:
        """Heuristic: does this href point to an anime detail page?"""
        if not href or href.startswith("#") or href.startswith("javascript:"):
            return False
        lower = href.lower()
        # Must contain a slug-like segment (numbers, letters, hyphens)
        detail_patterns = [
            r"/anime/\w", r"/title/\w", r"/series/\w", r"/show/\w",
            r"/watch/\w", r"/drama/\w", r"/movie/\d", r"/film/\w",
            r"/video/\w",
        ]
        return any(re.search(p, lower) for p in detail_patterns)


def _ms(start: float) -> float:
    return round((time.monotonic() - start) * 1000, 1)
