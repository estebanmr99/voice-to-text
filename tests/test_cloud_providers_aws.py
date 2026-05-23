"""Tests for the AWS Transcribe provider (``AWSTranscribeProvider``).

All tests mock ``boto3`` at the module level so no real AWS credentials
or network calls are involved.
"""

from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, call, patch

import pytest

# NOTE: boto3 is NOT installed in this venv. All tests mock boto3 to avoid
# requiring real AWS credentials. The provider imports boto3 lazily inside
# _get_clients(), so we inject a fake boto3 module into sys.modules here
# so that the lazy import resolves to a mockable object.
_fake_boto3_module = MagicMock()
sys.modules["boto3"] = _fake_boto3_module

from cloud_providers.aws import (
    AWSTranscribeProvider,
    _map_language,
    _detect_media_format,
    _extract_transcript_text,
)
from cloud_transcriber import TranscriptionResult
from transcriber import TranscriptionError

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_transcribe_job_response(
    status: str = "COMPLETED",
    transcript_uri: str = "https://s3.example.com/transcript.json",
    failure_reason: str | None = None,
) -> dict:
    """Build a fake ``get_transcription_job`` response."""
    job: dict = {
        "TranscriptionJobStatus": status,
    }
    if transcript_uri:
        job["Transcript"] = {"TranscriptFileUri": transcript_uri}
    if failure_reason:
        job["FailureReason"] = failure_reason
    return {"TranscriptionJob": job}


def _make_transcript_json(text: str = "Hello world") -> bytes:
    """Build a fake AWS Transcribe output JSON."""
    data = {
        "jobName": "test-job",
        "results": {
            "transcripts": [{"transcript": text}],
            "items": [],
        },
        "status": "COMPLETED",
    }
    return json.dumps(data).encode("utf-8")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_boto3():
    """Configure the injected fake ``boto3`` module for each test.

    Resets state before each test so ``client()`` returns fresh mocks.
    Returns a tuple ``(mock_boto3, mock_transcribe, mock_s3)``.
    """
    # Reset the global fake boto3 module
    _fake_boto3_module.reset_mock()
    mock_s3 = MagicMock()
    mock_transcribe = MagicMock()
    _fake_boto3_module.client.side_effect = [mock_transcribe, mock_s3]
    yield _fake_boto3_module, mock_transcribe, mock_s3


@pytest.fixture
def mock_urlopen():
    """Mock ``urllib.request.urlopen`` to return a controlled response."""
    with patch(
        "cloud_providers.aws.urllib.request.urlopen"
    ) as mock_urlopen:
        yield mock_urlopen


@pytest.fixture
def provider(mock_boto3):
    """Return an ``AWSTranscribeProvider`` with mocked boto3 clients."""
    _, mock_transcribe, mock_s3 = mock_boto3

    # Configure the waiter mock so wait() succeeds immediately
    mock_waiter = MagicMock()
    mock_transcribe.get_waiter.return_value = mock_waiter

    # Configure get_transcription_job to return COMPLETED
    mock_transcribe.get_transcription_job.return_value = (
        _make_transcribe_job_response()
    )

    prov = AWSTranscribeProvider(
        region="us-east-1",
        s3_bucket="test-bucket",
    )
    # Trigger lazy init so tests can inspect the call
    prov._get_clients()
    return prov


# ===================================================================
# Language code mapping
# ===================================================================


class TestLanguageMapping:
    def test_es_maps_to_es_us(self):
        assert _map_language("es") == "es-US"

    def test_en_maps_to_en_us(self):
        assert _map_language("en") == "en-US"

    def test_none_returns_none(self):
        assert _map_language(None) is None

    def test_passes_through_bcp47(self):
        assert _map_language("en-US") == "en-US"
        assert _map_language("es-419") == "es-419"

    def test_unknown_code_passes_through(self):
        assert _map_language("xx") == "xx"


# ===================================================================
# Media format detection
# ===================================================================


class TestMediaFormatDetection:
    def test_wav_format(self):
        assert _detect_media_format("audio.wav") == "wav"

    def test_mp3_format(self):
        assert _detect_media_format("audio.mp3") == "mp3"

    def test_m4a_format(self):
        assert _detect_media_format("audio.m4a") == "m4a"

    def test_fallback_to_wav_for_unknown(self):
        assert _detect_media_format("audio.xyz") == "wav"

    def test_fallback_to_wav_no_extension(self):
        assert _detect_media_format("audio") == "wav"


# ===================================================================
# S3 upload
# ===================================================================


