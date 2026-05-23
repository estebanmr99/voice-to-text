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
        s.cloud_provider = ""
        s.cloud_endpoint_url = ""
        s.cloud_model_name = "whisper-1"
        s.cloud_profiles = []
        s.store_api_key.return_value = True
        s.get_api_key.return_value = None
        s.delete_api_key.return_value = True
        s.get.return_value = ""
        return s

    @pytest.fixture
    def model_manager(self):
        p1 = MagicMock(canonical_name="cpu-portable", display_name="CPU Portable")
        p2 = MagicMock(canonical_name="cpu-high-accuracy", display_name="CPU High Accuracy")
        p3 = MagicMock(canonical_name="cloud-azure-default", display_name="Cloud - Azure Whisper", mode="cloud")
        mgr = MagicMock()
        mgr.list_profiles.return_value = [p1, p2, p3]
        return mgr

    def test_dialog_constructs_and_populates(self, qapp, settings, model_manager):
        from settings_dialog import SettingsDialog

        with patch("settings_dialog.AudioCapture.list_devices", return_value=[{"index": 0, "name": "Mock Mic", "display_name": "Mock Mic — WASAPI (1 channel)", "default_samplerate": 16000}]):
            dialog = SettingsDialog(settings=settings, audio_capture=None, model_manager=model_manager)

        assert dialog.hotkey_push_to_talk_input.text() == "Ctrl+Alt+D"
        assert dialog.hotkey_toggle_input.text() == "Ctrl+Alt+T"
        assert dialog.vad_profile_combo.currentData() == "webrtc"
        assert dialog.paste_mode_combo.currentData() == "immediate"
        assert dialog.language_combo.currentData() == "auto"
        assert dialog.audio_device_combo.itemText(1) == "Mock Mic — WASAPI (1 channel)"

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
        settings.begin_batch.assert_called()
        settings.end_batch.assert_called()
        settings.set.assert_any_call("glossary_path", "C:/tmp/glossary.json")

    def test_save_emits_settings_applied(self, qapp, settings, model_manager):
        from settings_dialog import SettingsDialog

        with patch("settings_dialog.AudioCapture.list_devices", return_value=[]):
            dialog = SettingsDialog(settings=settings, audio_capture=None, model_manager=model_manager)

        seen = []
        dialog.settings_applied.connect(lambda: seen.append(True))
        dialog._on_save()

        assert seen == [True]

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

    def test_glossary_import_export_buttons_exist(self, qapp, settings, model_manager):
        from settings_dialog import SettingsDialog
        from unittest.mock import MagicMock

        glossary_store = MagicMock()
        with patch("settings_dialog.AudioCapture.list_devices", return_value=[]):
            dialog = SettingsDialog(
                settings=settings, audio_capture=None,
                model_manager=model_manager, glossary_store=glossary_store,
            )

        assert hasattr(dialog, "import_button")
        assert hasattr(dialog, "export_button")
        assert dialog.import_button.text() == "Import..."
        assert dialog.export_button.text() == "Export..."

    def test_glossary_import_button_calls_handler(self, qapp, settings, model_manager):
        from settings_dialog import SettingsDialog
        from unittest.mock import MagicMock

        glossary_store = MagicMock()
        with patch("settings_dialog.AudioCapture.list_devices", return_value=[]):
            dialog = SettingsDialog(
                settings=settings, audio_capture=None,
                model_manager=model_manager, glossary_store=glossary_store,
            )

        with patch("settings_dialog.QFileDialog.getOpenFileName", return_value=("", "")):
            with patch.object(dialog, "_on_import_glossary") as mock_handler:
                dialog.import_button.click()
                mock_handler.assert_called_once()

    def test_glossary_export_button_calls_handler(self, qapp, settings, model_manager):
        from settings_dialog import SettingsDialog
        from unittest.mock import MagicMock

        glossary_store = MagicMock()
        with patch("settings_dialog.AudioCapture.list_devices", return_value=[]):
            dialog = SettingsDialog(
                settings=settings, audio_capture=None,
                model_manager=model_manager, glossary_store=glossary_store,
            )

        with patch("settings_dialog.QFileDialog.getSaveFileName", return_value=("", "")):
            with patch.object(dialog, "_on_export_glossary") as mock_handler:
                dialog.export_button.click()
                mock_handler.assert_called_once()

    def test_cloud_provider_group_exists(self, qapp, settings, model_manager):
        """Test that all cloud provider UI elements are present."""
        from settings_dialog import SettingsDialog

        with patch("settings_dialog.AudioCapture.list_devices", return_value=[]):
            dialog = SettingsDialog(settings=settings, audio_capture=None, model_manager=model_manager)

        assert hasattr(dialog, "cloud_provider_combo")
        assert hasattr(dialog, "cloud_endpoint_input")
        assert hasattr(dialog, "cloud_api_key_input")
        assert hasattr(dialog, "cloud_model_input")
        assert hasattr(dialog, "cloud_region_input")
        assert hasattr(dialog, "cloud_save_button")
        assert hasattr(dialog, "cloud_delete_button")
        assert hasattr(dialog, "cloud_test_button")
        assert hasattr(dialog, "cloud_profile_combo")

    def test_cloud_fields_accept_input(self, qapp, settings, model_manager):
        """Test that cloud provider fields accept and return user input."""
        from settings_dialog import SettingsDialog

        with patch("settings_dialog.AudioCapture.list_devices", return_value=[]):
            dialog = SettingsDialog(settings=settings, audio_capture=None, model_manager=model_manager)

        dialog.cloud_endpoint_input.setText("https://test.azure.com")
        dialog.cloud_api_key_input.setText("secret-key-123")
        dialog.cloud_model_input.setText("whisper-2")
        dialog.cloud_region_input.setText("eu-west-1")

        assert dialog.cloud_endpoint_input.text() == "https://test.azure.com"
        assert dialog.cloud_api_key_input.text() == "secret-key-123"
        assert dialog.cloud_model_input.text() == "whisper-2"
        assert dialog.cloud_region_input.text() == "eu-west-1"

    def test_cloud_api_key_field_has_password_mode(self, qapp, settings, model_manager):
        """Test that the API key field uses password echo mode."""
        from PySide6.QtWidgets import QLineEdit
        from settings_dialog import SettingsDialog

        with patch("settings_dialog.AudioCapture.list_devices", return_value=[]):
            dialog = SettingsDialog(settings=settings, audio_capture=None, model_manager=model_manager)

        assert dialog.cloud_api_key_input.echoMode() == QLineEdit.EchoMode.Password

    def test_model_profile_combo_includes_cloud_profiles(self, qapp, settings, model_manager):
        """Test that the model profile combo shows cloud profiles."""
        from settings_dialog import SettingsDialog

        with patch("settings_dialog.AudioCapture.list_devices", return_value=[]):
            dialog = SettingsDialog(settings=settings, audio_capture=None, model_manager=model_manager)

        items = [dialog.model_profile_combo.itemText(i) for i in range(dialog.model_profile_combo.count())]
        assert "Cloud - Azure Whisper" in items
        assert "CPU Portable" in items
        assert "CPU High Accuracy" in items

    def test_save_cloud_settings(self, qapp, settings, model_manager):
        """Test that cloud settings are saved on dialog save."""
        from settings_dialog import SettingsDialog

        with patch("settings_dialog.AudioCapture.list_devices", return_value=[]):
            dialog = SettingsDialog(settings=settings, audio_capture=None, model_manager=model_manager)

        # Set cloud fields
        dialog.cloud_provider_combo.setCurrentIndex(1)  # AWS Transcribe
        dialog.cloud_endpoint_input.setText("https://aws.example.com")
        dialog.cloud_api_key_input.setText("test-api-key-123")
        dialog.cloud_model_input.setText("my-model")
        dialog.cloud_region_input.setText("us-west-2")

        dialog.hotkey_push_to_talk_input.setText("Ctrl+Alt+F")
        dialog.hotkey_toggle_input.setText("Win+Shift+G")
        dialog._on_save()

        assert settings.cloud_provider == "aws"
        assert settings.cloud_endpoint_url == "https://aws.example.com"
        assert settings.cloud_model_name == "my-model"
        settings.store_api_key.assert_called_with("cloud/main", "test-api-key-123")
