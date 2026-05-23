"""Tests for main.py — wiring, profile switching, privacy guard integration."""

from pathlib import Path
from unittest.mock import MagicMock, patch

# Patch PrivacyGuard before main is imported to prevent socket
# monkey-patching in the test environment.  The patch is scoped to
# this import only — it is stopped immediately afterwards so that
# privacy_guard tests are not affected.
_pg_patcher = patch("privacy_guard.PrivacyGuard")
_pg_patcher.start()
from main import _apply_profile_change  # noqa: E402 — import after patching
_pg_patcher.stop()

from model_manager import CloudProviderConfig, ModelInfo  # noqa: E402
from profile_resolver import ProfileResolutionResult  # noqa: E402
from transcriber import TranscriptionError  # noqa: E402

import pytest  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers: build ProfileResolutionResult values quickly
# ---------------------------------------------------------------------------


def _cloud_result(
    *,
    provider_type: str = "azure",
    endpoint_url: str = "https://api.example.com",
    model_name: str = "whisper-1",
    profile_used: str = "cloud-profile",
) -> ProfileResolutionResult:
    """Return a cloud ProfileResolutionResult."""
    return ProfileResolutionResult(
        model_info=None,
        profile_used=profile_used,
        fallback_applied=False,
        is_cloud=True,
        provider_config=CloudProviderConfig(
            provider_type=provider_type,
            endpoint_url=endpoint_url,
            api_key_id="cloud/test-key",
            model_name=model_name,
        ),
    )


def _local_result(
    *,
    model_name: str = "base",
    profile_used: str = "local-profile",
    advisory_message: str = "",
    error_message: str = "",
    model_info: ModelInfo | None = None,
) -> ProfileResolutionResult:
    """Return a local ProfileResolutionResult."""
    if model_info is None:
        model_info = ModelInfo(
            name=model_name,
            path=Path("/fake/models/ggml-base.bin"),
            size_mb=500,
        )
    return ProfileResolutionResult(
        model_info=model_info,
        profile_used=profile_used,
        fallback_applied=False,
        advisory_message=advisory_message,
        error_message=error_message,
        is_cloud=False,
    )


def _make_mocks():
    """Return a dict of mock objects for _apply_profile_change parameters."""
    return {
        "settings": MagicMock(),
        "model_manager": MagicMock(),
        "transcriber": MagicMock(),
        "cloud_transcriber": MagicMock(),
        "dictation_loop": MagicMock(),
        "privacy_guard": MagicMock(),
        "shell": MagicMock(),
        "diagnostics": MagicMock(),
        "hardware_info": MagicMock(),
    }


# ---------------------------------------------------------------------------
# Cloud profile tests
# ---------------------------------------------------------------------------


class TestCloudProfile:
    """_apply_profile_change with cloud profile resolution."""

    def test_whitelist_endpoints_called(self):
        """Cloud profile should whitelist the endpoint URL."""
        mocks = _make_mocks()

        with patch("main.resolve_profile", return_value=_cloud_result()):
            _apply_profile_change(
                "cloud-profile",
                **{k: v for k, v in mocks.items()},
            )

        mocks["privacy_guard"].whitelist_endpoints.assert_called_once_with(
            ["https://api.example.com"]
        )
        mocks["cloud_transcriber"].start.assert_called_once()
        mocks["dictation_loop"].set_active_transcriber.assert_called_once_with(
            mocks["cloud_transcriber"]
        )
        mocks["privacy_guard"].revoke_whitelist.assert_not_called()

    def test_cloud_start_failure_revokes_whitelist(self):
        """If CloudTranscriber.start() raises, whitelist should be revoked."""
        mocks = _make_mocks()
        mocks["cloud_transcriber"].start.side_effect = TranscriptionError("Bad key")

        with patch("main.resolve_profile", return_value=_cloud_result()):
            _apply_profile_change(
                "cloud-profile",
                **{k: v for k, v in mocks.items()},
            )

        mocks["privacy_guard"].revoke_whitelist.assert_called_once()
        mocks["dictation_loop"].set_active_transcriber.assert_not_called()
        mocks["privacy_guard"].whitelist_endpoints.assert_called_once_with(
            ["https://api.example.com"]
        )
        mocks["diagnostics"].event.assert_any_call(
            "profile_change_failed",
            profile="cloud-profile",
            error="Bad key",
        )

    def test_missing_provider_config_shows_error(self):
        """When is_cloud=True but provider_config is None, show error."""
        mocks = _make_mocks()
        bad_result = ProfileResolutionResult(
            model_info=None,
            profile_used="broken-cloud",
            fallback_applied=False,
            is_cloud=True,
            provider_config=None,
        )

        with patch("main.resolve_profile", return_value=bad_result):
            _apply_profile_change(
                "broken-cloud",
                **{k: v for k, v in mocks.items()},
            )

        mocks["privacy_guard"].whitelist_endpoints.assert_not_called()
        mocks["cloud_transcriber"].start.assert_not_called()
        mocks["dictation_loop"].set_active_transcriber.assert_not_called()

    def test_cloud_start_called_with_correct_config(self):
        """Cloud transcriber should be started with provider config dict."""
        mocks = _make_mocks()

        with patch("main.resolve_profile", return_value=_cloud_result()):
            _apply_profile_change(
                "cloud-profile",
                **{k: v for k, v in mocks.items()},
            )

        mocks["cloud_transcriber"].start.assert_called_once_with(
            {
                "provider_type": "azure",
                "endpoint_url": "https://api.example.com",
                "api_key_id": "cloud/test-key",
                "deployment_name": "whisper-1",
            }
        )

    def test_cloud_profile_updates_tooltip(self):
        """Tooltip should show the cloud model/deployment name."""
        mocks = _make_mocks()

        with patch("main.resolve_profile", return_value=_cloud_result()):
            _apply_profile_change(
                "cloud-profile",
                **{k: v for k, v in mocks.items()},
            )

        mocks["shell"].update_profile_tooltip.assert_called_once_with("whisper-1")