class TestS3Upload:
    def test_upload_called_with_correct_bucket_and_key(
        self, mock_boto3, mock_urlopen
    ):
        """Verify ``put_object`` receives the expected bucket and key."""
        _, mock_transcribe, mock_s3 = mock_boto3

        # Configure waiter
        mock_waiter = MagicMock()
        mock_transcribe.get_waiter.return_value = mock_waiter
        mock_transcribe.get_transcription_job.return_value = (
            _make_transcribe_job_response()
        )

        # Configure urlopen
        mock_urlopen.return_value.__enter__.return_value.read.return_value = (
            _make_transcript_json()
        )

        prov = AWSTranscribeProvider(s3_bucket="my-bucket")
        prov.transcribe(b"audio data", "test.wav", "es")

        # Verify S3 upload
        assert mock_s3.put_object.called
        call_kwargs = mock_s3.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "my-bucket"
        assert call_kwargs["Key"].startswith("transcribe-input/")
        assert call_kwargs["Key"].endswith("test.wav")
        assert call_kwargs["Body"] == b"audio data"

    def test_upload_failure_raises_error(
        self, mock_boto3, mock_urlopen
    ):
        """When S3 upload fails, a ``TranscriptionError`` should be raised."""
        _, mock_transcribe, mock_s3 = mock_boto3

        mock_s3.put_object.side_effect = Exception("S3 is down")

        prov = AWSTranscribeProvider(s3_bucket="my-bucket")

        with pytest.raises(TranscriptionError, match="Failed to upload"):
            prov.transcribe(b"audio data", "test.wav", "en")

    def test_s3_key_uses_timestamp(
        self, mock_boto3, mock_urlopen
    ):
        """The S3 key should contain a timestamp prefix."""
        _, mock_transcribe, mock_s3 = mock_boto3
        mock_waiter = MagicMock()
        mock_transcribe.get_waiter.return_value = mock_waiter
        mock_transcribe.get_transcription_job.return_value = (
            _make_transcribe_job_response()
        )
        mock_urlopen.return_value.__enter__.return_value.read.return_value = (
            _make_transcript_json()
        )

        prov = AWSTranscribeProvider(s3_bucket="my-bucket")
        prov.transcribe(b"data", "recording.wav", "en")

        key = mock_s3.put_object.call_args[1]["Key"]
        # Should look like: transcribe-input/1234567890_recording.wav
        assert key.startswith("transcribe-input/")
        parts = key.split("/")[1].split("_", 1)
        assert parts[0].isdigit()  # timestamp
        assert parts[1] == "recording.wav"


# ===================================================================
# Transcription job
# ===================================================================


