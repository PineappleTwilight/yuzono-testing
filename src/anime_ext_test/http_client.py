"""Async HTTP client with retry, timeout, and Cloudflare detection."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import aiohttp
from bs4 import BeautifulSoup

from anime_ext_test.config import Config

logger = logging.getLogger(__name__)

# Cloudflare challenge markers in HTML responses
CF_CHALLENGE_MARKERS = [
    "Just a moment...",
    "cf-browser-verification",
    "cf_chl_opt",
    "_cf_chl_tk",
    "Checking your browser",
    "Attention Required! | Cloudflare",
    "Enable JavaScript and cookies to continue",
]


class RetryableError(Exception):
    """Error that can be retried (5xx, timeout, connection reset, 429)."""


class PermanentError(Exception):
    """Error that should not be retried (4xx except 429)."""


class CloudflareError(Exception):
    """Site returned a Cloudflare challenge page."""


@dataclass
class ResponseData:
    """Container for HTTP response data."""

    status: int
    url: str
    content_type: str = ""
    text: str = ""
    headers: dict[str, str] = None  # type: ignore[assignment]

    @property
    def is_cloudflare_challenge(self) -> bool:
        """Check if the response is a Cloudflare challenge page."""
        if self.status in (403, 503):
            for marker in CF_CHALLENGE_MARKERS:
                if marker in self.text:
                    return True
        cf_headers = {k.lower(): v for k, v in (self.headers or {}).items()}
        return "cf-ray" in cf_headers and self.status in (403, 503)


def create_session(config: Config) -> aiohttp.ClientSession:
    """Create an aiohttp ClientSession configured with timeouts and headers."""
    timeout = aiohttp.ClientTimeout(
        total=config.http_timeout,
        connect=config.http_connect_timeout,
    )
    headers = {
        "User-Agent": config.user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    connector = aiohttp.TCPConnector(limit=config.max_concurrent, ssl=False)
    return aiohttp.ClientSession(
        timeout=timeout,
        headers=headers,
        connector=connector,
    )


async def fetch(
    session: aiohttp.ClientSession,
    url: str,
    config: Config,
    method: str = "GET",
) -> ResponseData:
    """Fetch a URL with retry logic.

    Raises:
        RetryableError: On transient failures (5xx, timeout).
        PermanentError: On client errors (4xx except 429).
        CloudflareError: On Cloudflare challenge pages.
    """
    last_error: Exception | None = None

    for attempt in range(config.max_retries + 1):
        try:
            async with session.request(method, url, allow_redirects=True) as resp:
                text = await resp.text(errors="replace")
                data = ResponseData(
                    status=resp.status,
                    url=str(resp.url),
                    content_type=resp.content_type,
                    text=text,
                    headers=dict(resp.headers),
                )

                # Check for Cloudflare challenge
                if data.is_cloudflare_challenge:
                    raise CloudflareError(f"Cloudflare challenge detected at {url} (HTTP {data.status})")

                # Check status code
                if 200 <= resp.status < 300:
                    return data
                elif resp.status == 429:
                    # Rate limited — retryable
                    last_error = RetryableError(f"HTTP 429 Rate Limited at {url}")
                elif 400 <= resp.status < 500:
                    raise PermanentError(f"HTTP {resp.status} at {url}")
                elif resp.status >= 500:
                    last_error = RetryableError(f"HTTP {resp.status} Server Error at {url}")
                else:
                    return data  # Redirection or unusual status — return as-is

        except CloudflareError:
            raise
        except PermanentError:
            raise
        except aiohttp.ServerTimeoutError as exc:
            last_error = RetryableError(f"Timeout fetching {url}: {exc}")
        except aiohttp.ClientConnectorError as exc:
            last_error = RetryableError(f"Connection error for {url}: {exc}")
        except aiohttp.ClientError as exc:
            last_error = RetryableError(f"Client error for {url}: {exc}")

        # Retry with backoff
        if attempt < config.max_retries:
            backoff = config.retry_backoff * (attempt + 1)
            logger.debug("Retry %d/%d for %s in %.1fs", attempt + 1, config.max_retries, url, backoff)
            await asyncio.sleep(backoff)

    # All retries exhausted
    if last_error is not None:
        raise last_error
    raise RetryableError(f"Failed fetching {url} after {config.max_retries + 1} attempts")


async def fetch_html(
    session: aiohttp.ClientSession,
    url: str,
    config: Config,
) -> tuple[ResponseData, BeautifulSoup]:
    """Fetch a URL and parse the response as HTML.

    Returns:
        Tuple of (raw response data, parsed BeautifulSoup object).
    """
    data = await fetch(session, url, config)
    soup = BeautifulSoup(data.text, "lxml")
    return data, soup


async def fetch_json(
    session: aiohttp.ClientSession,
    url: str,
    config: Config,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: dict[str, str] | None = None,
) -> tuple[ResponseData, dict]:
    """Fetch a URL and parse the response as JSON.

    Supports POST with form data and/or custom headers for XHR/AJAX endpoints.

    Args:
        session: aiohttp session.
        url: URL to fetch.
        config: Config for timeouts/retries.
        method: HTTP method (GET or POST).
        headers: Extra headers to merge into request (e.g. X-Requested-With).
        data: Form data dict for POST requests.

    Returns:
        Tuple of (raw response data, parsed JSON dict).
    """
    import json

    raw = await fetch_with_headers(session, url, config, method=method, headers=headers, data=data)
    try:
        parsed = json.loads(raw.text)
    except json.JSONDecodeError as exc:
        raise PermanentError(f"Invalid JSON from {url}: {exc}") from exc
    return raw, parsed


async def fetch_with_headers(
    session: aiohttp.ClientSession,
    url: str,
    config: Config,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: dict[str, str] | None = None,
) -> ResponseData:
    """Fetch a URL with custom headers and/or POST form data.

    Unlike fetch(), this allows overriding headers per-request and sending
    form-encoded POST bodies — needed for XHR/AJAX and POST-based search
    endpoints used by several themes.

    Args:
        session: aiohttp session.
        url: URL to fetch.
        config: Config for timeouts/retries.
        method: HTTP method (GET or POST).
        headers: Extra headers to merge into the request.
        data: Form data dict for POST body (URL-encoded automatically).

    Returns:
        ResponseData with status, url, content_type, text, headers.
    """
    last_error: Exception | None = None

    for attempt in range(config.max_retries + 1):
        try:
            # Merge session headers with per-request extras
            req_headers = dict(session.headers) if session.headers else {}
            if headers:
                req_headers.update(headers)

            kwargs: dict = {
                "allow_redirects": True,
                "headers": req_headers,
            }
            if data and method == "POST":
                kwargs["data"] = data

            async with session.request(method, url, **kwargs) as resp:
                text = await resp.text(errors="replace")
                resp_data = ResponseData(
                    status=resp.status,
                    url=str(resp.url),
                    content_type=resp.content_type,
                    text=text,
                    headers=dict(resp.headers),
                )

                if resp_data.is_cloudflare_challenge:
                    raise CloudflareError(
                        f"Cloudflare challenge at {url} (HTTP {resp.status})"
                    )

                if 200 <= resp.status < 300:
                    return resp_data
                elif resp.status == 429:
                    last_error = RetryableError(f"HTTP 429 Rate Limited at {url}")
                elif 400 <= resp.status < 500:
                    raise PermanentError(f"HTTP {resp.status} at {url}")
                elif resp.status >= 500:
                    last_error = RetryableError(f"HTTP {resp.status} Server Error at {url}")
                else:
                    return resp_data

        except CloudflareError:
            raise
        except PermanentError:
            raise
        except aiohttp.ServerTimeoutError as exc:
            last_error = RetryableError(f"Timeout fetching {url}: {exc}")
        except aiohttp.ClientConnectorError as exc:
            last_error = RetryableError(f"Connection error for {url}: {exc}")
        except aiohttp.ClientError as exc:
            last_error = RetryableError(f"Client error for {url}: {exc}")

        if attempt < config.max_retries:
            backoff = config.retry_backoff * (attempt + 1)
            logger.debug("Retry %d/%d for %s in %.1fs", attempt + 1, config.max_retries, url, backoff)
            await asyncio.sleep(backoff)

    if last_error is not None:
        raise last_error
    raise RetryableError(f"Failed fetching {url} after {config.max_retries + 1} attempts")
