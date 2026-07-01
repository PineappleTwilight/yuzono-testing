"""Layer 3: Search anime tests — verify searchAnime endpoint returns results."""

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
from anime_ext_test.theme_patterns import build_search_url

# Generic search terms with high hit rates across anime sites
DEFAULT_SEARCH_TERMS = ["naruto", "one piece", "dragon"]


@register_test
class SearchTest(ExtensionTest):
    """Test that the search endpoint works and returns results."""

    name = "search"
    category = "search"

    async def run(
        self,
        ext: ExtensionMeta,
        session: aiohttp.ClientSession | None = None,
    ) -> list[TestResult]:
        if session is None:
            return [self._error("search_page_load", 0, "No HTTP session provided")]
        if not ext.base_url:
            return [self._skip("search_page_load", 0, "No baseUrl defined")]
        if ext.requires_api_key:
            return [self._skip("search_page_load", 0, "Requires API key")]

        results: list[TestResult] = []
        results.append(await self._test_search_load(ext, session))
        if results[-1].status == "pass":
            results.append(await self._test_search_results(ext, session))

        return results

    async def _test_search_load(
        self, ext: ExtensionMeta, session: aiohttp.ClientSession,
    ) -> TestResult:
        start = time.monotonic()
        url = self._build_search_url(ext, DEFAULT_SEARCH_TERMS[0])
        try:
            data, _soup = await fetch_html(session, url, self.config)
            if 200 <= data.status < 300:
                return self._pass("search_page_load", _ms(start), f"HTTP {data.status} from {url}")
            return self._fail("search_page_load", _ms(start), f"HTTP {data.status} from {url}")
        except RetryableError as exc:
            return self._fail("search_page_load", _ms(start), f"Transient error: {exc}")
        except PermanentError as exc:
            return self._fail("search_page_load", _ms(start), f"HTTP error: {exc}")
        except CloudflareError as exc:
            return self._fail("search_page_load", _ms(start), f"Cloudflare: {exc}")
        except Exception as exc:
            return self._error("search_page_load", _ms(start), f"Unexpected: {exc}")

    async def _test_search_results(
        self, ext: ExtensionMeta, session: aiohttp.ClientSession,
    ) -> TestResult:
        start = time.monotonic()
        # Try each search term until we find results
        for term in DEFAULT_SEARCH_TERMS:
            url = self._build_search_url(ext, term)
            try:
                _data, soup = await fetch_html(session, url, self.config)
                anime_links = soup.select("a[href]")
                entry_links = [
                    a for a in anime_links
                    if self._looks_like_anime_link(a.get("href", ""), ext)
                ]
                if entry_links:
                    return self._pass(
                        "search_has_results",
                        _ms(start),
                        f"Found {len(entry_links)} result(s) for '{term}'",
                    )
            except (RetryableError, PermanentError, CloudflareError):
                continue
            except Exception:
                continue

        return self._fail(
            "search_has_results",
            _ms(start),
            f"No search results found for any term: {DEFAULT_SEARCH_TERMS}",
        )

    @staticmethod
    def _build_search_url(ext: ExtensionMeta, query: str) -> str:
        return build_search_url(ext.base_url, ext.theme_pkg if ext.is_multisrc else None, query)

    @staticmethod
    def _looks_like_anime_link(href: str, ext: ExtensionMeta) -> bool:
        if not href:
            return False
        skip_prefixes = (
            "#", "javascript:", "mailto:", "/login", "/register",
            "/auth", "/category", "/genre", "/tag", "/year",
        )
        lower = href.lower()
        if any(lower.startswith(p) for p in skip_prefixes):
            return False
        anime_patterns = (
            "/anime/", "/watch/", "/title/", "/series/",
            "/show/", "/drama/", "/movie/", "/film/",
        )
        return any(p in lower for p in anime_patterns)


def _ms(start: float) -> float:
    return round((time.monotonic() - start) * 1000, 1)
