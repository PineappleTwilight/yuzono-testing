"""Layer 3: Series detail field tests — verify individual data fields on detail pages."""

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
class SeriesDetailsTest(ExtensionTest):
    """Test that detail pages contain specific data fields (title, description, thumbnail, genres)."""

    name = "series_details"
    category = "series_details"

    async def run(
        self,
        ext: ExtensionMeta,
        session: aiohttp.ClientSession | None = None,
    ) -> list[TestResult]:
        if session is None:
            return [self._error("detail_title", 0, "No HTTP session provided")]
        if not ext.base_url:
            return [self._skip("detail_title", 0, "No baseUrl defined")]
        if ext.requires_api_key:
            return [self._skip("detail_title", 0, "Requires API key")]

        detail_url = await self._find_detail_url(ext, session)
        if not detail_url:
            return [
                self._skip("detail_title", 0, "Could not find a detail page URL"),
                self._skip("detail_description", 0, "No detail URL found"),
                self._skip("detail_thumbnail", 0, "No detail URL found"),
                self._skip("detail_genres", 0, "No detail URL found"),
            ]

        results: list[TestResult] = []
        results.append(await self._test_title(ext, session, detail_url))
        results.append(await self._test_description(ext, session, detail_url))
        results.append(await self._test_thumbnail(ext, session, detail_url))
        results.append(await self._test_genres(ext, session, detail_url))
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

        for link in soup.select("a[href]"):
            href = link.get("href", "")
            if self._is_detail_link(href, ext):
                if href.startswith("/"):
                    return base + href
                if href.startswith("http"):
                    return href
        return None

    async def _test_title(
        self, ext: ExtensionMeta, session: aiohttp.ClientSession, url: str,
    ) -> TestResult:
        return await self._check_selector(
            ext, session, url,
            test_name="detail_title",
            selector_attr="detail_title_selector",
            validation=lambda el: bool(el.get_text(strip=True)),
            fail_msg="No title text found on detail page",
        )

    async def _test_description(
        self, ext: ExtensionMeta, session: aiohttp.ClientSession, url: str,
    ) -> TestResult:
        return await self._check_selector(
            ext, session, url,
            test_name="detail_description",
            selector_attr="detail_description_selector",
            validation=lambda el: len(el.get_text(strip=True)) > 20,
            fail_msg="Description too short or missing on detail page",
        )

    async def _test_thumbnail(
        self, ext: ExtensionMeta, session: aiohttp.ClientSession, url: str,
    ) -> TestResult:
        return await self._check_selector(
            ext, session, url,
            test_name="detail_thumbnail",
            selector_attr="detail_thumbnail_selector",
            validation=lambda el: bool(el.get("src") or el.get("data-src") or el.get("data-lazy-src")),
            fail_msg="No thumbnail image found on detail page",
        )

    async def _test_genres(
        self, ext: ExtensionMeta, session: aiohttp.ClientSession, url: str,
    ) -> TestResult:
        return await self._check_selector(
            ext, session, url,
            test_name="detail_genres",
            selector_attr="detail_genres_selector",
            validation=lambda els: len(els) > 0,
            multi=True,
            fail_msg="No genre links found on detail page",
        )

    async def _check_selector(
        self,
        ext: ExtensionMeta,
        session: aiohttp.ClientSession,
        url: str,
        *,
        test_name: str,
        selector_attr: str,
        validation,
        fail_msg: str,
        multi: bool = False,
    ) -> TestResult:
        start = time.monotonic()
        try:
            _data, soup = await fetch_html(session, url, self.config)

            if ext.is_multisrc:
                pattern = get_theme_pattern(ext.theme_pkg or "")
                selector = getattr(pattern, selector_attr, None) or ""
            else:
                selector = ""

            if not selector:
                return self._skip(test_name, _ms(start), f"No theme selector for {selector_attr}")

            elements = soup.select(selector)
            if not elements:
                return self._fail(test_name, _ms(start), fail_msg, detail=f"selector: {selector}")

            if multi:
                if validation(elements):
                    return self._pass(
                        test_name, _ms(start),
                        f"Found {len(elements)} element(s) with selector: {selector}",
                    )
            else:
                if validation(elements[0]):
                    text = elements[0].get_text(strip=True)[:80]
                    return self._pass(test_name, _ms(start), f"Found: {text!r}")

            return self._fail(test_name, _ms(start), fail_msg, detail=f"selector: {selector}")
        except RetryableError as exc:
            return self._fail(test_name, _ms(start), f"Transient: {exc}")
        except PermanentError as exc:
            return self._fail(test_name, _ms(start), f"HTTP error: {exc}")
        except CloudflareError as exc:
            return self._fail(test_name, _ms(start), f"Cloudflare: {exc}")
        except Exception as exc:
            return self._error(test_name, _ms(start), f"Unexpected: {exc}")

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


def _ms(start: float) -> float:
    return round((time.monotonic() - start) * 1000, 1)
