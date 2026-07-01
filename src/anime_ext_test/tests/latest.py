"""Layer 3: Latest updates tests — verify latestUpdates endpoint returns entries."""

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
from anime_ext_test.theme_patterns import build_latest_url


@register_test
class LatestTest(ExtensionTest):
    """Test that the latest updates page loads and contains entries."""

    name = "latest"
    category = "latest"

    async def run(
        self,
        ext: ExtensionMeta,
        session: aiohttp.ClientSession | None = None,
    ) -> list[TestResult]:
        if session is None:
            return [self._error("latest_page_load", 0, "No HTTP session provided")]
        if not ext.base_url:
            return [self._skip("latest_page_load", 0, "No baseUrl defined")]
        if ext.requires_api_key:
            return [self._skip("latest_page_load", 0, "Requires API key")]

        # Not all themes/sites have a dedicated latest page
        latest_url = self._build_latest_url(ext)
        if not latest_url:
            return [self._skip("latest_page_load", 0, "No known latest path for this theme")]

        results: list[TestResult] = []
        results.append(await self._test_latest_load(ext, session, latest_url))
        if results[-1].status == "pass":
            results.append(await self._test_latest_entries(ext, session, latest_url))

        return results

    async def _test_latest_load(
        self, ext: ExtensionMeta, session: aiohttp.ClientSession, url: str,
    ) -> TestResult:
        start = time.monotonic()
        try:
            data, _soup = await fetch_html(session, url, self.config)
            if 200 <= data.status < 300:
                return self._pass("latest_page_load", _ms(start), f"HTTP {data.status}")
            return self._fail("latest_page_load", _ms(start), f"HTTP {data.status}")
        except RetryableError as exc:
            return self._fail("latest_page_load", _ms(start), f"Transient: {exc}")
        except PermanentError as exc:
            return self._fail("latest_page_load", _ms(start), f"HTTP error: {exc}")
        except CloudflareError as exc:
            return self._fail("latest_page_load", _ms(start), f"Cloudflare: {exc}")
        except Exception as exc:
            return self._error("latest_page_load", _ms(start), f"Unexpected: {exc}")

    async def _test_latest_entries(
        self, ext: ExtensionMeta, session: aiohttp.ClientSession, url: str,
    ) -> TestResult:
        start = time.monotonic()
        try:
            _data, soup = await fetch_html(session, url, self.config)
            links = soup.select("a[href]")
            # Use same heuristic as popular page: look for anime entry links
            anime_patterns = (
                "/anime/", "/watch/", "/title/", "/series/",
                "/show/", "/drama/", "/movie/", "/film/",
            )
            entry_links = [
                a for a in links
                if any(p in (a.get("href", "") or "").lower() for p in anime_patterns)
            ]
            if entry_links:
                return self._pass(
                    "latest_has_entries",
                    _ms(start),
                    f"Found {len(entry_links)} entry link(s)",
                )
            return self._fail(
                "latest_has_entries",
                _ms(start),
                "No anime entries found on latest page",
            )
        except (RetryableError, PermanentError, CloudflareError) as exc:
            return self._fail("latest_has_entries", _ms(start), f"Fetch error: {exc}")
        except Exception as exc:
            return self._error("latest_has_entries", _ms(start), f"Unexpected: {exc}")

    @staticmethod
    def _build_latest_url(ext: ExtensionMeta) -> str | None:
        return build_latest_url(ext.base_url, ext.theme_pkg if ext.is_multisrc else None)


def _ms(start: float) -> float:
    return round((time.monotonic() - start) * 1000, 1)
