"""Tests for settings_dialog.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestSettingsDialog:
    @pytest.fixture
    def settings(self):
        s = MagicMock()
        s.hotkey_push_to_talk = "Ctrl+Alt+D"
        s.hotkey_toggle = "Ctrl+Alt+T"
        s.audio_device_index = None
        s.model_profile = "cpu-portable"
        s.vad_profile = "webrtc"
        s.paste_mode = "immediate"
        s.language = "auto"
        s.get.return_value = ""
        return s

    @pytest.fixture
    def model_manager(self):
        p1 = MagicMock(canonical_name="cpu-portable", display_name="CPU Portable")
        p2 = MagicMock(canonical_name="cpu-high-accuracy", display_name="CPU High Accuracy")
        mgr = MagicMock()
        mgr.list_profiles.return_value = [p1, p2]
        return mgr

    def test_dialog_constructs_and_populates(self, qapp, settings, model_manager):
        from settings_dialog import SettingsDialog

        with patch("settings_dialog.AudioCapture.list_devices", return_value=[{"index": 0, "name": "Mock Mic", "default_samplerate": 16000}]):
            dialog = SettingsDialog(settings=settings, audio_capture=None, model_manager=model_manager)

        assert dialog.hotkey_push_to_talk_input.text() == "Ctrl+Alt+D"
        assert dialog.hotkey_toggle_input.text() == "Ctrl+Alt+T"
        assert dialog.vad_profile_combo.currentData() == "webrtc"
        assert dialog.paste_mode_combo.currentData() == "immediate"
        assert dialog.language_combo.currentData() == "auto"

    def test_save_writes_and_calls_save(self, qapp, settings, model_manager):
        from settings_dialog import SettingsDialog

        with patch("settings_dialog.AudioCapture.list_devices", return_value=[{"index": 0, "name": "Mock Mic", "default_samplerate": 16000}]):
            dialog = SettingsDialog(settings=settings, audio_capture=None, model_manager=model_manager)

        dialog.hotkey_push_to_talk_input.setText("Ctrl+Alt+F")
        dialog.hotkey_toggle_input.setText("Win+Shift+G")
        dialog.glossary_path_input.setText("C:/tmp/glossary.json")
        dialog._on_save()

        assert settings.hotkey_push_to_talk == "Ctrl+Alt+F"
        assert settings.hotkey_toggle == "Win+Shift+G"
        settings.save.assert_called()
        settings.set.assert_any_call("glossary_path", "C:/tmp/glossary.json")

    def test_cancel_does_not_save(self, qapp, settings, model_manager):
        from settings_dialog import SettingsDialog

        with patch("settings_dialog.AudioCapture.list_devices", return_value=[]):
            dialog = SettingsDialog(settings=settings, audio_capture=None, model_manager=model_manager)

        dialog.reject()
        settings.save.assert_not_called()

    def test_hotkey_validation_rejects_bad_format(self, qapp, settings, model_manager):
        from settings_dialog import SettingsDialog

        with patch("settings_dialog.AudioCapture.list_devices", return_value=[]):
            dialog = SettingsDialog(settings=settings, audio_capture=None, model_manager=model_manager)

        dialog.hotkey_push_to_talk_input.setText("bad-hotkey")
        with patch("settings_dialog.QMessageBox.warning") as warning:
            dialog._on_save()
        warning.assert_called_once()

    def test_hotkey_validation_accepts_good_format(self, qapp, settings, model_manager):
        from settings_dialog import SettingsDialog

        with patch("settings_dialog.AudioCapture.list_devices", return_value=[]):
            dialog = SettingsDialog(settings=settings, audio_capture=None, model_manager=model_manager)

        dialog.hotkey_push_to_talk_input.setText("Ctrl+Alt+F")
        dialog.hotkey_toggle_input.setText("Win+Shift+G")
        with patch("settings_dialog.QMessageBox.warning") as warning:
            dialog._on_save()
        warning.assert_not_called()

    def test_audio_device_combo_disabled_when_sounddevice_unavailable(self, qapp, settings, model_manager):
        from settings_dialog import SettingsDialog

        with patch("settings_dialog.AudioCapture.list_devices", side_effect=RuntimeError("sounddevice missing")):
            dialog = SettingsDialog(settings=settings, audio_capture=None, model_manager=model_manager)

        assert dialog.audio_device_combo.isEnabled() is False
        assert "sounddevice not available" in dialog.audio_device_combo.itemText(0)