# ---------------------------------------------------------------------------
# Local profile tests
# ---------------------------------------------------------------------------


class TestLocalProfile:
    """_apply_profile_change with local profile resolution."""

    def test_revoke_whitelist_called(self):
        """Local profile should revoke the whitelist."""
        mocks = _make_mocks()

        with patch("main.resolve_profile", return_value=_local_result()):
            _apply_profile_change(
                "local-profile",
                **{k: v for k, v in mocks.items()},
            )

        mocks["privacy_guard"].revoke_whitelist.assert_called_once()
        mocks["transcriber"].start.assert_called_once()
        mocks["dictation_loop"].set_active_transcriber.assert_called_once_with(
            mocks["transcriber"]
        )
        mocks["privacy_guard"].whitelist_endpoints.assert_not_called()

    def test_model_unavailable_shows_error(self):
        """Local profile with no valid model should show notification."""
        mocks = _make_mocks()
        no_model = ProfileResolutionResult(
            model_info=None,
            profile_used="local-profile",
            fallback_applied=False,
            error_message="Model file not found",
            is_cloud=False,
        )

        with patch("main.resolve_profile", return_value=no_model):
            _apply_profile_change(
                "local-profile",
                **{k: v for k, v in mocks.items()},
            )

        mocks["transcriber"].start.assert_not_called()
        mocks["shell"].show_notification.assert_called_once()
        mocks["privacy_guard"].revoke_whitelist.assert_called_once()

    def test_local_start_failure_does_not_switch_transcriber(self):
        """Local transcriber start failure should not switch active transcriber."""
        mocks = _make_mocks()
        mocks["transcriber"].start.return_value = False

        with patch("main.resolve_profile", return_value=_local_result()):
            _apply_profile_change(
                "local-profile",
                **{k: v for k, v in mocks.items()},
            )

        mocks["dictation_loop"].set_active_transcriber.assert_not_called()
        mocks["diagnostics"].event.assert_any_call(
            "profile_change_model_load_failed",
            profile="local-profile",
        )

    def test_both_transcribers_stopped_on_local_profile(self):
        """Both local and cloud transcribers are stopped before starting local."""
        mocks = _make_mocks()

        with patch("main.resolve_profile", return_value=_local_result()):
            _apply_profile_change(
                "local-profile",
                **{k: v for k, v in mocks.items()},
            )

        mocks["transcriber"].stop.assert_called_once()
        mocks["cloud_transcriber"].stop.assert_called_once()


# ---------------------------------------------------------------------------
# Mode switch tests
# ---------------------------------------------------------------------------


class TestModeSwitch:
    """Switching between cloud and local profiles."""

    def test_switch_from_local_to_cloud_changes_active_transcriber(self):
        """Switching to cloud should activate the cloud transcriber."""
        mocks = _make_mocks()

        with patch("main.resolve_profile", return_value=_cloud_result()):
            _apply_profile_change(
                "cloud-profile",
                **{k: v for k, v in mocks.items()},
            )

        mocks["dictation_loop"].set_active_transcriber.assert_called_once_with(
            mocks["cloud_transcriber"]
        )
        mocks["privacy_guard"].whitelist_endpoints.assert_called_once()

    def test_switch_from_cloud_to_local_changes_active_transcriber(self):
        """Switching to local should activate the local transcriber."""
        mocks = _make_mocks()

        with patch("main.resolve_profile", return_value=_local_result()):
            _apply_profile_change(
                "local-profile",
                **{k: v for k, v in mocks.items()},
            )

        mocks["dictation_loop"].set_active_transcriber.assert_called_once_with(
            mocks["transcriber"]
        )
        mocks["privacy_guard"].revoke_whitelist.assert_called_once()
        mocks["privacy_guard"].whitelist_endpoints.assert_not_called()
