"""AWS Transcribe provider plugin.

Transcribes audio by:
1. Uploading to S3
2. Starting an async transcription job
3. Polling for completion
4. Downloading the transcript JSON from ``TranscriptFileUri``

Credentials are resolved through the standard **boto3 credential chain**
(``AWS_ACCESS_KEY_ID`` / ``AWS_SECRET_ACCESS_KEY`` env vars,
``~/.aws/credentials`` file, IAM role).  No API keys are passed directly.

Usage::

    from cloud_providers.aws import AWSTranscribeProvider

    provider = AWSTranscribeProvider(
        region="us-east-1",
        s3_bucket="my-transcribe-bucket",
    )
    result = provider.transcribe(audio_bytes, "recording.wav", "es")
    print(result.text)
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
from typing import Any

from cloud_transcriber import TranscriptionProvider, TranscriptionResult
from transcriber import TranscriptionError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_JOB_TIMEOUT_SECONDS = 30 * 60  # 30 minutes
_POLL_INTERVAL_SECONDS = 5

# ISO 639-1 → AWS BCP-47 language code mapping.
# AWS Transcribe requires codes like "en-US", "es-US", etc.
_LANGUAGE_MAP: dict[str, str] = {
    "en": "en-US",
    "es": "es-US",
    "fr": "fr-FR",
    "de": "de-DE",
    "it": "it-IT",
    "pt": "pt-BR",
    "ja": "ja-JP",
    "ko": "ko-KR",
    "zh": "zh-CN",
    "ar": "ar-SA",
    "ru": "ru-RU",
    "hi": "hi-IN",
}

# Supported audio formats for AWS Transcribe.
_SUPPORTED_FORMATS = {"mp3", "mp4", "wav", "flac", "ogg", "amr", "webm", "m4a"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _map_language(language: str | None) -> str | None:
    """Convert a short language code to AWS BCP-47 format.

    Returns ``None`` when *language* is ``None`` (enabling auto-detect).
    Passes through codes already in BCP-47 format.
    """
    if language is None:
        return None
    mapped = _LANGUAGE_MAP.get(language)
    if mapped is not None:
        return mapped
    # Already in BCP-47-like format (e.g. "en-US", "es-419")
    if isinstance(language, str) and len(language) == 5 and "-" in language:
        return language
    logger.warning("Unknown language code %r, passing through", language)
    return language


def _detect_media_format(filename: str) -> str:
    """Extract and validate the media format from *filename*.

    Falls back to ``"wav"`` for unknown extensions.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "wav"
    return ext if ext in _SUPPORTED_FORMATS else "wav"


def _build_job_params(
    job_name: str,
    media_file_uri: str,
    language_code: str | None,
) -> dict[str, Any]:
    """Build the ``start_transcription_job`` parameter dict."""
    media_format = _detect_media_format(media_file_uri)

    params: dict[str, Any] = {
        "TranscriptionJobName": job_name,
        "Media": {"MediaFileUri": media_file_uri},
        "MediaFormat": media_format,
    }

    if language_code:
        params["LanguageCode"] = language_code
    else:
        params["IdentifyLanguage"] = True

    return params


