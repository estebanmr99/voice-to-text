"""Cloud-based transcription with provider plugin architecture.

Defines :class:`TranscriptionResult`, the abstract :class:`TranscriptionProvider`
interface, and :class:`CloudTranscriber` which implements
:class:`transcriber.TranscriberInterface` for cloud backends.

The :class:`CloudTranscriber` converts numpy audio arrays to WAV bytes and
delegates HTTP calls to a :class:`TranscriptionProvider` plugin
(e.g. :class:`cloud_providers.azure.AzureOpenAIProvider`).
"""

from __future__ import annotations

import io
import logging
import wave
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from settings_store import SettingsStore
from transcriber import TranscriberInterface, TranscriptionError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class TranscriptionResult:
    """Result of a cloud provider transcription request.

    Attributes
    ----------
    text:
        The transcribed text.
    language:
        Detected or requested language code (e.g. ``"en"``, ``"es"``).
    segments:
        Optional list of per-segment transcription results with timestamps.
    raw:
        The raw provider response dict (for debugging / diagnostics).
    """

    text: str
    language: str | None = None
    segments: list | None = None
    raw: dict | None = None


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

_providers: dict[str, type["TranscriptionProvider"]] = {}
_providers_initialized: bool = False


def register_provider(name: str, cls: type["TranscriptionProvider"]) -> None:
    """Register a provider class under *name* for factory lookup."""
    _providers[name] = cls


def _ensure_providers() -> None:
    """Lazy-register built-in providers on first access.

    Uses deferred imports inside the function body to avoid circular
    dependencies (each provider module imports from ``cloud_transcriber``
    for base classes).
    """
    global _providers_initialized
    if _providers_initialized:
        return
    _providers_initialized = True

    from cloud_providers.aws import (  # type: ignore[import-untyped]  # noqa: PLC0415
        AWSTranscribeProvider,
    )

    register_provider("aws", AWSTranscribeProvider)


def get_provider_names() -> list[str]:
    """Return sorted list of registered provider names."""
    _ensure_providers()
    return sorted(_providers)


# ---------------------------------------------------------------------------
# Provider interface
# ---------------------------------------------------------------------------


