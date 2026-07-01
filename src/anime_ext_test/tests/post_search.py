"""Layer 3: POST search tests — verify POST-based search (datalifeengine, wcotheme, graphql)."""

from __future__ import annotations

import time

import aiohttp

from anime_ext_test.http_client import (
    CloudflareError,
    PermanentError,
    RetryableError,
    fetch_html,
    fetch_with_headers,
)
from anime_ext_test.models import ExtensionMeta, TestResult
from anime_ext_test.tests.registry import ExtensionTest, register_test
from anime_ext_test.theme_patterns import get_theme_pattern

DEFAULT_SEARCH_TERMS = ["naruto", "one piece", "dragon"]


@register_test
class PostSearchTest(ExtensionTest):
    """Test POST-based search endpoints — form POST, and GraphQL-style search."""

    name = "post_search"
    category = "post_search"

    async def run(
        self,
        ext: ExtensionMeta,
        session: aiohttp.ClientSession | None = None,
    ) -> list[TestResult]:
        if session is None:
            return [self._error("post_search_load", 0, "No HTTP session provided")]
        if not ext.base_url:
            return [self._skip("post_search_load", 0, "No baseUrl defined")]
        if ext.requires_api_key:
            return [self._skip("post_search_load", 0, "Requires API key")]

        if not ext.is_multisrc:
            return [self._skip("post_search_load", 0, "Non-multisrc extension: no POST search pattern")]

        pattern = get_theme_pattern(ext.theme_pkg or "")

        if pattern.search_method == "GET":
            return [self._skip("post_search_load", 0, "Theme uses GET search, not POST")]

        results: list[TestResult] = []

        if pattern.search_method == "POST":
            results.append(await self._test_form_post(ext, session, pattern))
            if results[-1].status == "pass":
                results.append(await self._test_form_post_results(ext, session, pattern))
        elif pattern.search_method == "graphql":
            results.append(await self._test_graphql(ext, session, pattern))
        else:
            results.append(self._skip("post_search_load", 0, f"Unknown search_method: {pattern.search_method}"))

        return results

    async def _test_form_post(
        self,
        ext: ExtensionMeta,
        session: aiohttp.ClientSession,
        pattern,
    ) -> TestResult:
        start = time.monotonic()
        base = ext.base_url.rstrip("/")
        url = base + (pattern.search_path or "/")

        form_data = {}
        if pattern.search_post_field:
            form_data[pattern.search_post_field] = DEFAULT_SEARCH_TERMS[0]
        if pattern.search_post_extra:
            form_data.update(pattern.search_post_extra)

        try:
            _data, soup = await fetch_html(session, url, self.config)
            data = await fetch_with_headers(
                session, url, self.config,
                method="POST",
                data=form_data,
            )
            if 200 <= data.status < 300:
                return self._pass(
                    "post_search_load",
                    _ms(start),
                    f"POST search returned HTTP {data.status}",
                )
            return self._fail("post_search_load", _ms(start), f"POST search returned HTTP {data.status}")
        except RetryableError as exc:
            return self._fail("post_search_load", _ms(start), f"Transient: {exc}")
        except PermanentError as exc:
            return self._fail("post_search_load", _ms(start), f"HTTP error: {exc}")
        except CloudflareError as exc:
            return self._fail("post_search_load", _ms(start), f"Cloudflare: {exc}")
        except Exception as exc:
            return self._error("post_search_load", _ms(start), f"Unexpected: {exc}")

    async def _test_form_post_results(
        self,
        ext: ExtensionMeta,
        session: aiohttp.ClientSession,
        pattern,
    ) -> TestResult:
        start = time.monotonic()
        base = ext.base_url.rstrip("/")
        url = base + (pattern.search_path or "/")

        for term in DEFAULT_SEARCH_TERMS:
            form_data = {}
            if pattern.search_post_field:
                form_data[pattern.search_post_field] = term
            if pattern.search_post_extra:
                form_data.update(pattern.search_post_extra)

            try:
                data = await fetch_with_headers(
                    session, url, self.config,
                    method="POST",
                    data=form_data,
                )

                from bs4 import BeautifulSoup
                soup = BeautifulSoup(data.text, "lxml")

                results = soup.select(pattern.search_selector or "a[href]")
                anime_links = [
                    a for a in results
                    if _looks_like_anime_link(a.get("href", ""))
                ]
                if anime_links:
                    return self._pass(
                        "post_search_has_results",
                        _ms(start),
                        f"POST search for '{term}' returned {len(anime_links)} result(s)",
                    )
            except (RetryableError, PermanentError, CloudflareError, Exception):
                continue

        return self._fail(
            "post_search_has_results",
            _ms(start),
            f"No search results for any term via POST: {DEFAULT_SEARCH_TERMS}",
        )

    async def _test_graphql(
        self,
        ext: ExtensionMeta,
        session: aiohttp.ClientSession,
        pattern,
    ) -> TestResult:
        start = time.monotonic()

        if ext.theme_pkg == "anilist":
            url = "https://graphql.anilist.co"
        else:
            url = ext.base_url.rstrip("/") + (pattern.search_path or "/")

        query = (
            '{ Page(page: 1, perPage: 5) { media(search: "naruto") { id title { romaji english } } } }'
        )
        payload = {"query": query}

        try:
            import json
            data = await fetch_with_headers(
                session, url, self.config,
                method="POST",
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                data=payload,
            )

            try:
                parsed = json.loads(data.text)
                if isinstance(parsed, dict) and "data" in parsed:
                    media = parsed.get("data", {}).get("Page", {}).get("media", [])
                    if media:
                        return self._pass(
                            "post_search_load",
                            _ms(start),
                            f"GraphQL search returned {len(media)} result(s)",
                        )
                    return self._fail("post_search_load", _ms(start), "GraphQL returned empty media list")
                return self._fail("post_search_load", _ms(start), "GraphQL response missing 'data' key")
            except json.JSONDecodeError:
                return self._fail("post_search_load", _ms(start), "GraphQL response not valid JSON")
        except RetryableError as exc:
            return self._fail("post_search_load", _ms(start), f"Transient: {exc}")
        except PermanentError as exc:
            return self._fail("post_search_load", _ms(start), f"HTTP error: {exc}")
        except CloudflareError as exc:
            return self._fail("post_search_load", _ms(start), f"Cloudflare: {exc}")
        except Exception as exc:
            return self._error("post_search_load", _ms(start), f"Unexpected: {exc}")


def _looks_like_anime_link(href: str) -> bool:
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
