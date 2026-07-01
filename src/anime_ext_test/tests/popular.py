"""Layer 3: Popular anime tests — verify popularAnime endpoint returns entries."""

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
from anime_ext_test.theme_patterns import build_popular_url


@register_test
class PopularTest(ExtensionTest):
    """Test that the popular anime page loads and contains anime entries."""

    name = "popular"
    category = "popular"

    async def run(
        self,
        ext: ExtensionMeta,
        session: aiohttp.ClientSession | None = None,
    ) -> list[TestResult]:
        if session is None:
            return [self._error("popular_page_load", 0, "No HTTP session provided")]
        if not ext.base_url:
            return [self._skip("popular_page_load", 0, "No baseUrl defined")]

        if ext.requires_api_key:
            return [self._skip("popular_page_load", 0, "Requires API key")]

        results: list[TestResult] = []
        results.append(await self._test_page_load(ext, session))
        if results[-1].status == "pass":
            results.append(await self._test_has_entries(ext, session))

        return results

    async def _test_page_load(self, ext: ExtensionMeta, session: aiohttp.ClientSession) -> TestResult:
        start = time.monotonic()
        url = self._build_popular_url(ext)
        try:
            data, _soup = await fetch_html(session, url, self.config)
            if 200 <= data.status < 300:
                return self._pass("popular_page_load", _ms(start), f"HTTP {data.status} from {url}")
            return self._fail("popular_page_load", _ms(start), f"HTTP {data.status} from {url}")
        except RetryableError as exc:
            return self._fail("popular_page_load", _ms(start), f"Transient error: {exc}")
        except PermanentError as exc:
            return self._fail("popular_page_load", _ms(start), f"HTTP error: {exc}")
        except CloudflareError as exc:
            return self._fail("popular_page_load", _ms(start), f"Cloudflare: {exc}")
        except Exception as exc:
            return self._error("popular_page_load", _ms(start), f"Unexpected: {exc}")

    async def _test_has_entries(self, ext: ExtensionMeta, session: aiohttp.ClientSession) -> TestResult:
        start = time.monotonic()
        url = self._build_popular_url(ext)
        try:
            _data, soup = await fetch_html(session, url, self.config)
            # Look for common anime link patterns: <a href> with typical path segments
            anime_links = soup.select("a[href]")
            # Filter to links that look like anime entries
            entry_links = [
                a for a in anime_links
                if self._looks_like_anime_link(a.get("href", ""), ext)
            ]
            if entry_links:
                return self._pass(
                    "popular_has_entries",
                    _ms(start),
                    f"Found {len(entry_links)} potential anime entry link(s)",
                )
            return self._fail(
                "popular_has_entries",
                _ms(start),
                "No anime entry links found on popular page",
                detail=f"URL: {url}, total links: {len(anime_links)}",
            )
        except (RetryableError, PermanentError, CloudflareError) as exc:
            return self._fail("popular_has_entries", _ms(start), f"Fetch error: {exc}")
        except Exception as exc:
            return self._error("popular_has_entries", _ms(start), f"Unexpected: {exc}")

    @staticmethod
    def _build_popular_url(ext: ExtensionMeta) -> str:
        return build_popular_url(ext.base_url, ext.theme_pkg if ext.is_multisrc else None)

    @staticmethod
    def _looks_like_anime_link(href: str, ext: ExtensionMeta) -> bool:
        """Heuristic: does this href look like an anime detail page link?"""
        if not href:
            return False
        # Ignore navigation, auth, category links
        skip_prefixes = (
            "#", "javascript:", "mailto:", "/login", "/register",
            "/auth", "/category", "/genre", "/tag", "/year",
            "/page", "/sitemap", "/feed", "/rss",
        )
        lower = href.lower()
        if any(lower.startswith(p) for p in skip_prefixes):
            return False
        # Look for common anime URL patterns
        anime_patterns = (
            "/anime/", "/watch/", "/title/", "/series/",
            "/show/", "/drama/", "/movie/", "/film/",
            "/video/", "/episode/",
        )
        return any(p in lower for p in anime_patterns)


def _ms(start: float) -> float:
    return round((time.monotonic() - start) * 1000, 1)
