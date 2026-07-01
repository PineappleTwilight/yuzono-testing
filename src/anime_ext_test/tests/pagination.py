"""Layer 3: Pagination tests — verify page 1 and page 2 return different results."""

from __future__ import annotations

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
class PaginationTest(ExtensionTest):
    """Test that paginated endpoints return different content on different pages."""

    name = "pagination"
    category = "pagination"

    async def run(
        self,
        ext: ExtensionMeta,
        session: aiohttp.ClientSession | None = None,
    ) -> list[TestResult]:
        if session is None:
            return [self._error("pagination_page2", 0, "No HTTP session provided")]
        if not ext.base_url:
            return [self._skip("pagination_page2", 0, "No baseUrl defined")]
        if ext.requires_api_key:
            return [self._skip("pagination_page2", 0, "Requires API key")]

        results: list[TestResult] = []

        if ext.is_multisrc:
            pattern = get_theme_pattern(ext.theme_pkg or "")
            has_page_param = pattern.popular_query_param is not None
            if not has_page_param:
                results.append(self._skip("pagination_page2", 0, "Theme does not use page query param"))
                return results

        results.append(await self._test_pagination(ext, session))
        return results

    async def _test_pagination(
        self, ext: ExtensionMeta, session: aiohttp.ClientSession,
    ) -> TestResult:
        start = time.monotonic()

        url_p1 = build_popular_url(ext.base_url, ext.theme_pkg if ext.is_multisrc else None, page=1)
        url_p2 = build_popular_url(ext.base_url, ext.theme_pkg if ext.is_multisrc else None, page=2)

        try:
            _data1, soup1 = await fetch_html(session, url_p1, self.config)
        except (RetryableError, PermanentError, CloudflareError, Exception) as exc:
            return self._fail("pagination_page2", _ms(start), f"Failed to fetch page 1: {exc}")

        try:
            _data2, soup2 = await fetch_html(session, url_p2, self.config)
        except (RetryableError, PermanentError, CloudflareError, Exception) as exc:
            return self._fail("pagination_page2", _ms(start), f"Failed to fetch page 2: {exc}")

        links_p1 = _extract_anime_hrefs(soup1)
        links_p2 = _extract_anime_hrefs(soup2)

        if not links_p1:
            return self._skip("pagination_page2", _ms(start), "No anime links found on page 1")

        if not links_p2:
            return self._fail(
                "pagination_page2",
                _ms(start),
                "Page 2 returned no anime links",
                detail=f"page1: {len(links_p1)} links, page2: 0 links",
            )

        overlap = len(links_p1 & links_p2)
        total_unique = len(links_p1 | links_p2)

        if total_unique == 0:
            return self._skip("pagination_page2", _ms(start), "No links to compare")

        overlap_ratio = overlap / total_unique

        if overlap_ratio < 1.0:
            return self._pass(
                "pagination_page2",
                _ms(start),
                f"Pages differ: {len(links_p1)} p1, "
                f"{len(links_p2)} p2, {overlap} overlap ({overlap_ratio:.0%})",
            )
        return self._fail(
            "pagination_page2",
            _ms(start),
            f"Pages identical: {overlap} overlapping links out of {total_unique}",
            detail=f"page1_url: {url_p1}, page2_url: {url_p2}",
        )


def _extract_anime_hrefs(soup) -> set[str]:
    anime_patterns = (
        "/anime/", "/watch/", "/title/", "/series/",
        "/show/", "/drama/", "/movie/", "/film/",
    )
    hrefs: set[str] = set()
    for link in soup.select("a[href]"):
        href = link.get("href", "") or ""
        if any(p in href.lower() for p in anime_patterns):
            hrefs.add(href)
    return hrefs


def _ms(start: float) -> float:
    return round((time.monotonic() - start) * 1000, 1)
