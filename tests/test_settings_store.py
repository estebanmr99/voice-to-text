"""Tests for SettingsStore."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from settings_store import SettingsStore


class TestSettingsStoreDefaults:
    """Verify out-of-the-box values."""

    def test_default_hotkey_push_to_talk(self, tmp_path: Path) -> None:
        store = SettingsStore(path=tmp_path / "settings.json")
        assert store.hotkey_push_to_talk == "Ctrl+Shift+Space"

    def test_default_hotkey_toggle(self, tmp_path: Path) -> None:
        store = SettingsStore(path=tmp_path / "settings.json")
        assert store.hotkey_toggle == "Ctrl+Shift+D"

    def test_default_audio_device_index(self, tmp_path: Path) -> None:
        store = SettingsStore(path=tmp_path / "settings.json")
        assert store.audio_device_index is None

    def test_default_vad_profile(self, tmp_path: Path) -> None:
        store = SettingsStore(path=tmp_path / "settings.json")
        assert store.vad_profile == "webrtc"

    def test_default_model_profile(self, tmp_path: Path) -> None:
        store = SettingsStore(path=tmp_path / "settings.json")
        assert store.model_profile == "cpu-portable"

    def test_default_paste_mode(self, tmp_path: Path) -> None:
        store = SettingsStore(path=tmp_path / "settings.json")
        assert store.paste_mode == "immediate"

    def test_default_language(self, tmp_path: Path) -> None:
        store = SettingsStore(path=tmp_path / "settings.json")
        assert store.language == "auto"


class TestSettingsStorePersistence:
    """Verify load/save round-trips."""

    def test_persistence_round_trip(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"

        # First instance — mutate and persist
        store1 = SettingsStore(path=path)
        store1.hotkey_push_to_talk = "Ctrl+Shift+X"
        store1.audio_device_index = 3
        store1.vad_profile = "silero"
        store1.set("custom_key", 42)

        # Second instance — reload from disk
        store2 = SettingsStore(path=path)
        assert store2.hotkey_push_to_talk == "Ctrl+Shift+X"
        assert store2.audio_device_index == 3
        assert store2.vad_profile == "silero"
        assert store2.get("custom_key") == 42

    def test_custom_path(self, tmp_path: Path) -> None:
        custom = tmp_path / "nested" / "prefs.json"
        store = SettingsStore(path=custom)
        store.language = "es"
        assert custom.exists()
        assert custom.read_text(encoding="utf-8").startswith("{")

    def test_corrupt_file_falls_back_to_defaults(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"
        path.write_text("this is not json", encoding="utf-8")
        store = SettingsStore(path=path)
        assert store.hotkey_push_to_talk == "Ctrl+Shift+Space"
        assert store.language == "auto"

    def test_non_dict_file_falls_back_to_defaults(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"
        path.write_text("[1, 2, 3]", encoding="utf-8")
        store = SettingsStore(path=path)
        assert store.vad_profile == "webrtc"

    def test_missing_file_uses_defaults(self, tmp_path: Path) -> None:
        path = tmp_path / "does_not_exist.json"
        store = SettingsStore(path=path)
        assert store.paste_mode == "immediate"
        assert not path.exists()


class TestCloudSettingsDefaults:
    """Verify default cloud setting values."""

    def test_default_cloud_provider(self, tmp_path: Path) -> None:
        store = SettingsStore(path=tmp_path / "settings.json")
        assert store.cloud_provider == ""

    def test_default_cloud_endpoint_url(self, tmp_path: Path) -> None:
        store = SettingsStore(path=tmp_path / "settings.json")
        assert store.cloud_endpoint_url == ""

    def test_default_cloud_model_name(self, tmp_path: Path) -> None:
        store = SettingsStore(path=tmp_path / "settings.json")
        assert store.cloud_model_name == "whisper-1"

    def test_default_cloud_profiles(self, tmp_path: Path) -> None:
        store = SettingsStore(path=tmp_path / "settings.json")
        assert store.cloud_profiles == []


class TestCloudSettingsPersistence:
    """Verify cloud settings save/load round-trip."""

    def test_cloud_properties_round_trip(self, tmp_path: Path) -> None:
        path = tmp_path / "settings.json"
        store1 = SettingsStore(path=path)
        store1.cloud_provider = "azure"
        store1.cloud_endpoint_url = "https://example.openai.azure.com"
        store1.cloud_model_name = "gpt-4o-transcribe"
        store1.cloud_profiles = [
            {
                "name": "Azure Prod",
                "provider": "azure",
                "endpoint": "https://example.openai.azure.com",
                "model": "whisper-1",
                "api_key_id": "cloud/azure-prod",
            },
        ]

        store2 = SettingsStore(path=path)
        assert store2.cloud_provider == "azure"
        assert store2.cloud_endpoint_url == "https://example.openai.azure.com"
        assert store2.cloud_model_name == "gpt-4o-transcribe"
        assert len(store2.cloud_profiles) == 1
        assert store2.cloud_profiles[0]["name"] == "Azure Prod"
        assert store2.cloud_profiles[0]["api_key_id"] == "cloud/azure-prod"


class TestKeyringIntegration:
    """Verify keyring-based API key storage (mocked)."""

    def test_store_api_key_uses_keyring(self, tmp_path: Path) -> None:
        with (
            patch("settings_store._keyring_available", True),
            patch("settings_store._keyring_lib") as mock_keyring,
        ):
            store = SettingsStore(path=tmp_path / "settings.json")
            result = store.store_api_key("cloud/azure-prod", "sk-test-123")
            assert result is True
            mock_keyring.set_password.assert_called_once_with(
                "SpanglishDictation", "cloud/azure-prod", "sk-test-123",
            )

    def test_get_api_key_uses_keyring(self, tmp_path: Path) -> None:
        with (
            patch("settings_store._keyring_available", True),
            patch("settings_store._keyring_lib") as mock_keyring,
        ):
            mock_keyring.get_password.return_value = "sk-test-123"
            store = SettingsStore(path=tmp_path / "settings.json")
            result = store.get_api_key("cloud/azure-prod")
            assert result == "sk-test-123"
            mock_keyring.get_password.assert_called_once_with(
                "SpanglishDictation", "cloud/azure-prod",
            )

    def test_get_api_key_returns_none_when_missing(self, tmp_path: Path) -> None:
        with (
            patch("settings_store._keyring_available", True),
            patch("settings_store._keyring_lib") as mock_keyring,
        ):
            mock_keyring.get_password.return_value = None
            store = SettingsStore(path=tmp_path / "settings.json")
            result = store.get_api_key("cloud/nonexistent")
            assert result is None

    def test_delete_api_key_uses_keyring(self, tmp_path: Path) -> None:
        with (
            patch("settings_store._keyring_available", True),
            patch("settings_store._keyring_lib") as mock_keyring,
        ):
            store = SettingsStore(path=tmp_path / "settings.json")
            result = store.delete_api_key("cloud/azure-prod")
            assert result is True
            mock_keyring.delete_password.assert_called_once_with(
                "SpanglishDictation", "cloud/azure-prod",
            )

    def test_delete_api_key_handles_missing_key(self, tmp_path: Path) -> None:
        with (
            patch("settings_store._keyring_available", True),
            patch("settings_store._keyring_lib") as mock_keyring,
        ):
            # Simulate keyring raising PasswordDeleteError for missing key
            PasswordDeleteError = type("PasswordDeleteError", (Exception,), {})
            mock_keyring.errors.PasswordDeleteError = PasswordDeleteError
            mock_keyring.delete_password.side_effect = PasswordDeleteError("not found")
            store = SettingsStore(path=tmp_path / "settings.json")
            result = store.delete_api_key("cloud/nonexistent")
            assert result is True  # Missing key is not an error


class TestDPAPIFallback:
    """Verify DPAPI fallback when keyring is unavailable (mocked)."""

    def test_dpapi_store_key(self, tmp_path: Path) -> None:
        with (
            patch("settings_store._keyring_available", False),
            patch("settings_store._dpapi_available", True),
            patch("settings_store.win32crypt.CryptProtectData") as mock_encrypt,
        ):
            mock_encrypt.return_value = b"\x01\x02\x03encrypted"
            store = SettingsStore(path=tmp_path / "settings.json")
            result = store.store_api_key("cloud/test", "my-api-key")
            assert result is True
            # Verify key was encoded to utf-16-le before encryption
            call_data = mock_encrypt.call_args[0][0]
            assert call_data == "my-api-key".encode("utf-16-le")

    def test_dpapi_get_key(self, tmp_path: Path) -> None:
        with (
            patch("settings_store._keyring_available", False),
            patch("settings_store._dpapi_available", True),
            patch("settings_store.win32crypt.CryptProtectData") as mock_encrypt,
            patch("settings_store.win32crypt.CryptUnprotectData") as mock_decrypt,
        ):
            # Store: encrypt returns a fixed blob
            mock_encrypt.return_value = b"\x01\x02\x03encrypted"
            store = SettingsStore(path=tmp_path / "settings.json")
            store.store_api_key("cloud/test", "my-api-key")

            # Get: decrypt returns (description, data_bytes)
            mock_decrypt.return_value = ("", "my-api-key".encode("utf-16-le"))
            result = store.get_api_key("cloud/test")
            assert result == "my-api-key"

    def test_dpapi_get_key_nonexistent(self, tmp_path: Path) -> None:
        with (
            patch("settings_store._keyring_available", False),
            patch("settings_store._dpapi_available", True),
        ):
            store = SettingsStore(path=tmp_path / "settings.json")
            result = store.get_api_key("cloud/nonexistent")
            assert result is None

    def test_dpapi_delete_key(self, tmp_path: Path) -> None:
        with (
            patch("settings_store._keyring_available", False),
            patch("settings_store._dpapi_available", True),
            patch("settings_store.win32crypt.CryptProtectData") as mock_encrypt,
        ):
            mock_encrypt.return_value = b"\x01\x02\x03encrypted"
            store = SettingsStore(path=tmp_path / "settings.json")
            store.store_api_key("cloud/test", "my-api-key")

            result = store.delete_api_key("cloud/test")
            assert result is True
            assert store.get_api_key("cloud/test") is None

    def test_dpapi_delete_nonexistent_key(self, tmp_path: Path) -> None:
        with (
            patch("settings_store._keyring_available", False),
            patch("settings_store._dpapi_available", True),
        ):
            store = SettingsStore(path=tmp_path / "settings.json")
            result = store.delete_api_key("cloud/nonexistent")
            assert result is True


class TestApiKeyNotInJson:
    """Verify API keys are NEVER stored in settings JSON."""

    def test_keyring_key_not_in_settings_json(self, tmp_path: Path) -> None:
        with (
            patch("settings_store._keyring_available", True),
            patch("settings_store._keyring_lib") as mock_keyring,
        ):
            mock_keyring.get_password.return_value = None
            store = SettingsStore(path=tmp_path / "settings.json")
            store.cloud_provider = "azure"
            store.store_api_key("cloud/azure-prod", "sk-secret-456")

            raw = (tmp_path / "settings.json").read_text("utf-8")
            assert "sk-secret-456" not in raw
            assert "cloud_provider" in raw  # Non-secret data is fine

    def test_dpapi_key_not_in_settings_json(self, tmp_path: Path) -> None:
        with (
            patch("settings_store._keyring_available", False),
            patch("settings_store._dpapi_available", True),
            patch("settings_store.win32crypt.CryptProtectData") as mock_encrypt,
        ):
            mock_encrypt.return_value = b"\x01\x02\x03encrypted"
            store = SettingsStore(path=tmp_path / "settings.json")
            store.cloud_provider = "azure"  # trigger settings file creation
            store.store_api_key("cloud/azure-prod", "sk-secret-789")

            raw = (tmp_path / "settings.json").read_text("utf-8")
            assert "sk-secret-789" not in raw


class TestNoStorageAvailable:
    """Verify graceful handling when neither keyring nor DPAPI is available."""

    def test_store_returns_false(self, tmp_path: Path) -> None:
        with (
            patch("settings_store._keyring_available", False),
            patch("settings_store._dpapi_available", False),
        ):
            store = SettingsStore(path=tmp_path / "settings.json")
            result = store.store_api_key("cloud/test", "sk-test")
            assert result is False

    def test_get_returns_none(self, tmp_path: Path) -> None:
        with (
            patch("settings_store._keyring_available", False),
            patch("settings_store._dpapi_available", False),
        ):
            store = SettingsStore(path=tmp_path / "settings.json")
            result = store.get_api_key("cloud/test")
            assert result is None

    def test_delete_returns_true(self, tmp_path: Path) -> None:
        with (
            patch("settings_store._keyring_available", False),
            patch("settings_store._dpapi_available", False),
        ):
            store = SettingsStore(path=tmp_path / "settings.json")
            result = store.delete_api_key("cloud/test")
            assert result is True
