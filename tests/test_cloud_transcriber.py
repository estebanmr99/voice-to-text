"""Tests for cloud transcription module and Azure provider.

All tests mock ``httpx.Client`` so no real HTTP connections are made.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import numpy as np
import pytest

from cloud_transcriber import (
    CloudTranscriber,
    TranscriptionProvider,
    TranscriptionResult,
    _numpy_to_wav,
)
from transcriber import TranscriptionError


# ======================================================================
# WAV conversion
# ======================================================================


class TestNumpyToWav:
    """Verify ``_numpy_to_wav`` produces valid WAV output."""

    def test_converts_float32_to_wav(self) -> None:
        audio = np.array([0.5, -0.5, 0.0, 0.25], dtype=np.float32)
        wav_bytes = _numpy_to_wav(audio, 16000)
        assert wav_bytes[:4] == b"RIFF"
        assert wav_bytes[8:12] == b"WAVE"
        assert len(wav_bytes) > 44  # header + data

    def test_converts_float64_to_wav(self) -> None:
        audio = np.array([0.5, -0.5], dtype=np.float64)
        wav_bytes = _numpy_to_wav(audio, 48000)
        assert wav_bytes[:4] == b"RIFF"
        assert wav_bytes[8:12] == b"WAVE"

    def test_converts_int16_to_wav(self) -> None:
        audio = np.array([100, -200, 0, 32767], dtype=np.int16)
        wav_bytes = _numpy_to_wav(audio, 16000)
        assert wav_bytes[:4] == b"RIFF"

    def test_clips_float32_out_of_range(self) -> None:
        """Values outside [-1, 1] should be clipped."""
        audio = np.array([2.0, -2.0, 0.5], dtype=np.float32)
        wav_bytes = _numpy_to_wav(audio, 16000)
        assert wav_bytes[:4] == b"RIFF"
        # Clipped values should not overflow int16
        assert len(wav_bytes) > 44

    def test_empty_audio_returns_valid_wav(self) -> None:
        audio = np.array([], dtype=np.int16)
        wav_bytes = _numpy_to_wav(audio, 16000)
        assert wav_bytes[:4] == b"RIFF"
        assert len(wav_bytes) == 44  # header only, no data

    def test_preserves_sample_rate_in_header(self) -> None:
        import struct
        audio = np.array([0.5], dtype=np.float32)
        wav_bytes = _numpy_to_wav(audio, 22050)
        # Sample rate is at bytes 24-27 in WAV header
        sr = struct.unpack_from("<I", wav_bytes, 24)[0]
        assert sr == 22050


# ======================================================================
# TranscriptionResult dataclass
# ======================================================================


class TestTranscriptionResult:
    """Dataclass defaults and field access."""

    def test_defaults(self) -> None:
        r = TranscriptionResult(text="hello")
        assert r.text == "hello"
        assert r.language is None
        assert r.segments is None
        assert r.raw is None

    def test_all_fields(self) -> None:
        r = TranscriptionResult(
            text="hello world",
            language="en",
            segments=[{"start": 0.0, "end": 1.0, "text": "hello"}],
            raw={"text": "hello world"},
        )
        assert r.language == "en"
        assert len(r.segments) == 1
        assert r.raw == {"text": "hello world"}


# ======================================================================
# CloudTranscriber — lifecycle & routing
# ======================================================================


class TestCloudTranscriberStart:
    """``start()`` validation and provider instantiation."""

    def test_missing_provider_type(self) -> None:
        ct = CloudTranscriber()
        with pytest.raises(TranscriptionError, match="provider_type"):
            ct.start({})

    def test_missing_endpoint_url(self) -> None:
        ct = CloudTranscriber()
        with pytest.raises(TranscriptionError, match="endpoint_url"):
            ct.start({"provider_type": "azure"})

    def test_loads_api_key_from_settings(self) -> None:
        mock_store = MagicMock()
        mock_store.get_api_key.return_value = "test-key-abc"

        ct = CloudTranscriber(settings_store=mock_store)

        with patch(
            "cloud_providers.azure.AzureOpenAIProvider"
        ) as mock_provider_cls:
            mock_provider_cls.return_value = MagicMock()
            ct.start(
                {
                    "provider_type": "azure",
                    "endpoint_url": "https://test.openai.azure.com",
                }
            )

        mock_store.get_api_key.assert_called_once_with("cloud/azure")
        assert ct.is_running() is True

    def test_raises_if_api_key_not_found(self) -> None:
        mock_store = MagicMock()
        mock_store.get_api_key.return_value = None

        ct = CloudTranscriber(settings_store=mock_store)

        with pytest.raises(TranscriptionError, match="API key not found"):
            ct.start(
                {
                    "provider_type": "azure",
                    "endpoint_url": "https://test.openai.azure.com",
                }
            )

    def test_uses_custom_api_key_id(self) -> None:
        mock_store = MagicMock()
        mock_store.get_api_key.return_value = "key"

        ct = CloudTranscriber(settings_store=mock_store)

        with patch("cloud_providers.azure.AzureOpenAIProvider"):
            ct.start(
                {
                    "provider_type": "azure",
                    "endpoint_url": "https://test.openai.azure.com",
                    "api_key_id": "cloud/my-custom-id",
                }
            )

        mock_store.get_api_key.assert_called_once_with("cloud/my-custom-id")

    def test_unknown_provider_raises(self) -> None:
        mock_store = MagicMock()
        mock_store.get_api_key.return_value = "key"

        ct = CloudTranscriber(settings_store=mock_store)

        with pytest.raises(TranscriptionError, match="Unknown cloud provider"):
            ct.start(
                {
                    "provider_type": "nonexistent",
                    "endpoint_url": "https://test.example.com",
                }
            )

    def test_passes_config_to_azure_provider(self) -> None:
        mock_store = MagicMock()
        mock_store.get_api_key.return_value = "secret-key"

        ct = CloudTranscriber(settings_store=mock_store)

        with patch(
            "cloud_providers.azure.AzureOpenAIProvider"
        ) as mock_provider_cls:
            ct.start(
                {
                    "provider_type": "azure",
                    "endpoint_url": "https://my-resource.openai.azure.com",
                    "deployment_name": "gpt-4o-transcribe",
                    "api_version": "2025-05-01",
                }
            )

        mock_provider_cls.assert_called_once_with(
            endpoint_url="https://my-resource.openai.azure.com",
            api_key="secret-key",
            deployment_name="gpt-4o-transcribe",
            api_version="2025-05-01",
        )


class TestCloudTranscriberStop:
    """``stop()`` clears state."""

    def test_stop_resets_running_state(self) -> None:
        mock_store = MagicMock()
        mock_store.get_api_key.return_value = "key"

        ct = CloudTranscriber(settings_store=mock_store)

        with patch("cloud_providers.azure.AzureOpenAIProvider"):
            ct.start(
                {
                    "provider_type": "azure",
                    "endpoint_url": "https://test.openai.azure.com",
                }
            )

        assert ct.is_running() is True
        ct.stop()
        assert ct.is_running() is False

    def test_stop_is_idempotent(self) -> None:
        ct = CloudTranscriber()
        ct.stop()  # should not raise
        ct.stop()
        assert ct.is_running() is False


class TestCloudTranscriberTranscribe:
    """``transcribe()`` numpy → WAV → provider flow."""

    def test_converts_audio_and_delegates_to_provider(self) -> None:
        mock_store = MagicMock()
        mock_store.get_api_key.return_value = "key"

        mock_provider = MagicMock(spec=TranscriptionProvider)
        mock_provider.transcribe.return_value = TranscriptionResult(
            text="transcribed result"
        )

        ct = CloudTranscriber(settings_store=mock_store)

        with patch(
            "cloud_providers.azure.AzureOpenAIProvider"
        ) as mock_cls:
            mock_cls.return_value = mock_provider
            ct.start(
                {
                    "provider_type": "azure",
                    "endpoint_url": "https://test.openai.azure.com",
                }
            )

        audio = np.ones(3200, dtype=np.float32) * 0.5
        result = ct.transcribe(audio, 16000)

        assert result == "transcribed result"

        # Verify WAV bytes were passed to provider
        mock_provider.transcribe.assert_called_once()
        call_kwargs = mock_provider.transcribe.call_args[1]
        assert isinstance(call_kwargs["audio_bytes"], bytes)
        assert call_kwargs["audio_bytes"][:4] == b"RIFF"
        assert call_kwargs["filename"].endswith(".wav")

    def test_empty_audio_returns_empty_string(self) -> None:
        mock_store = MagicMock()
        mock_store.get_api_key.return_value = "key"

        ct = CloudTranscriber(settings_store=mock_store)

        with patch("cloud_providers.azure.AzureOpenAIProvider"):
            ct.start(
                {
                    "provider_type": "azure",
                    "endpoint_url": "https://test.openai.azure.com",
                }
            )

        result = ct.transcribe(np.array([], dtype=np.float32), 16000)
        assert result == ""

    def test_very_short_audio_returns_empty_string(self) -> None:
        mock_store = MagicMock()
        mock_store.get_api_key.return_value = "key"

        ct = CloudTranscriber(settings_store=mock_store)

        with patch("cloud_providers.azure.AzureOpenAIProvider"):
            ct.start(
                {
                    "provider_type": "azure",
                    "endpoint_url": "https://test.openai.azure.com",
                }
            )

        # Less than 160 samples (10 ms @ 16 kHz)
        result = ct.transcribe(np.array([0.5], dtype=np.float32), 16000)
        assert result == ""

    def test_raises_if_not_started(self) -> None:
        ct = CloudTranscriber()
        with pytest.raises(TranscriptionError, match="not started"):
            ct.transcribe(np.array([0.5], dtype=np.float32), 16000)

    def test_raises_on_provider_failure(self) -> None:
        mock_store = MagicMock()
        mock_store.get_api_key.return_value = "key"

        mock_provider = MagicMock(spec=TranscriptionProvider)
        mock_provider.transcribe.side_effect = RuntimeError("API error")

        ct = CloudTranscriber(settings_store=mock_store)

        with patch(
            "cloud_providers.azure.AzureOpenAIProvider"
        ) as mock_cls:
            mock_cls.return_value = mock_provider
            ct.start(
                {
                    "provider_type": "azure",
                    "endpoint_url": "https://test.openai.azure.com",
                }
            )

        audio = np.ones(3200, dtype=np.float32) * 0.5
        with pytest.raises(TranscriptionError, match="API error"):
            ct.transcribe(audio, 16000)

    def test_maps_auto_language_to_none(self) -> None:
        """``language="auto"`` should be passed as ``None`` to provider."""
        mock_store = MagicMock()
        mock_store.get_api_key.return_value = "key"

        mock_provider = MagicMock(spec=TranscriptionProvider)
        mock_provider.transcribe.return_value = TranscriptionResult(
            text="result"
        )

        ct = CloudTranscriber(settings_store=mock_store)

        with patch(
            "cloud_providers.azure.AzureOpenAIProvider"
        ) as mock_cls:
            mock_cls.return_value = mock_provider
            ct.start(
                {
                    "provider_type": "azure",
                    "endpoint_url": "https://test.openai.azure.com",
                }
            )

        audio = np.ones(3200, dtype=np.float32) * 0.5
        ct.transcribe(audio, 16000, language="auto")

        _, call_kwargs = mock_provider.transcribe.call_args
        assert call_kwargs["language"] is None

    def test_passes_language_to_provider(self) -> None:
        """Explicit language code is forwarded."""
        mock_store = MagicMock()
        mock_store.get_api_key.return_value = "key"

        mock_provider = MagicMock(spec=TranscriptionProvider)
        mock_provider.transcribe.return_value = TranscriptionResult(
            text="result"
        )

        ct = CloudTranscriber(settings_store=mock_store)

        with patch(
            "cloud_providers.azure.AzureOpenAIProvider"
        ) as mock_cls:
            mock_cls.return_value = mock_provider
            ct.start(
                {
                    "provider_type": "azure",
                    "endpoint_url": "https://test.openai.azure.com",
                }
            )

        audio = np.ones(3200, dtype=np.float32) * 0.5
        ct.transcribe(audio, 16000, language="es")

        _, call_kwargs = mock_provider.transcribe.call_args
        assert call_kwargs["language"] == "es"


class TestCloudTranscriberStatus:
    """Status / capability checks."""

    def test_is_running_initially_false(self) -> None:
        ct = CloudTranscriber()
        assert ct.is_running() is False

    def test_supports_language_returns_true(self) -> None:
        ct = CloudTranscriber()
        assert ct.supports_language() is True


# ======================================================================
# AzureOpenAIProvider — HTTP mocking
# ======================================================================


def _make_mock_httpx_client(
    status_code: int = 200,
    json_data: dict | None = None,
    headers: dict | None = None,
    side_effect: Exception | None = None,
) -> tuple[MagicMock, MagicMock]:
    """Create a mocked ``httpx.Client`` context manager.

    Returns ``(mock_client_cls, mock_client)`` where
    ``mock_client.post`` returns or raises as configured.
    """
    mock_client = MagicMock()

    if side_effect is not None:
        mock_client.post.side_effect = side_effect
    else:
        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock_response.json.return_value = json_data or {}
        mock_response.headers = headers or {}
        mock_client.post.return_value = mock_response

    mock_client_cls = MagicMock()
    mock_client_cls.return_value.__enter__.return_value = mock_client

    return mock_client_cls, mock_client


class TestAzureOpenAIProvider:
    """Azure provider HTTP behaviour."""

    PROVIDER_KWARGS = {
        "endpoint_url": "https://test-azure.openai.azure.com",
        "api_key": "test-key-456",
        "deployment_name": "whisper-1",
        "api_version": "2025-04-01-preview",
    }

    # ------------------------------------------------------------------
    # URL construction
    # ------------------------------------------------------------------

    def test_constructs_correct_endpoint_url(self) -> None:
        """Provider should POST to the correct Azure endpoint."""
        mock_client_cls, mock_client = _make_mock_httpx_client(
            json_data={"text": "hello"}
        )

        with patch("cloud_providers.azure.httpx.Client", mock_client_cls):
            from cloud_providers.azure import AzureOpenAIProvider

            provider = AzureOpenAIProvider(**self.PROVIDER_KWARGS)
            provider.transcribe(b"fake-audio", "test.wav")

        expected_url = (
            "https://test-azure.openai.azure.com/openai/deployments/"
            "whisper-1/audio/transcriptions"
            "?api-version=2025-04-01-preview"
        )
        mock_client.post.assert_called_once()
        actual_url = mock_client.post.call_args[0][0]
        assert actual_url == expected_url

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def test_sends_api_key_header(self) -> None:
        """Provider should send ``api-key`` header, not Bearer."""
        mock_client_cls, mock_client = _make_mock_httpx_client(
            json_data={"text": "hello"}
        )

        with patch("cloud_providers.azure.httpx.Client", mock_client_cls):
            from cloud_providers.azure import AzureOpenAIProvider

            provider = AzureOpenAIProvider(**self.PROVIDER_KWARGS)
            provider.transcribe(b"fake-audio", "test.wav")

        _, kwargs = mock_client.post.call_args
        assert kwargs["headers"]["api-key"] == "test-key-456"

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def test_returns_text_from_response(self) -> None:
        """Provider returns ``TranscriptionResult`` with correct text."""
        mock_client_cls, _ = _make_mock_httpx_client(
            json_data={"text": "hello world", "language": "en"}
        )

        with patch("cloud_providers.azure.httpx.Client", mock_client_cls):
            from cloud_providers.azure import AzureOpenAIProvider

            provider = AzureOpenAIProvider(**self.PROVIDER_KWARGS)
            result = provider.transcribe(b"fake-audio", "test.wav")

        assert isinstance(result, TranscriptionResult)
        assert result.text == "hello world"
        assert result.language == "en"

    def test_preserves_raw_response(self) -> None:
        """The full response JSON should be stored in ``raw``."""
        raw_data = {"text": "hi", "language": "es", "duration": 2.5}
        mock_client_cls, _ = _make_mock_httpx_client(json_data=raw_data)

        with patch("cloud_providers.azure.httpx.Client", mock_client_cls):
            from cloud_providers.azure import AzureOpenAIProvider

            provider = AzureOpenAIProvider(**self.PROVIDER_KWARGS)
            result = provider.transcribe(b"fake-audio", "test.wav")

        assert result.raw == raw_data

    # ------------------------------------------------------------------
    # Multipart request
    # ------------------------------------------------------------------

    def test_sends_multipart_file(self) -> None:
        """Audio should be sent as a multipart ``file`` field."""
        mock_client_cls, mock_client = _make_mock_httpx_client(
            json_data={"text": "hello"}
        )

        with patch("cloud_providers.azure.httpx.Client", mock_client_cls):
            from cloud_providers.azure import AzureOpenAIProvider

            provider = AzureOpenAIProvider(**self.PROVIDER_KWARGS)
            provider.transcribe(b"\x00\x01\x02", "my_audio.wav")

        _, call_kwargs = mock_client.post.call_args
        files = call_kwargs["files"]
        assert "file" in files
        file_tuple = files["file"]
        assert file_tuple[0] == "my_audio.wav"
        assert file_tuple[1] == b"\x00\x01\x02"
        assert "audio" in file_tuple[2]

    def test_sends_language_in_form_data(self) -> None:
        """Language hint should be included in multipart form data."""
        mock_client_cls, mock_client = _make_mock_httpx_client(
            json_data={"text": "hola"}
        )

        with patch("cloud_providers.azure.httpx.Client", mock_client_cls):
            from cloud_providers.azure import AzureOpenAIProvider

            provider = AzureOpenAIProvider(**self.PROVIDER_KWARGS)
            provider.transcribe(b"fake-audio", "test.wav", language="es")

        _, call_kwargs = mock_client.post.call_args
        assert call_kwargs["data"]["language"] == "es"

    # ------------------------------------------------------------------
    # Error handling — 4xx (non-429)
    # ------------------------------------------------------------------

    def test_raises_on_4xx_config_error(self) -> None:
        """Non-retriable 4xx errors should raise immediately."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": {"message": "Invalid API key"}
        }
        mock_response.headers = {}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=MagicMock(),
            response=mock_response,
        )

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response

        mock_client_cls = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client

        with patch("cloud_providers.azure.httpx.Client", mock_client_cls):
            from cloud_providers.azure import AzureOpenAIProvider

            provider = AzureOpenAIProvider(**self.PROVIDER_KWARGS)

            with pytest.raises(RuntimeError, match="Invalid API key"):
                provider.transcribe(b"fake-audio", "test.wav")

        # Should NOT have retried
        assert mock_client.post.call_count == 1

    # ------------------------------------------------------------------
    # Error handling — 429 rate limit
    # ------------------------------------------------------------------

    def test_retries_on_429_and_succeeds(self) -> None:
        """Rate limited (429) should retry and eventually succeed."""
        retry_response = MagicMock()
        retry_response.status_code = 429
        retry_response.headers = {}

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"text": "retried successfully"}
        success_response.headers = {}

        mock_client = MagicMock()
        mock_client.post.side_effect = [retry_response, success_response]

        mock_client_cls = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client

        with patch("cloud_providers.azure.httpx.Client", mock_client_cls):
            from cloud_providers.azure import AzureOpenAIProvider

            provider = AzureOpenAIProvider(**self.PROVIDER_KWARGS)
            result = provider.transcribe(b"fake-audio", "test.wav")

        assert result.text == "retried successfully"
        assert mock_client.post.call_count == 2

    # ------------------------------------------------------------------
    # Error handling — 5xx server errors
    # ------------------------------------------------------------------

    def test_retries_on_5xx_and_succeeds(self) -> None:
        """Server errors (5xx) should retry and eventually succeed."""
        error_response = MagicMock()
        error_response.status_code = 500
        error_response.headers = {}
        error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Server Error",
            request=MagicMock(),
            response=error_response,
        )

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"text": "recovered"}
        success_response.headers = {}

        mock_client = MagicMock()
        mock_client.post.side_effect = [error_response, success_response]

        mock_client_cls = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client

        with patch("cloud_providers.azure.httpx.Client", mock_client_cls):
            from cloud_providers.azure import AzureOpenAIProvider

            provider = AzureOpenAIProvider(**self.PROVIDER_KWARGS)
            result = provider.transcribe(b"fake-audio", "test.wav")

        assert result.text == "recovered"
        assert mock_client.post.call_count == 2

    def test_fails_after_max_5xx_retries(self) -> None:
        """After exhausting retries on 5xx, should raise RuntimeError."""
        error_response = MagicMock()
        error_response.status_code = 503
        error_response.headers = {}
        error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "503 Service Unavailable",
            request=MagicMock(),
            response=error_response,
        )

        mock_client = MagicMock()
        mock_client.post.return_value = error_response

        mock_client_cls = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client

        with patch("cloud_providers.azure.httpx.Client", mock_client_cls):
            from cloud_providers.azure import AzureOpenAIProvider

            provider = AzureOpenAIProvider(**self.PROVIDER_KWARGS)

            with pytest.raises(RuntimeError, match="503|retries"):
                provider.transcribe(b"fake-audio", "test.wav")

        # Should have tried 3 times
        assert mock_client.post.call_count == 3

    # ------------------------------------------------------------------
    # Error handling — timeout
    # ------------------------------------------------------------------

    def test_raises_on_timeout(self) -> None:
        """Timeout should raise after max retries."""
        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.TimeoutException(
            "Connection timed out"
        )

        mock_client_cls = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client

        with patch("cloud_providers.azure.httpx.Client", mock_client_cls):
            from cloud_providers.azure import AzureOpenAIProvider

            provider = AzureOpenAIProvider(**self.PROVIDER_KWARGS)

            with pytest.raises(RuntimeError, match="timed out|retries"):
                provider.transcribe(b"fake-audio", "test.wav")

        assert mock_client.post.call_count == 3  # max retries

    # ------------------------------------------------------------------
    # Error handling — network error
    # ------------------------------------------------------------------

    def test_raises_on_network_error(self) -> None:
        """Network errors should raise after max retries."""
        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.RequestError("DNS resolution failed")

        mock_client_cls = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client

        with patch("cloud_providers.azure.httpx.Client", mock_client_cls):
            from cloud_providers.azure import AzureOpenAIProvider

            provider = AzureOpenAIProvider(**self.PROVIDER_KWARGS)

            with pytest.raises(RuntimeError, match="retries"):
                provider.transcribe(b"fake-audio", "test.wav")

        assert mock_client.post.call_count == 3

    # ------------------------------------------------------------------
    # Retry-After header parsing
    # ------------------------------------------------------------------

    def test_uses_retry_after_header_on_429(self) -> None:
        """Retry-After header should be respected on 429."""
        retry_response = MagicMock()
        retry_response.status_code = 429
        retry_response.headers = {"Retry-After": "0.01"}

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"text": "done"}
        success_response.headers = {}

        mock_client = MagicMock()
        mock_client.post.side_effect = [retry_response, success_response]

        mock_client_cls = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client

        with (
            patch("cloud_providers.azure.httpx.Client", mock_client_cls),
            patch("cloud_providers.azure.time.sleep") as mock_sleep,
        ):
            from cloud_providers.azure import AzureOpenAIProvider

            provider = AzureOpenAIProvider(**self.PROVIDER_KWARGS)
            result = provider.transcribe(b"fake-audio", "test.wav")

        assert result.text == "done"
        # Should have slept for ~0.01s
        mock_sleep.assert_called_once()
        assert mock_sleep.call_args[0][0] < 1.0
