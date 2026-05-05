"""Tests for SettingsStore."""

from pathlib import Path

import pytest

from settings_store import SettingsStore


class TestSettingsStoreDefaults:
    """Verify out-of-the-box values."""

    def test_default_hotkey_push_to_talk(self, tmp_path: Path) -> None:
        store = SettingsStore(path=tmp_path / "settings.json")
        assert store.hotkey_push_to_talk == "Ctrl+Alt+D"

    def test_default_hotkey_toggle(self, tmp_path: Path) -> None:
        store = SettingsStore(path=tmp_path / "settings.json")
        assert store.hotkey_toggle == "Ctrl+Alt+T"

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
        assert store.hotkey_push_to_talk == "Ctrl+Alt+D"
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
