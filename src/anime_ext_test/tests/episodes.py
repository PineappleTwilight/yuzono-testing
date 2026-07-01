"""Layer 3: Episode list tests — verify episodeList returns episodes."""

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
class EpisodesTest(ExtensionTest):
    """Test that episode links are present on anime detail pages."""

    name = "episodes"
    category = "episodes"

    async def run(
        self,
        ext: ExtensionMeta,
        session: aiohttp.ClientSession | None = None,
    ) -> list[TestResult]:
        if session is None:
            return [self._error("episode_page_load", 0, "No HTTP session provided")]
        if not ext.base_url:
            return [self._skip("episode_page_load", 0, "No baseUrl defined")]
        if ext.requires_api_key:
            return [self._skip("episode_page_load", 0, "Requires API key")]

        # Find a detail URL first, then look for episode links on it
        detail_url = await self._find_detail_url(ext, session)
        if not detail_url:
            return [self._skip("episode_page_load", 0, "Could not find a detail page to check for episodes")]

        results: list[TestResult] = []
        results.append(await self._test_episode_links(ext, session, detail_url))
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

        links = soup.select("a[href]")
        for link in links:
            href = link.get("href", "")
            lower = href.lower() if href else ""
            detail_patterns = [
                r"/anime/\w", r"/title/\w", r"/series/\w",
                r"/show/\w", r"/drama/\w",
            ]
            if any(re.search(p, lower) for p in detail_patterns):
                return href if href.startswith("http") else base + href
        return None

    async def _test_episode_links(
        self, ext: ExtensionMeta, session: aiohttp.ClientSession, detail_url: str,
    ) -> TestResult:
        start = time.monotonic()
        try:
            _data, soup = await fetch_html(session, detail_url, self.config)

            if ext.is_multisrc:
                pattern = get_theme_pattern(ext.theme_pkg or "")
                selector = pattern.episode_selector
                if pattern.supports_episodes is False:
                    return self._skip(
                        "episode_page_load",
                        _ms(start),
                        "Theme does not support episode lists",
                    )
            else:
                selector = "a"

            episode_links = soup.select(selector)
            ep_links = [a for a in episode_links if self._is_episode_link(a, ext)]

            if ep_links:
                numbers = self._extract_episode_numbers(ep_links)
                num_info = f" (numbers: {numbers[:5]})" if numbers else ""
                has_valid_hrefs = sum(1 for el in ep_links if el.get("href"))
                return self._pass(
                    "episode_page_load",
                    _ms(start),
                    f"Found {len(ep_links)} episode link(s), {has_valid_hrefs} with hrefs{num_info}",
                )
            ep_sections = soup.select(
                ".episodes, .episode-list, .playlist, "
                "#episode_related, .episodios, .seasons"
            )
            if ep_sections:
                return self._pass(
                    "episode_page_load",
                    _ms(start),
                    f"Found {len(ep_sections)} episode section(s)",
                )
            return self._fail(
                "episode_page_load",
                _ms(start),
                "No episode links or sections found on detail page",
                detail=f"URL: {detail_url}, selector: {selector}",
            )
        except RetryableError as exc:
            return self._fail("episode_page_load", _ms(start), f"Transient: {exc}")
        except PermanentError as exc:
            return self._fail("episode_page_load", _ms(start), f"HTTP error: {exc}")
        except CloudflareError as exc:
            return self._fail("episode_page_load", _ms(start), f"Cloudflare: {exc}")
        except Exception as exc:
            return self._error("episode_page_load", _ms(start), f"Unexpected: {exc}")

    @staticmethod
    def _extract_episode_numbers(elements: list) -> list[str]:
        nums = []
        for el in elements:
            text = getattr(el, "get_text", lambda: "")().strip()
            match = re.search(r"\d+", text)
            if match:
                nums.append(match.group())
        return sorted(set(nums))

    @staticmethod
    def _is_episode_link(element: object, ext: ExtensionMeta) -> bool:
        """Check if an anchor element looks like an episode link."""
        href = getattr(element, "get", lambda _k, _d="": _d)("href", "")
        text = getattr(element, "get_text", lambda: "")().strip().lower()
        if not href:
            return False
        # Episode indicators in href or text
        ep_indicators = [
            "episode", "ep-", "ep_", "capitulo", "episodio",
            "ova", "special", "ova", "ona",
        ]
        lower_href = href.lower()
        for indicator in ep_indicators:
            if indicator in lower_href or indicator in text:
                return True
        has_ep_pattern = re.search(r"\bep\s*\d", text) or re.search(r"\b\d+\b", text)
        has_watch_path = any(p in lower_href for p in ["/watch/", "/play/", "/video/", "/episode/"])
        return bool(has_ep_pattern and has_watch_path)


def _ms(start: float) -> float:
    return round((time.monotonic() - start) * 1000, 1)
