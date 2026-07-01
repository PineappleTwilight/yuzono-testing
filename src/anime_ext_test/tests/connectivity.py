"""Layer 2: Connectivity tests — validate HTTP reachability of baseUrl."""

from __future__ import annotations

import time

import aiohttp

from anime_ext_test.http_client import (
    CloudflareError,
    PermanentError,
    RetryableError,
    fetch,
)
from anime_ext_test.models import ExtensionMeta, TestResult
from anime_ext_test.tests.registry import ExtensionTest, register_test


@register_test
class ConnectivityTest(ExtensionTest):
    """Verify that an extension's baseUrl is reachable and returns valid HTTP."""

    name = "connectivity"
    category = "connectivity"

    async def run(
        self,
        ext: ExtensionMeta,
        session: aiohttp.ClientSession | None = None,
    ) -> list[TestResult]:
        if session is None:
            return [self._error("connectivity", 0, "No HTTP session provided")]

        results: list[TestResult] = []

        if not ext.base_url:
            results.append(self._skip("base_url_reachable", 0, "No baseUrl defined"))
            results.append(self._skip("base_url_resolves", 0, "No baseUrl defined"))
            results.append(self._skip("base_url_tls", 0, "No baseUrl defined"))
            results.append(self._skip("base_url_status_200", 0, "No baseUrl defined"))
            results.append(self._skip("base_url_no_cloudflare", 0, "No baseUrl defined"))
            return results

        results.append(await self._test_reachable(ext, session))
        if results[-1].status in ("pass", "fail"):
            results.append(await self._test_dns(ext, session))
            results.append(await self._test_tls(ext, session))
            results.append(await self._test_status(ext, session))
            results.append(await self._test_no_cloudflare(ext, session))
        else:
            for name in ("base_url_resolves", "base_url_tls", "base_url_status_200", "base_url_no_cloudflare"):
                results.append(self._skip(name, 0, "Skipped: baseUrl not reachable"))

        return results

    async def _test_reachable(self, ext: ExtensionMeta, session: aiohttp.ClientSession) -> TestResult:
        start = time.monotonic()
        try:
            data = await fetch(session, ext.base_url, self.config)
            return self._pass("base_url_reachable", _ms(start), f"HTTP {data.status} from {ext.base_url}")
        except RetryableError as exc:
            return self._fail("base_url_reachable", _ms(start), f"Transient error: {exc}")
        except PermanentError as exc:
            return self._fail("base_url_reachable", _ms(start), f"HTTP error: {exc}")
        except CloudflareError as exc:
            return self._fail("base_url_reachable", _ms(start), f"Cloudflare blocked: {exc}")
        except Exception as exc:
            return self._error("base_url_reachable", _ms(start), f"Unexpected: {exc}")

    async def _test_dns(self, ext: ExtensionMeta, session: aiohttp.ClientSession) -> TestResult:
        start = time.monotonic()
        try:
            data = await fetch(session, ext.base_url, self.config, method="HEAD")
            return self._pass("base_url_resolves", _ms(start), f"DNS resolved, HTTP {data.status}")
        except aiohttp.ClientConnectorError as exc:
            return self._fail("base_url_resolves", _ms(start), f"DNS/connection failed: {exc}")
        except RetryableError:
            return self._pass("base_url_resolves", _ms(start), "DNS resolved (server error on response)")
        except PermanentError:
            return self._pass("base_url_resolves", _ms(start), "DNS resolved (client error on response)")
        except CloudflareError:
            return self._pass("base_url_resolves", _ms(start), "DNS resolved (Cloudflare challenged)")
        except Exception as exc:
            return self._error("base_url_resolves", _ms(start), f"Unexpected: {exc}")

    async def _test_tls(self, ext: ExtensionMeta, session: aiohttp.ClientSession) -> TestResult:
        start = time.monotonic()
        if not ext.base_url.startswith("https://"):
            return self._skip("base_url_tls", _ms(start), "baseUrl uses HTTP, not HTTPS")
        try:
            await fetch(session, ext.base_url, self.config)
            return self._pass("base_url_tls", _ms(start), "TLS handshake succeeded")
        except aiohttp.ClientConnectorError as exc:
            if "SSL" in str(exc) or "certificate" in str(exc):
                return self._fail("base_url_tls", _ms(start), f"TLS error: {exc}")
            return self._fail("base_url_tls", _ms(start), f"Connection failed: {exc}")
        except RetryableError:
            return self._pass("base_url_tls", _ms(start), "TLS OK (server error on response)")
        except (PermanentError, CloudflareError):
            return self._pass("base_url_tls", _ms(start), "TLS OK (HTTP error on response)")
        except Exception as exc:
            return self._error("base_url_tls", _ms(start), f"Unexpected: {exc}")

    async def _test_status(self, ext: ExtensionMeta, session: aiohttp.ClientSession) -> TestResult:
        start = time.monotonic()
        try:
            data = await fetch(session, ext.base_url, self.config)
            if 200 <= data.status < 300:
                return self._pass("base_url_status_200", _ms(start), f"HTTP {data.status}")
            if 300 <= data.status < 400:
                return self._fail(
                    "base_url_status_200",
                    _ms(start),
                    f"Redirect (HTTP {data.status}), final: {data.url}",
                )
            return self._fail("base_url_status_200", _ms(start), f"HTTP {data.status} (expected 2xx)")
        except RetryableError as exc:
            return self._fail("base_url_status_200", _ms(start), f"Server error: {exc}")
        except PermanentError as exc:
            return self._fail("base_url_status_200", _ms(start), f"Client error: {exc}")
        except CloudflareError:
            return self._fail("base_url_status_200", _ms(start), "Cloudflare challenge (HTTP 403/503)")
        except Exception as exc:
            return self._error("base_url_status_200", _ms(start), f"Unexpected: {exc}")

    async def _test_no_cloudflare(self, ext: ExtensionMeta, session: aiohttp.ClientSession) -> TestResult:
        start = time.monotonic()
        try:
            await fetch(session, ext.base_url, self.config)
            return self._pass("base_url_no_cloudflare", _ms(start), "No Cloudflare challenge detected")
        except CloudflareError as exc:
            return self._fail("base_url_no_cloudflare", _ms(start), f"Cloudflare challenge: {exc}")
        except (RetryableError, PermanentError):
            return self._skip("base_url_no_cloudflare", _ms(start), "Could not verify (HTTP error)")
        except Exception as exc:
            return self._error("base_url_no_cloudflare", _ms(start), f"Unexpected: {exc}")


def _ms(start: float) -> float:
    return round((time.monotonic() - start) * 1000, 1)
