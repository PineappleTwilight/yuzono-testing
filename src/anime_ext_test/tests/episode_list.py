"""Layer 3: Episode list tests — verify episode delivery (inline HTML and XHR/AJAX)."""

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
class EpisodeListTest(ExtensionTest):
    """Test episode list delivery — inline HTML on detail page or via XHR/AJAX endpoint."""

    name = "episode_list"
    category = "episode_list"

    async def run(
        self,
        ext: ExtensionMeta,
        session: aiohttp.ClientSession | None = None,
    ) -> list[TestResult]:
        if session is None:
            return [self._error("episode_list_delivery", 0, "No HTTP session provided")]
        if not ext.base_url:
            return [self._skip("episode_list_delivery", 0, "No baseUrl defined")]
        if ext.requires_api_key:
            return [self._skip("episode_list_delivery", 0, "Requires API key")]

        if not ext.is_multisrc:
            return [self._skip("episode_list_delivery", 0, "Non-multisrc: handled by episodes test")]

        pattern = get_theme_pattern(ext.theme_pkg or "")

        if pattern.supports_episodes is False:
            return [self._skip("episode_list_delivery", 0, "Theme does not support episode lists")]

        if pattern.episode_delivery == "none":
            return [self._skip("episode_list_delivery", 0, "Theme episode_delivery=none")]

        detail_url = await self._find_detail_url(ext, session)
        if not detail_url:
            return [self._skip("episode_list_delivery", 0, "Could not find a detail page URL")]

        results: list[TestResult] = []

        if pattern.episode_delivery == "inline":
            results.append(await self._test_inline_episodes(ext, session, detail_url))
        elif pattern.episode_delivery == "xhr":
            results.append(await self._test_inline_episodes(ext, session, detail_url))
            results.append(await self._test_xhr_episodes(ext, session, detail_url))
        elif pattern.episode_delivery == "graphql":
            results.append(self._skip("episode_list_delivery", 0, "GraphQL episode delivery not testable via HTTP"))
        else:
            results.append(self._skip("episode_list_delivery", 0, f"Unknown: {pattern.episode_delivery}"))

        return results

    async def _test_inline_episodes(
        self, ext: ExtensionMeta, session: aiohttp.ClientSession, detail_url: str,
    ) -> TestResult:
        start = time.monotonic()
        try:
            _data, soup = await fetch_html(session, detail_url, self.config)
            pattern = get_theme_pattern(ext.theme_pkg or "")
            selector = pattern.episode_selector
            elements = soup.select(selector)

            ep_links = [el for el in elements if self._is_episode_element(el)]

            if ep_links:
                nums = self._extract_episode_numbers(ep_links)
                num_info = f" (eps: {nums[:5]})" if nums else ""
                return self._pass(
                    "episode_list_inline",
                    _ms(start),
                    f"Found {len(ep_links)} inline episode(s){num_info}",
                )
            return self._fail(
                "episode_list_inline",
                _ms(start),
                "No episode elements found with inline selector",
                detail=f"selector: {selector}, URL: {detail_url}",
            )
        except RetryableError as exc:
            return self._fail("episode_list_inline", _ms(start), f"Transient: {exc}")
        except PermanentError as exc:
            return self._fail("episode_list_inline", _ms(start), f"HTTP error: {exc}")
        except CloudflareError as exc:
            return self._fail("episode_list_inline", _ms(start), f"Cloudflare: {exc}")
        except Exception as exc:
            return self._error("episode_list_inline", _ms(start), f"Unexpected: {exc}")

    async def _test_xhr_episodes(
        self, ext: ExtensionMeta, session: aiohttp.ClientSession, detail_url: str,
    ) -> TestResult:
        start = time.monotonic()
        pattern = get_theme_pattern(ext.theme_pkg or "")

        if not pattern.episode_xhr_path:
            return self._skip("episode_list_xhr", _ms(start), "No XHR episode path defined for theme")

        anime_id = await self._extract_anime_id(ext, session, detail_url)
        if not anime_id:
            return self._skip("episode_list_xhr", _ms(start), "Could not extract anime ID from detail page")

        base = ext.base_url.rstrip("/")
        xhr_url = base + pattern.episode_xhr_path.replace("{id}", str(anime_id))
        headers = dict(pattern.xhr_headers) if pattern.xhr_headers else {}

        try:
            data, parsed = await fetch_json(session, xhr_url, self.config, headers=headers)
            if _is_valid_xhr_response(parsed):
                ep_count = _count_xhr_episodes(parsed)
                return self._pass(
                    "episode_list_xhr",
                    _ms(start),
                    f"XHR endpoint returned valid JSON with {ep_count} episode(s)",
                )
            return self._fail(
                "episode_list_xhr",
                _ms(start),
                "XHR endpoint returned JSON but no episode data",
                detail=(
                    f"url: {xhr_url}, keys: "
                    f"{list(parsed.keys())[:5] if isinstance(parsed, dict) else type(parsed).__name__}"
                ),
            )
        except PermanentError as exc:
            return self._fail("episode_list_xhr", _ms(start), f"HTTP error: {exc}")
        except CloudflareError as exc:
            return self._fail("episode_list_xhr", _ms(start), f"Cloudflare: {exc}")
        except RetryableError as exc:
            return self._fail("episode_list_xhr", _ms(start), f"Transient: {exc}")
        except Exception as exc:
            return self._skip("episode_list_xhr", _ms(start), f"XHR episode test skipped: {exc}")

    async def _extract_anime_id(
        self, ext: ExtensionMeta, session: aiohttp.ClientSession, detail_url: str,
    ) -> str | None:
        try:
            _data, soup = await fetch_html(session, detail_url, self.config)
        except (RetryableError, PermanentError, CloudflareError, Exception):
            return None

        el = soup.select_one("[data-id]")
        if el:
            return el.get("data-id")

        el = soup.select_one("[data-id]")
        if el and el.get("data-id"):
            return el.get("data-id")

        match = re.search(r"/(\d+)(?:/|$)", detail_url)
        if match:
            return match.group(1)

        return None

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
    def _is_episode_element(element) -> bool:
        href = getattr(element, "get", lambda _k, _d="": _d)("href", "")
        text = getattr(element, "get_text", lambda: "")().strip().lower()
        if not href and not text:
            return False
        ep_indicators = [
            "episode", "ep-", "ep_", "capitulo", "episodio",
            "ova", "special", "ona",
        ]
        lower_href = (href or "").lower()
        return any(ind in lower_href or ind in text for ind in ep_indicators)

    @staticmethod
    def _extract_episode_numbers(elements: list) -> list[str]:
        nums = []
        for el in elements:
            text = getattr(el, "get_text", lambda: "")().strip()
            match = re.search(r"\d+", text)
            if match:
                nums.append(match.group())
        return sorted(set(nums))


def _is_valid_xhr_response(parsed) -> bool:
    if isinstance(parsed, dict):
        if "html" in parsed:
            return bool(parsed["html"])
        if "result" in parsed:
            return bool(parsed["result"])
        if "data" in parsed:
            return True
        if any(k in parsed for k in ("episodes", "items", "list", "status", "type")):
            return True
    return isinstance(parsed, list) or bool(isinstance(parsed, str) and len(parsed) > 50)


def _count_xhr_episodes(parsed) -> int:
    if isinstance(parsed, dict):
        for key in ("episodes", "items", "list"):
            val = parsed.get(key)
            if isinstance(val, list):
                return len(val)
        html_val = parsed.get("html") or parsed.get("result")
        if isinstance(html_val, str):
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_val, "lxml")
            return len(soup.select("a, li, div[data-id]"))
    if isinstance(parsed, list):
        return len(parsed)
    return 0


def _ms(start: float) -> float:
    return round((time.monotonic() - start) * 1000, 1)
