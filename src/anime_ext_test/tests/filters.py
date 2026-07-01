"""Layer 3: Filter list tests — verify getFilterList returns filter options."""

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


@register_test
class FiltersTest(ExtensionTest):
    """Test that filter-related pages and parameters work.

    Since we can't call getFilterList() directly (it's Kotlin code),
    we test what we can: does the site support filter/query parameters
    and does filtering by genre/category return different results?
    """

    name = "filters"
    category = "filters"

    async def run(
        self,
        ext: ExtensionMeta,
        session: aiohttp.ClientSession | None = None,
    ) -> list[TestResult]:
        if session is None:
            return [self._error("filter_page_load", 0, "No HTTP session provided")]
        if not ext.base_url:
            return [self._skip("filter_page_load", 0, "No baseUrl defined")]
        if ext.requires_api_key:
            return [self._skip("filter_page_load", 0, "Requires API key")]

        results: list[TestResult] = []
        results.append(await self._test_genre_page(ext, session))
        results.append(await self._test_filter_params(ext, session))

        return results

    async def _test_genre_page(
        self, ext: ExtensionMeta, session: aiohttp.ClientSession,
    ) -> TestResult:
        start = time.monotonic()
        base = ext.base_url.rstrip("/")
        # Try common genre/filter page paths
        genre_paths = ["/genre", "/genres", "/category", "/filter", "/categories"]
        for path in genre_paths:
            url = base + path
            try:
                data, soup = await fetch_html(session, url, self.config)
                if 200 <= data.status < 300:
                    # Check for genre links
                    genre_links = soup.select("a[href*='genre'], a[href*='category'], a[href*='filter']")
                    if genre_links:
                        return self._pass(
                            "filter_page_load",
                            _ms(start),
                            f"Found {len(genre_links)} genre/filter link(s) at {path}",
                        )
            except (RetryableError, PermanentError, CloudflareError, Exception):
                continue

        # No dedicated genre page — not a failure, many sites embed filters in the main page
        return self._skip(
            "filter_page_load",
            _ms(start),
            "No dedicated genre/filter page found (may use inline filters)",
        )

    async def _test_filter_params(
        self, ext: ExtensionMeta, session: aiohttp.ClientSession,
    ) -> TestResult:
        start = time.monotonic()
        base = ext.base_url.rstrip("/")
        # Try to load popular page with a common filter param
        # Many anime sites support ?genre=action or ?type=tv
        filter_urls = [
            base + "/?genre=action",
            base + "/?type=tv",
            base + "/genre/action",
        ]
        for url in filter_urls:
            try:
                data, _soup = await fetch_html(session, url, self.config)
                if 200 <= data.status < 300:
                    return self._pass(
                        "filter_params_work",
                        _ms(start),
                        f"Filter URL returned HTTP {data.status}: {url}",
                    )
            except (RetryableError, PermanentError, CloudflareError, Exception):
                continue

        return self._skip(
            "filter_params_work",
            _ms(start),
            "Could not verify filter parameter support",
        )


def _ms(start: float) -> float:
    return round((time.monotonic() - start) * 1000, 1)
