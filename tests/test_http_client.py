"""Unit tests for http_client — ResponseData, CF detection, error types, retry logic."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from anime_ext_test.config import Config
from anime_ext_test.http_client import (
    CF_CHALLENGE_MARKERS,
    CloudflareError,
    PermanentError,
    ResponseData,
    RetryableError,
    create_session,
    fetch,
    fetch_html,
    fetch_json,
    fetch_with_headers,
)


class TestResponseData:
    """Verify ResponseData container and is_cloudflare_challenge logic."""

    def test_basic_creation(self):
        rd = ResponseData(status=200, url="https://example.com")
        assert rd.status == 200
        assert rd.url == "https://example.com"

    def test_default_content_type_empty(self):
        rd = ResponseData(status=200, url="https://example.com")
        assert rd.content_type == ""

    def test_default_text_empty(self):
        rd = ResponseData(status=200, url="https://example.com")
        assert rd.text == ""

    def test_default_headers_none(self):
        rd = ResponseData(status=200, url="https://example.com")
        assert rd.headers is None

    def test_cloudflare_403_with_marker(self):
        for marker in CF_CHALLENGE_MARKERS:
            rd = ResponseData(
                status=403, url="https://example.com",
                text=f"some page {marker} more text",
                headers={},
            )
            assert rd.is_cloudflare_challenge is True, f"Marker '{marker}' not detected"

    def test_cloudflare_503_with_marker(self):
        rd = ResponseData(
            status=503, url="https://example.com",
            text="Just a moment...",
            headers={},
        )
        assert rd.is_cloudflare_challenge is True

    def test_cloudflare_403_with_cf_ray_header(self):
        rd = ResponseData(
            status=403, url="https://example.com",
            text="normal page",
            headers={"cf-ray": "some-raw-value"},
        )
        assert rd.is_cloudflare_challenge is True

    def test_cloudflare_503_with_cf_ray_header(self):
        rd = ResponseData(
            status=503, url="https://example.com",
            text="normal page",
            headers={"cf-ray": "some-value"},
        )
        assert rd.is_cloudflare_challenge is True

    def test_not_cloudflare_200(self):
        rd = ResponseData(status=200, url="https://example.com", text="OK", headers={})
        assert rd.is_cloudflare_challenge is False

    def test_not_cloudflare_404(self):
        rd = ResponseData(status=404, url="https://example.com", text="Not Found", headers={})
        assert rd.is_cloudflare_challenge is False

    def test_not_cloudflare_500_no_cf_ray(self):
        rd = ResponseData(status=500, url="https://example.com", text="Error", headers={})
        assert rd.is_cloudflare_challenge is False

    def test_cf_ray_header_case_insensitive(self):
        rd = ResponseData(
            status=403, url="https://example.com",
            text="normal",
            headers={"CF-Ray": "abc123"},
        )
        assert rd.is_cloudflare_challenge is True

    def test_cloudflare_401_not_detected(self):
        """Only 403 and 503 trigger CF detection."""
        rd = ResponseData(
            status=401, url="https://example.com",
            text="Just a moment...", headers={},
        )
        assert rd.is_cloudflare_challenge is False


class TestErrorTypes:
    """Verify error hierarchy."""

    def test_retryable_error_is_exception(self):
        err = RetryableError("timeout")
        assert isinstance(err, Exception)
        assert str(err) == "timeout"

    def test_permanent_error_is_exception(self):
        err = PermanentError("HTTP 404")
        assert isinstance(err, Exception)
        assert str(err) == "HTTP 404"

    def test_cloudflare_error_is_exception(self):
        err = CloudflareError("CF challenge")
        assert isinstance(err, Exception)
        assert str(err) == "CF challenge"

    def test_retryable_and_permanent_distinct(self):
        assert not issubclass(RetryableError, PermanentError)
        assert not issubclass(PermanentError, RetryableError)


class TestCreateSession:
    """create_session returns a properly configured ClientSession."""

    @pytest.mark.asyncio
    async def test_session_headers_have_user_agent(self):
        config = Config()
        session = create_session(config)
        try:
            assert "User-Agent" in session.headers
            assert "Chrome" in session.headers["User-Agent"]
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_session_headers_have_accept(self):
        config = Config()
        session = create_session(config)
        try:
            assert "Accept" in session.headers
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_custom_user_agent(self):
        config = Config(user_agent="CustomBot/1.0")
        session = create_session(config)
        try:
            assert session.headers["User-Agent"] == "CustomBot/1.0"
        finally:
            await session.close()


class TestFetchRetryBehavior:
    """Verify fetch() retry logic using mocked session responses."""

    @pytest.fixture
    def config(self) -> Config:
        return Config(max_retries=2, retry_backoff=0.01)

    async def test_fetch_succeeds_on_first_try(self, config):
        """200 response should return immediately."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="OK")
        mock_response.url = "https://example.com"
        mock_response.content_type = "text/html"
        mock_response.headers = {}
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_response)
        mock_session.headers = {}

        result = await fetch(mock_session, "https://example.com", config)
        assert result.status == 200
        assert result.text == "OK"

    async def test_fetch_raises_cloudflare_on_cf_challenge(self, config):
        """403 with CF marker should raise CloudflareError immediately."""
        mock_response = AsyncMock()
        mock_response.status = 403
        mock_response.text = AsyncMock(return_value="Just a moment...")
        mock_response.url = "https://example.com"
        mock_response.content_type = "text/html"
        mock_response.headers = {}
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_response)

        with pytest.raises(CloudflareError):
            await fetch(mock_session, "https://example.com", config)

    async def test_fetch_raises_permanent_on_404(self, config):
        """404 should raise PermanentError immediately."""
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.text = AsyncMock(return_value="Not Found")
        mock_response.url = "https://example.com"
        mock_response.content_type = "text/html"
        mock_response.headers = {}
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_response)

        with pytest.raises(PermanentError):
            await fetch(mock_session, "https://example.com", config)

    async def test_fetch_retries_on_500(self, config):
        """500 should be retryable — retries exhaust then raises."""
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text = AsyncMock(return_value="Server Error")
        mock_response.url = "https://example.com"
        mock_response.content_type = "text/html"
        mock_response.headers = {}
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.request = MagicMock(return_value=mock_response)

        with pytest.raises(RetryableError):
            await fetch(mock_session, "https://example.com", config)


class TestCfChallengeMarkers:
    """Verify all documented CF challenge markers are in the list."""

    def test_marker_count(self):
        assert len(CF_CHALLENGE_MARKERS) >= 5

    def test_known_markers_present(self):
        known = [
            "Just a moment...",
            "cf-browser-verification",
            "cf_chl_opt",
            "_cf_chl_tk",
            "Checking your browser",
        ]
        for marker in known:
            assert marker in CF_CHALLENGE_MARKERS