class TranscriptionProvider(ABC):
    """Abstract base for cloud transcription providers.

    Each provider plugin (Azure OpenAI Whisper, AWS Transcribe, etc.)
    implements this interface.
    """

    @abstractmethod
    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str,
        language: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe *audio_bytes* and return the result.

        Parameters
        ----------
        audio_bytes:
            Raw audio bytes (typically WAV-encoded PCM).
        filename:
            Filename hint for the multipart upload (e.g. ``"audio.wav"``).
        language:
            Optional BCP-47 language code (e.g. ``"en"``, ``"es"``), or
            ``None`` for auto-detection.

        Returns
        -------
        TranscriptionResult

        Raises
        ------
        RuntimeError:
            If the API request fails after retries.
        """
        ...


# ---------------------------------------------------------------------------
# Cloud transcriber (TranscriberInterface implementation)
# ---------------------------------------------------------------------------


class CloudTranscriber(TranscriberInterface):
    """Cloud transcription backend implementing :class:`TranscriberInterface`.

    Converts numpy audio arrays to WAV bytes and delegates to a
    :class:`TranscriptionProvider` plugin for the actual HTTP calls.

    Usage::

        ct = CloudTranscriber(settings_store)
        ct.start({
            "provider_type": "azure",
            "endpoint_url": "https://my-resource.openai.azure.com",
            "deployment_name": "whisper-1",
            "api_version": "2025-04-01-preview",
            "api_key_id": "cloud/azure-prod",
        })
        text = ct.transcribe(audio_array, 16000)
        ct.stop()
    """

    def __init__(self, settings_store: SettingsStore | None = None) -> None:
        self._settings_store = settings_store or SettingsStore()
        self._provider: TranscriptionProvider | None = None
        self._config: dict[str, Any] | None = None
        self._started = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self, config: dict[str, Any]) -> None:
        """Validate config, load API key, and instantiate the provider.

        Parameters
        ----------
        config:
            Provider configuration dict with keys:

            * ``provider_type`` — ``"azure"`` (required)
            * ``endpoint_url`` — provider endpoint URL (required)
            * ``deployment_name`` — model deployment name (default ``"whisper-1"``)
            * ``api_version`` — API version string (Azure default ``"2025-04-01-preview"``)
            * ``api_key_id`` — keyring entry identifier (default ``"cloud/{provider_type}"``)

        Raises
        ------
        TranscriptionError:
            If the config is invalid or the API key is not found.
        """
        provider_type = config.get("provider_type", "").lower()
        if not provider_type:
            raise TranscriptionError("Missing 'provider_type' in cloud config")

        endpoint_url = config.get("endpoint_url", "")
        if not endpoint_url:
            raise TranscriptionError("Missing 'endpoint_url' in cloud config")

        api_key_id = config.get("api_key_id", f"cloud/{provider_type}")

        # Load API key from secure storage (keyring / DPAPI)
        api_key = self._settings_store.get_api_key(api_key_id)
        if not api_key:
            raise TranscriptionError(
                f"API key not found for '{api_key_id}'. "
                "Store it via Settings > Cloud Providers."
            )

        self._config = config

        if provider_type == "azure":
            from cloud_providers.azure import AzureOpenAIProvider

            self._provider = AzureOpenAIProvider(
                endpoint_url=endpoint_url,
                api_key=api_key,
                deployment_name=config.get("deployment_name", "whisper-1"),
                api_version=config.get("api_version", "2025-04-01-preview"),
            )
        elif provider_type == "aws":
            # AWS uses boto3 credential chain — no API key needed
            _ensure_providers()
            provider_cls = _providers.get("aws")
            if provider_cls is None:
                raise TranscriptionError(
                    "AWS Transcribe provider is not registered. "
                    "Ensure cloud_providers.aws is importable."
                )
            self._provider = provider_cls(
                region=config.get("region", "us-east-1"),
                s3_bucket=config.get("s3_bucket", ""),
            )
        else:
            raise TranscriptionError(
                f"Unknown cloud provider: '{provider_type}'"
            )

        self._started = True
        logger.info("CloudTranscriber started with provider: %s", provider_type)

    def stop(self) -> None:
        """No-op for HTTP-based cloud providers.

        HTTP clients are short-lived per request, so there is no persistent
        connection or subprocess to tear down.
        """
        self._started = False
        self._provider = None
        self._config = None
        logger.debug("CloudTranscriber stopped")

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def is_running(self) -> bool:
        """Return ``True`` if :meth:`start` was called successfully."""
        return self._started

    def supports_language(self) -> bool:
        """Cloud providers (Azure, AWS) support language hints."""
        return True

    # ------------------------------------------------------------------
    # Transcription
    # ------------------------------------------------------------------

    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int,
        language: str | None = None,
    ) -> str:
        """Convert numpy audio to WAV bytes and send to the cloud provider.

        Parameters
        ----------
        audio:
            1-D numpy array of audio samples (int16, float32, or float64).
        sample_rate:
            Sample rate in Hz.
        language:
            Language code (e.g. ``"en"``, ``"es"``) or ``"auto"`` for
            auto-detection.

        Returns
        -------
        str:
            Transcribed text, or an empty string for silent / empty audio.

        Raises
        ------
        TranscriptionError:
            If the transcriber is not running or the provider call fails.
        """
        if not self._started or self._provider is None:
            raise TranscriptionError("CloudTranscriber is not started")

        # Fast-path: empty or very short audio
        if audio is None or len(audio) < 160:  # 10 ms @ 16 kHz
            return ""

        # Convert numpy array to WAV bytes
        wav_bytes = _numpy_to_wav(audio, sample_rate)

        # Map "auto" to None (provider handles auto-detection)
        lang: str | None = language if language and language != "auto" else None

        filename = f"audio_{sample_rate}.wav"

        try:
            result = self._provider.transcribe(
                audio_bytes=wav_bytes,
                filename=filename,
                language=lang,
            )
            return result.text or ""
        except TranscriptionError:
            raise
        except Exception as exc:
            raise TranscriptionError(
                f"Cloud transcription failed: {exc}"
            ) from exc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _numpy_to_wav(audio: np.ndarray, sample_rate: int) -> bytes:
    """Convert a 1-D numpy array to WAV bytes (16-bit mono PCM).

    Parameters
    ----------
    audio:
        1-D array of int16, float32, or float64 samples.
    sample_rate:
        Sample rate in Hz.

    Returns
    -------
    bytes:
        Complete WAV file as bytes (RIFF header + PCM data).
    """
    buf = io.BytesIO()

    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit samples
        wf.setframerate(sample_rate)

        # Normalise to int16
        if audio.dtype in (np.float32, np.float64):
            audio = np.clip(audio, -1.0, 1.0)
            audio = (audio * 32767).astype(np.int16)
        elif audio.dtype != np.int16:
            # Unknown dtype — try cast
            audio = audio.astype(np.int16)

        wf.writeframes(audio.tobytes())

    return buf.getvalue()



