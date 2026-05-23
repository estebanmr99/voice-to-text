"""Integration-style tests for profile change application logic."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

# Scope-limited patch: prevent PrivacyGuard monkey-patching during import.
# Stopped immediately afterwards so other tests are not affected.
_pg_patcher = patch("privacy_guard.PrivacyGuard")
_pg_patcher.start()
from main import _apply_profile_change  # noqa: E402 — import after patching
_pg_patcher.stop()

from model_manager import ModelInfo
from profile_resolver import ProfileResolutionResult


class TestProfileChangeIntegration:
    def test_profile_change_restarts_transcriber(self) -> None:
        settings = MagicMock()
        model_manager = MagicMock()
        transcriber = MagicMock()
        transcriber.start.return_value = True
        cloud_transcriber = MagicMock()
        dictation_loop = MagicMock()
        privacy_guard = MagicMock()
        shell = MagicMock()
        diagnostics = MagicMock()
        hardware_info = MagicMock()

        mock_result = ProfileResolutionResult(
            model_info=ModelInfo(name="small", path=Path("small.bin"), size_mb=465),
            profile_used="cpu-high-accuracy",
            fallback_applied=False,
        )

        with patch("main.resolve_profile", return_value=mock_result):
            _apply_profile_change(
                "cpu-high-accuracy",
                settings,
                model_manager,
                transcriber,
                cloud_transcriber,
                dictation_loop,
                privacy_guard,
                shell,
                diagnostics,
                hardware_info,
            )

        transcriber.stop.assert_called_once()
        cloud_transcriber.stop.assert_called_once()
        transcriber.start.assert_called_once_with(mock_result.model_info)
        shell.update_profile_tooltip.assert_called_once_with("small")
        privacy_guard.revoke_whitelist.assert_called_once()

    def test_profile_change_failed_shows_notification(self) -> None:
        settings = MagicMock()
        model_manager = MagicMock()
        transcriber = MagicMock()
        cloud_transcriber = MagicMock()
        dictation_loop = MagicMock()
        privacy_guard = MagicMock()
        shell = MagicMock()
        diagnostics = MagicMock()
        hardware_info = MagicMock()

        mock_result = ProfileResolutionResult(
            model_info=None,
            profile_used="nvidia-dev",
            fallback_applied=False,
            error_message="Model missing",
        )
        with patch("main.resolve_profile", return_value=mock_result):
            _apply_profile_change(
                "nvidia-dev",
                settings,
                model_manager,
                transcriber,
                cloud_transcriber,
                dictation_loop,
                privacy_guard,
                shell,
                diagnostics,
                hardware_info,
            )

        shell.show_notification.assert_called_once()
        transcriber.start.assert_not_called()
        privacy_guard.revoke_whitelist.assert_called_once()