def _extract_transcript_text(transcript_data: dict[str, Any]) -> str:
    """Extract the full transcript text from the AWS JSON response.

    AWS Transcribe returns ``results.transcripts[0].transcript``.
    Returns empty string on any parse failure.
    """
    try:
        results = transcript_data.get("results", {})
        transcripts = results.get("transcripts", [])
        if transcripts:
            return transcripts[0].get("transcript", "")
    except Exception:
        logger.exception("Failed to extract transcript text from AWS response")
    return ""


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class AWSTranscribeProvider(TranscriptionProvider):
    """Transcribe audio using AWS Transcribe via S3 upload + async job.

    Parameters
    ----------
    region:
        AWS region name (default ``"us-east-1"``).
    s3_bucket:
        S3 bucket for audio upload and transcript output.
    """

    def __init__(
        self,
        region: str = "us-east-1",
        s3_bucket: str = "",
    ) -> None:
        if not s3_bucket:
            raise TranscriptionError(
                "s3_bucket is required for AWSTranscribeProvider"
            )

        self._region = region
        self._s3_bucket = s3_bucket
        self._client: Any = None  # boto3 transcribe client (lazy)
        self._s3_client: Any = None  # boto3 S3 client (lazy)

    # ------------------------------------------------------------------
    # Internal: lazy boto3 init
    # ------------------------------------------------------------------

    def _get_clients(self) -> tuple[Any, Any]:
        """Lazy-initialise and return ``(transcribe_client, s3_client)``."""
        if self._client is not None:
            return self._client, self._s3_client

        try:
            import boto3
        except ImportError as exc:
            raise TranscriptionError(
                "boto3 is required for AWS Transcribe. "
                "Install with: pip install boto3"
            ) from exc

        try:
            self._client = boto3.client("transcribe", region_name=self._region)
            self._s3_client = boto3.client("s3", region_name=self._region)
        except Exception as exc:
            raise TranscriptionError(
                f"Failed to create boto3 client: {exc}"
            ) from exc

        return self._client, self._s3_client

    # ------------------------------------------------------------------
    # TranscriptionProvider interface
    # ------------------------------------------------------------------

    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str,
        language: str | None = None,
    ) -> TranscriptionResult:
        """Upload audio to S3, start a transcription job, wait, and return result.

        Parameters
        ----------
        audio_bytes:
            Raw audio data bytes.
        filename:
            Original audio filename (used for format detection and S3 key).
        language:
            Language hint (e.g. ``"en"``, ``"es"``) or ``None`` for auto-detect.

        Returns
        -------
        TranscriptionResult
            Contains transcribed text and the raw AWS response.

        Raises
        ------
        TranscriptionError
            On S3 upload failure, job failure, or timeout.
        """
        client, s3_client = self._get_clients()

        # 1. Generate unique S3 key
        timestamp = int(time.time() * 1000)
        safe_filename = filename.replace(" ", "_")
        s3_key = f"transcribe-input/{timestamp}_{safe_filename}"
        media_file_uri = f"s3://{self._s3_bucket}/{s3_key}"

        # 2. Upload audio to S3
        self._upload_to_s3(s3_client, audio_bytes, s3_key)

        # 3. Start transcription job
        job_name = f"spanglish-dictation-{timestamp}"
        language_code = _map_language(language)
        job_params = _build_job_params(job_name, media_file_uri, language_code)

        try:
            client.start_transcription_job(**job_params)
        except Exception as exc:
            raise TranscriptionError(
                f"AWS Transcribe job failed to start: {exc}"
            ) from exc

        # 4. Wait for completion and get transcript URI
        transcript_uri = self._wait_for_job(client, job_name)

        # 5. Download transcript JSON
        transcript_data = self._download_transcript(transcript_uri)

        # 6. Extract text
        text = _extract_transcript_text(transcript_data)

        return TranscriptionResult(text=text, raw=transcript_data)

    # ------------------------------------------------------------------
    # S3 upload
    # ------------------------------------------------------------------

    def _upload_to_s3(
        self, s3_client: Any, audio_bytes: bytes, s3_key: str
    ) -> None:
        """Upload *audio_bytes* to the configured S3 bucket."""
        try:
            s3_client.put_object(
                Bucket=self._s3_bucket,
                Key=s3_key,
                Body=audio_bytes,
            )
        except Exception as exc:
            raise TranscriptionError(
                f"Failed to upload audio to S3 (bucket={self._s3_bucket}, "
                f"key={s3_key}): {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Job polling
    # ------------------------------------------------------------------

    def _wait_for_job(self, client: Any, job_name: str) -> str:
        """Poll for transcription job completion.

        Returns the ``TranscriptFileUri`` from the completed job.

        Raises ``TranscriptionError`` on failure or timeout.
        """
        # Attempt to use the built-in waiter
        try:
            waiter = client.get_waiter("transcription_job_completed")
            waiter.wait(
                TranscriptionJobName=job_name,
                WaiterConfig={
                    "Delay": _POLL_INTERVAL_SECONDS,
                    "MaxAttempts": _JOB_TIMEOUT_SECONDS // _POLL_INTERVAL_SECONDS,
                },
            )
        except Exception as waiter_exc:
            logger.debug(
                "Waiter failed (%s); falling back to polling", waiter_exc
            )

        # Always verify the final state via get_transcription_job
        return self._poll_until_complete(client, job_name)

    def _poll_until_complete(self, client: Any, job_name: str) -> str:
        """Poll ``get_transcription_job`` until ``COMPLETED`` or ``FAILED``.

        Used as a fallback when the waiter times out, and as the
        authoritative final status check after the waiter returns.
        """
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > _JOB_TIMEOUT_SECONDS:
                raise TranscriptionError(
                    f"AWS Transcribe job {job_name!r} timed out after "
                    f"{_JOB_TIMEOUT_SECONDS}s"
                )

            try:
                response = client.get_transcription_job(
                    TranscriptionJobName=job_name
                )
            except Exception as exc:
                raise TranscriptionError(
                    f"Failed to get transcription job status: {exc}"
                ) from exc

            job = response.get("TranscriptionJob", {})
            status = job.get("TranscriptionJobStatus", "UNKNOWN")

            if status == "COMPLETED":
                transcript_uri = (
                    job.get("Transcript", {}).get("TranscriptFileUri")
                )
                if not transcript_uri:
                    raise TranscriptionError(
                        "Transcription job completed but no "
                        "TranscriptFileUri found"
                    )
                return transcript_uri

            if status == "FAILED":
                failure_reason = job.get("FailureReason", "Unknown error")
                raise TranscriptionError(
                    f"AWS Transcribe job {job_name!r} failed: "
                    f"{failure_reason}"
                )

            time.sleep(_POLL_INTERVAL_SECONDS)

    # ------------------------------------------------------------------
    # Transcript download
    # ------------------------------------------------------------------

    @staticmethod
    def _download_transcript(transcript_uri: str) -> dict[str, Any]:
        """Download the transcript JSON from *transcript_uri*.

        The URI is a pre-signed S3 URL returned by AWS Transcribe.
        Uses stdlib ``urllib.request`` to minimise dependencies.
        """
        try:
            with urllib.request.urlopen(transcript_uri, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            raise TranscriptionError(
                f"Failed to download transcript from {transcript_uri}: {exc}"
            ) from exc
        return data
