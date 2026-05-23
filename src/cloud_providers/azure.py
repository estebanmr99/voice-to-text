"""Azure OpenAI Whisper transcription provider.

Posts audio to the Azure OpenAI Whisper API using ``httpx`` with
``api-key`` authentication over multipart/form-data.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from cloud_transcriber import TranscriptionProvider, TranscriptionResult

logger = logging.getLogger(__name__)

# Retry / timeout constants
_MAX_RETRIES = 3
_BACKOFF_INITIAL = 1.0
_BACKOFF_MULTIPLIER = 2.0
_REQUEST_TIMEOUT = 300.0  # 5 minutes for long audio


class AzureOpenAIProvider(TranscriptionProvider):
    """Azure OpenAI Whisper transcription provider.

    POSTs audio to the Azure OpenAI Whisper API endpoint using
    multipart/form-data with ``api-key`` header authentication.

    Parameters
    ----------
    endpoint_url:
        Base URL of the Azure OpenAI resource
        (e.g. ``https://my-resource.openai.azure.com``).
    api_key:
        Azure OpenAI API key.
    deployment_name:
        Model deployment name (default ``"whisper-1"``).
    api_version:
        API version string (default ``"2025-04-01-preview"``).
    """

    def __init__(
        self,
        endpoint_url: str,
        api_key: str,
        deployment_name: str = "whisper-1",
        api_version: str = "2025-04-01-preview",
    ) -> None:
        self._endpoint_url = endpoint_url.rstrip("/")
        self._api_key = api_key
        self._deployment_name = deployment_name
        self._api_version = api_version

    # ------------------------------------------------------------------
    # URL building
    # ------------------------------------------------------------------

    def _build_url(self) -> str:
        """Build the full transcription endpoint URL."""
        return (
            f"{self._endpoint_url}/openai/deployments/"
            f"{self._deployment_name}/audio/transcriptions"
            f"?api-version={self._api_version}"
        )

    # ------------------------------------------------------------------
    # Transcription
    # ------------------------------------------------------------------

    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str,
        language: str | None = None,
    ) -> TranscriptionResult:
        """POST *audio_bytes* to the Azure Whisper API and return the result.

        Handles transient errors with exponential backoff:
            * ``429`` — rate limited (reads ``Retry-After`` header)
            * ``5xx`` — server errors
            * Timeout — connection / read timeout

        Non-retriable errors (``4xx`` except ``429``) raise immediately.
        """
        url = self._build_url()
        headers = {"api-key": self._api_key}

        # Build multipart form data
        files: dict[str, Any] = {
            "file": (filename, audio_bytes, "audio/wav"),
        }
        data: dict[str, str] = {
            "response_format": "json",
        }
        if language:
            data["language"] = language

        last_error: Exception | None = None

        for attempt in range(_MAX_RETRIES):
            try:
                with httpx.Client(timeout=_REQUEST_TIMEOUT) as client:
                    response = client.post(
                        url, headers=headers, files=files, data=data
                    )

                if response.status_code == 429:
                    retry_after = _parse_retry_after(response)
                    logger.warning(
                        "Rate limited (429), retrying after %.1fs "
                        "(attempt %d/%d)",
                        retry_after,
                        attempt + 1,
                        _MAX_RETRIES,
                    )
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()

                result: dict[str, Any] = response.json()
                text = result.get("text", "")

                return TranscriptionResult(
                    text=text,
                    language=result.get("language"),
                    segments=result.get("segments"),
                    raw=result,
                )

            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning(
                    "Request timeout (attempt %d/%d)", attempt + 1, _MAX_RETRIES
                )
                if attempt < _MAX_RETRIES - 1:
                    _sleep_backoff(attempt)
                    continue
                raise RuntimeError(
                    f"Azure API timed out after {_MAX_RETRIES} retries"
                ) from exc

            except httpx.HTTPStatusError as exc:
                # 4xx errors (except 429) are configuration errors — do NOT retry
                status = exc.response.status_code
                if 400 <= status < 500 and status != 429:
                    body = _extract_error_body(exc.response)
                    raise RuntimeError(
                        f"Azure API configuration error ({status}): {body}"
                    ) from exc

                # 5xx errors — retry
                last_error = exc
                logger.warning(
                    "Server error %d (attempt %d/%d)",
                    status,
                    attempt + 1,
                    _MAX_RETRIES,
                )
                if attempt < _MAX_RETRIES - 1:
                    _sleep_backoff(attempt)
                    continue
                raise RuntimeError(
                    f"Azure API server error after {_MAX_RETRIES} retries: {exc}"
                ) from exc

            except httpx.RequestError as exc:
                # Network / connection errors — retry
                last_error = exc
                logger.warning(
                    "Request failed (attempt %d/%d): %s",
                    attempt + 1,
                    _MAX_RETRIES,
                    exc,
                )
                if attempt < _MAX_RETRIES - 1:
                    _sleep_backoff(attempt)
                    continue
                raise RuntimeError(
                    f"Azure API request failed after {_MAX_RETRIES} retries: {exc}"
                ) from exc

        # Fallback (should not be reached)
        raise RuntimeError(
            f"Azure API request failed after {_MAX_RETRIES} retries"
        ) from last_error


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_retry_after(response: httpx.Response) -> float:
    """Extract ``Retry-After`` header value, defaulting to 5 seconds."""
    retry_after = response.headers.get("Retry-After", "5")
    try:
        return float(retry_after)
    except (ValueError, TypeError):
        return 5.0


def _extract_error_body(response: httpx.Response) -> str:
    """Extract error message from an Azure API error response JSON body."""
    try:
        body = response.json()
        return body.get("error", {}).get("message", str(body))
    except (json.JSONDecodeError, AttributeError):
        return response.text[:500]


def _sleep_backoff(attempt: int) -> None:
    """Sleep with exponential backoff."""
    delay = _BACKOFF_INITIAL * (_BACKOFF_MULTIPLIER**attempt)
    time.sleep(delay)