class TestTranscriptionJob:
    def test_job_started_with_correct_params(
        self, mock_boto3, mock_urlopen
    ):
        """Verify ``start_transcription_job`` receives expected parameters."""
        _, mock_transcribe, mock_s3 = mock_boto3
        mock_waiter = MagicMock()
        mock_transcribe.get_waiter.return_value = mock_waiter
        mock_transcribe.get_transcription_job.return_value = (
            _make_transcribe_job_response()
        )
        mock_urlopen.return_value.__enter__.return_value.read.return_value = (
            _make_transcript_json()
        )

        prov = AWSTranscribeProvider(s3_bucket="my-bucket")
        prov.transcribe(b"data", "audio.wav", "es")

        mock_transcribe.start_transcription_job.assert_called_once()
        call_kwargs = mock_transcribe.start_transcription_job.call_args[1]

        # Job name should start with prefix
        assert call_kwargs["TranscriptionJobName"].startswith(
            "spanglish-dictation-"
        )
        # Media URI should reference the S3 bucket
        assert call_kwargs["Media"]["MediaFileUri"].startswith(
            "s3://my-bucket/transcribe-input/"
        )
        # Media format detected from filename
        assert call_kwargs["MediaFormat"] == "wav"
        # Language code should be mapped
        assert call_kwargs["LanguageCode"] == "es-US"

    def test_job_started_with_auto_detect(
        self, mock_boto3, mock_urlopen
    ):
        """Without a language hint, ``IdentifyLanguage`` should be set."""
        _, mock_transcribe, mock_s3 = mock_boto3
        mock_waiter = MagicMock()
        mock_transcribe.get_waiter.return_value = mock_waiter
        mock_transcribe.get_transcription_job.return_value = (
            _make_transcribe_job_response()
        )
        mock_urlopen.return_value.__enter__.return_value.read.return_value = (
            _make_transcript_json()
        )

        prov = AWSTranscribeProvider(s3_bucket="my-bucket")
        prov.transcribe(b"data", "audio.mp3", None)

        call_kwargs = mock_transcribe.start_transcription_job.call_args[1]
        assert "LanguageCode" not in call_kwargs
        assert call_kwargs["IdentifyLanguage"] is True

    def test_waiter_is_used(
        self, mock_boto3, mock_urlopen
    ):
        """The built-in waiter should be called for job completion."""
        _, mock_transcribe, mock_s3 = mock_boto3
        mock_waiter = MagicMock()
        mock_transcribe.get_waiter.return_value = mock_waiter
        mock_transcribe.get_transcription_job.return_value = (
            _make_transcribe_job_response()
        )
        mock_urlopen.return_value.__enter__.return_value.read.return_value = (
            _make_transcript_json()
        )

        prov = AWSTranscribeProvider(s3_bucket="my-bucket")
        prov.transcribe(b"data", "audio.wav", "en")

        mock_transcribe.get_waiter.assert_called_once_with(
            "transcription_job_completed"
        )
        mock_waiter.wait.assert_called_once()

    def test_transcript_uri_is_fetched(
        self, mock_boto3, mock_urlopen
    ):
        """After completion, the transcript must be downloaded from the URI."""
        _, mock_transcribe, mock_s3 = mock_boto3
        mock_waiter = MagicMock()
        mock_transcribe.get_waiter.return_value = mock_waiter
        mock_transcribe.get_transcription_job.return_value = (
            _make_transcribe_job_response(
                transcript_uri="https://aws.com/transcript-output.json"
            )
        )
        mock_urlopen.return_value.__enter__.return_value.read.return_value = (
            _make_transcript_json("Transcribed text here")
        )

        prov = AWSTranscribeProvider(s3_bucket="my-bucket")
        result = prov.transcribe(b"data", "audio.wav", "en")

        # Verify transcript was fetched from the correct URI
        mock_urlopen.assert_called_once_with(
            "https://aws.com/transcript-output.json", timeout=30
        )
        assert result.text == "Transcribed text here"
        assert isinstance(result, TranscriptionResult)

    def test_job_name_contains_timestamp(
        self, mock_boto3, mock_urlopen
    ):
        """Each job name should contain a millisecond timestamp prefix."""
        _, mock_transcribe, mock_s3 = mock_boto3
        mock_waiter = MagicMock()
        mock_transcribe.get_waiter.return_value = mock_waiter
        mock_transcribe.get_transcription_job.return_value = (
            _make_transcribe_job_response()
        )
        mock_urlopen.return_value.__enter__.return_value.read.return_value = (
            _make_transcript_json()
        )

        with patch("cloud_providers.aws.time.time", return_value=1234567890.500):
            prov = AWSTranscribeProvider(s3_bucket="my-bucket")
            prov.transcribe(b"data", "a.wav", "en")

        call_kwargs = mock_transcribe.start_transcription_job.call_args[1]
        assert call_kwargs["TranscriptionJobName"] == (
            "spanglish-dictation-1234567890500"
        )


# ===================================================================
# Error handling
# ===================================================================


class TestErrorHandling:
    def test_job_failure_raises_error(
        self, mock_boto3, mock_urlopen
    ):
        """When the transcription job fails, a ``TranscriptionError`` should be raised."""
        _, mock_transcribe, mock_s3 = mock_boto3

        # Make the waiter fail (the wait call raises)
        mock_waiter = MagicMock()
        mock_waiter.wait.side_effect = Exception("Waiter failed")
        mock_transcribe.get_waiter.return_value = mock_waiter

        # Then get_transcription_job returns FAILED
        mock_transcribe.get_transcription_job.return_value = (
            _make_transcribe_job_response(
                status="FAILED",
                failure_reason="Model not available",
            )
        )

        prov = AWSTranscribeProvider(s3_bucket="my-bucket")

        with pytest.raises(
            TranscriptionError, match="failed"
        ) as exc_info:
            prov.transcribe(b"data", "audio.wav", "en")

        assert "Model not available" in str(exc_info.value)

    def test_start_job_failure(
        self, mock_boto3, mock_urlopen
    ):
        """When ``start_transcription_job`` fails, a ``TranscriptionError`` should be raised."""
        _, mock_transcribe, mock_s3 = mock_boto3

        mock_transcribe.start_transcription_job.side_effect = Exception(
            "AccessDenied"
        )

        prov = AWSTranscribeProvider(s3_bucket="my-bucket")

        with pytest.raises(
            TranscriptionError, match="failed to start"
        ):
            prov.transcribe(b"data", "audio.wav", "en")

    def test_timeout_raises_error(
        self, mock_boto3, mock_urlopen
    ):
        """When the job exceeds the timeout, a ``TranscriptionError`` should be raised."""
        _, mock_transcribe, mock_s3 = mock_boto3

        # Make the waiter fail
        mock_waiter = MagicMock()
        mock_waiter.wait.side_effect = Exception("Waiter timed out")
        mock_transcribe.get_waiter.return_value = mock_waiter

        # Keep returning IN_PROGRESS to trigger timeout
        mock_transcribe.get_transcription_job.return_value = (
            _make_transcribe_job_response(status="IN_PROGRESS")
        )

        prov = AWSTranscribeProvider(s3_bucket="my-bucket")

        with patch("cloud_providers.aws._JOB_TIMEOUT_SECONDS", 0.01):
            with pytest.raises(
                TranscriptionError, match="timed out"
            ):
                prov.transcribe(b"data", "audio.wav", "en")

    def test_missing_s3_bucket_at_construction(self):
        """Creating a provider without ``s3_bucket`` should raise."""
        with pytest.raises(
            TranscriptionError, match="s3_bucket is required"
        ):
            AWSTranscribeProvider(region="us-east-1", s3_bucket="")

    def test_boto3_not_installed(self):
        """If ``boto3`` is not installed, a clear error should be raised."""
        prov = AWSTranscribeProvider(s3_bucket="my-bucket")

        # Remove the fake boto3 from sys.modules for this test
        with patch.dict(
            "sys.modules", {"boto3": None}, clear=False
        ), patch(
            "builtins.__import__",
            side_effect=ImportError("No module named 'boto3'"),
        ):
            with pytest.raises(
                TranscriptionError, match="boto3 is required"
            ):
                prov._get_clients()

    def test_extract_transcript_text_empty(self):
        """Extracting text from an empty response should return empty string."""
        assert _extract_transcript_text({}) == ""

    def test_extract_transcript_text_normal(self):
        """Extracting text from a valid response should return the transcript."""
        data = {
            "results": {
                "transcripts": [{"transcript": "Hello world"}],
            },
        }
        assert _extract_transcript_text(data) == "Hello world"

    def test_extract_transcript_text_missing_field(self):
        """Extracting text when the transcripts list is empty."""
        data = {
            "results": {
                "transcripts": [],
            },
        }
        assert _extract_transcript_text(data) == ""

    def test_waiter_failure_falls_back_to_polling(
        self, mock_boto3, mock_urlopen
    ):
        """When the waiter fails, polling should still complete the job."""
        _, mock_transcribe, mock_s3 = mock_boto3

        # Waiter fails
        mock_waiter = MagicMock()
        mock_waiter.wait.side_effect = Exception("Waiter error")
        mock_transcribe.get_waiter.return_value = mock_waiter

        # But polling succeeds
        mock_transcribe.get_transcription_job.return_value = (
            _make_transcribe_job_response(
                transcript_uri="https://aws.com/transcript.json"
            )
        )
        mock_urlopen.return_value.__enter__.return_value.read.return_value = (
            _make_transcript_json("Fallback polling worked")
        )

        prov = AWSTranscribeProvider(s3_bucket="my-bucket")
        result = prov.transcribe(b"data", "audio.wav", "en")

        assert result.text == "Fallback polling worked"
        # Verify polling was called
        mock_transcribe.get_transcription_job.assert_called()


# ===================================================================
# Raw response passthrough
# ===================================================================


class TestRawResponse:
    def test_raw_response_in_result(
        self, mock_boto3, mock_urlopen
    ):
        """The raw AWS response should be present in the result."""
        _, mock_transcribe, mock_s3 = mock_boto3
        mock_waiter = MagicMock()
        mock_transcribe.get_waiter.return_value = mock_waiter
        mock_transcribe.get_transcription_job.return_value = (
            _make_transcribe_job_response()
        )

        transcript_data = _make_transcript_json("Test")
        mock_urlopen.return_value.__enter__.return_value.read.return_value = (
            transcript_data
        )

        prov = AWSTranscribeProvider(s3_bucket="my-bucket")
        result = prov.transcribe(b"data", "audio.wav", "en")

        assert "results" in result.raw
        assert result.raw["results"]["transcripts"][0]["transcript"] == "Test"

    def test_output_is_transcription_result(
        self, mock_boto3, mock_urlopen
    ):
        """The return type should be ``TranscriptionResult``."""
        _, mock_transcribe, mock_s3 = mock_boto3
        mock_waiter = MagicMock()
        mock_transcribe.get_waiter.return_value = mock_waiter
        mock_transcribe.get_transcription_job.return_value = (
            _make_transcribe_job_response()
        )
        mock_urlopen.return_value.__enter__.return_value.read.return_value = (
            _make_transcript_json()
        )

        prov = AWSTranscribeProvider(s3_bucket="my-bucket")
        result = prov.transcribe(b"data", "audio.wav", "en")

        assert isinstance(result, TranscriptionResult)
        assert hasattr(result, "text")
        assert hasattr(result, "raw")


# ===================================================================
# Utility function tests
# ===================================================================


class TestDetectMediaFormat:
    def test_supported_formats(self):
        for fmt in ["mp3", "mp4", "wav", "flac", "ogg", "amr", "webm", "m4a"]:
            assert _detect_media_format(f"audio.{fmt}") == fmt

    def test_case_insensitive(self):
        assert _detect_media_format("audio.WAV") == "wav"
        assert _detect_media_format("audio.MP3") == "mp3"
