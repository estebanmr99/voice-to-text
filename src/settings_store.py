"""Local preferences persistence with JSON file storage.

This module is importable without PySide6 — no GUI dependencies.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

try:
    import keyring as _keyring_lib

    _keyring_available = True
except ImportError:
    _keyring_lib = None  # type: ignore[assignment]
    _keyring_available = False

try:
    import win32crypt

    _dpapi_available = True
except ImportError:
    win32crypt = None  # type: ignore[assignment]
    _dpapi_available = False

import base64

logger = logging.getLogger(__name__)


class SettingsStore:
    """Persistent key-value store backed by a local JSON file.

    Known settings are exposed as typed properties with sensible defaults.
    Arbitrary keys can be read/written via :meth:`get` and :meth:`set`.

    The store attempts to load existing data on construction.  If the file
    is missing or corrupt, it silently starts from defaults.
    """

    _SERVICE_NAME = "SpanglishDictation"

    _DEFAULTS: dict[str, Any] = {
        "hotkey_push_to_talk": "Ctrl+Shift+Space",
        "hotkey_toggle": "Ctrl+Shift+D",
        "audio_device_index": None,
        "vad_profile": "webrtc",
        "model_profile": "cpu-portable",
        "paste_mode": "immediate",
        "language": "auto",
        "cloud_provider": "",
        "cloud_endpoint_url": "",
        "cloud_model_name": "whisper-1",
        "cloud_profiles": [],
    }

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or Path.home() / ".spanglish-dictation" / "settings.json"
        self._data: dict[str, Any] = dict(self._DEFAULTS)
        self._batch_depth = 0
        self._batch_dirty = False
        self.load()

    # ------------------------------------------------------------------
    # Low-level storage
    # ------------------------------------------------------------------

    def _ensure_dir(self) -> None:
        """Create parent directories if they do not exist."""
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> None:
        """Load settings from disk, falling back to defaults on error."""
        if not self._path.exists():
            return
        try:
            with self._path.open("r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            if isinstance(loaded, dict):
                self._data.update(loaded)
            else:
                logger.warning("Settings file did not contain a dict; using defaults.")
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load settings from %s: %s", self._path, exc)
            self._data = dict(self._DEFAULTS)

    def save(self) -> None:
        """Persist current settings to disk atomically."""
        if self._batch_depth > 0:
            self._batch_dirty = True
            return
        self._ensure_dir()
        # Write to temp file then rename for crash-safe atomic save
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=str(self._path.parent), suffix=".tmp", prefix=".settings_"
            )
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_path, str(self._path))
        except OSError as exc:
            logger.warning("Failed to save settings: %s", exc)
            # Clean up temp file if rename failed
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    def begin_batch(self) -> None:
        """Begin a batch of changes — save() calls are deferred."""
        self._batch_depth += 1

    def end_batch(self) -> None:
        """End a batch — if any changes were made, save once."""
        self._batch_depth = max(0, self._batch_depth - 1)
        if self._batch_depth == 0 and self._batch_dirty:
            self._batch_dirty = False
            self.save()

    # ------------------------------------------------------------------
    # Generic key-value API
    # ------------------------------------------------------------------

    def get(self, key: str, default: Any = None) -> Any:
        """Return the value for *key* or *default*."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set *key* to *value* and persist to disk."""
        self._data[key] = value
        self.save()

    # ------------------------------------------------------------------
    # Typed property accessors for known settings
    # ------------------------------------------------------------------

    @property
    def hotkey_push_to_talk(self) -> str:
        return self.get("hotkey_push_to_talk", self._DEFAULTS["hotkey_push_to_talk"])

    @hotkey_push_to_talk.setter
    def hotkey_push_to_talk(self, value: str) -> None:
        self.set("hotkey_push_to_talk", value)

    @property
    def hotkey_toggle(self) -> str:
        return self.get("hotkey_toggle", self._DEFAULTS["hotkey_toggle"])

    @hotkey_toggle.setter
    def hotkey_toggle(self, value: str) -> None:
        self.set("hotkey_toggle", value)

    @property
    def audio_device_index(self) -> int | None:
        return self.get("audio_device_index", self._DEFAULTS["audio_device_index"])

    @audio_device_index.setter
    def audio_device_index(self, value: int | None) -> None:
        self.set("audio_device_index", value)

    @property
    def vad_profile(self) -> str:
        return self.get("vad_profile", self._DEFAULTS["vad_profile"])

    @vad_profile.setter
    def vad_profile(self, value: str) -> None:
        self.set("vad_profile", value)

    @property
    def model_profile(self) -> str:
        return self.get("model_profile", self._DEFAULTS["model_profile"])

    @model_profile.setter
    def model_profile(self, value: str) -> None:
        self.set("model_profile", value)

    @property
    def paste_mode(self) -> str:
        return self.get("paste_mode", self._DEFAULTS["paste_mode"])

    @paste_mode.setter
    def paste_mode(self, value: str) -> None:
        self.set("paste_mode", value)

    @property
    def language(self) -> str:
        return self.get("language", self._DEFAULTS["language"])

    @language.setter
    def language(self, value: str) -> None:
        self.set("language", value)

    @property
    def glossary_path(self) -> str:
        return self.get("glossary_path", "")

    @glossary_path.setter
    def glossary_path(self, value: str) -> None:
        self.set("glossary_path", value)

    # ------------------------------------------------------------------
    # Typed property accessors for cloud settings
    # ------------------------------------------------------------------

    @property
    def cloud_provider(self) -> str:
        return self.get("cloud_provider", self._DEFAULTS["cloud_provider"])

    @cloud_provider.setter
    def cloud_provider(self, value: str) -> None:
        self.set("cloud_provider", value)

    @property
    def cloud_endpoint_url(self) -> str:
        return self.get("cloud_endpoint_url", self._DEFAULTS["cloud_endpoint_url"])

    @cloud_endpoint_url.setter
    def cloud_endpoint_url(self, value: str) -> None:
        self.set("cloud_endpoint_url", value)

    @property
    def cloud_model_name(self) -> str:
        return self.get("cloud_model_name", self._DEFAULTS["cloud_model_name"])

    @cloud_model_name.setter
    def cloud_model_name(self, value: str) -> None:
        self.set("cloud_model_name", value)

    @property
    def cloud_profiles(self) -> list:
        return self.get("cloud_profiles", self._DEFAULTS["cloud_profiles"])

    @cloud_profiles.setter
    def cloud_profiles(self, value: list) -> None:
        self.set("cloud_profiles", value)

    # ------------------------------------------------------------------
    # Secure API key storage (keyring with DPAPI fallback)
    # ------------------------------------------------------------------

    @property
    def _api_keys_path(self) -> Path:
        """Path to the DPAPI-encrypted key store file."""
        return self._path.parent / ".api_keys"

    def store_api_key(self, profile_id: str, key: str) -> bool:
        """Store an API key securely.

        Uses keyring (Windows Credential Locker) when available, falling
        back to DPAPI-encrypted file storage via pywin32.

        Args:
            profile_id: Username/identifier for the keyring entry
                       (e.g. "cloud/azure-prod").
            key: The API key to store.

        Returns:
            True if the key was stored successfully, False otherwise.
        """
        if _keyring_available:
            try:
                _keyring_lib.set_password(self._SERVICE_NAME, profile_id, key)
                return True
            except Exception as exc:
                logger.warning(
                    "keyring.set_password failed for %s: %s",
                    profile_id,
                    exc,
                )
        if _dpapi_available:
            return self._dpapi_store_key(profile_id, key)
        logger.warning(
            "No secure storage available — cannot store API key %s", profile_id
        )
        return False

    def get_api_key(self, profile_id: str) -> str | None:
        """Retrieve a stored API key.

        Args:
            profile_id: Username/identifier used during storage.

        Returns:
            The API key string, or None if not found.
        """
        if _keyring_available:
            try:
                value = _keyring_lib.get_password(
                    self._SERVICE_NAME, profile_id
                )
                if value is not None:
                    return value
            except Exception as exc:
                logger.warning(
                    "keyring.get_password failed for %s: %s",
                    profile_id,
                    exc,
                )
        if _dpapi_available:
            return self._dpapi_get_key(profile_id)
        return None

    def delete_api_key(self, profile_id: str) -> bool:
        """Delete a stored API key.

        Args:
            profile_id: Username/identifier used during storage.

        Returns:
            True if the key was deleted or did not exist, False on error.
        """
        deleted = False
        if _keyring_available:
            try:
                _keyring_lib.delete_password(
                    self._SERVICE_NAME, profile_id
                )
                deleted = True
            except _keyring_lib.errors.PasswordDeleteError:
                # Key didn't exist in keyring — that's fine
                deleted = True
            except Exception as exc:
                logger.warning(
                    "keyring.delete_password failed for %s: %s",
                    profile_id,
                    exc,
                )
        if _dpapi_available:
            dpapi_deleted = self._dpapi_delete_key(profile_id)
            deleted = deleted or dpapi_deleted
        if not _keyring_available and not _dpapi_available:
            # No storage available — nothing to delete
            deleted = True
        return deleted

    # ------------------------------------------------------------------
    # DPAPI fallback implementation
    # ------------------------------------------------------------------

    def _dpapi_store_key(self, profile_id: str, key: str) -> bool:
        """Store an API key using DPAPI encryption to a local file."""
        try:
            encrypted = win32crypt.CryptProtectData(
                key.encode("utf-16-le"), None, None, None, None, 0
            )
            if isinstance(encrypted, tuple):
                encrypted = encrypted[0]
            b64 = base64.b64encode(encrypted).decode("ascii")
            keys = self._load_dpapi_keys()
            keys[profile_id] = b64
            self._save_dpapi_keys(keys)
            return True
        except Exception as exc:
            logger.warning(
                "DPAPI store failed for %s: %s", profile_id, exc
            )
            return False

    def _dpapi_get_key(self, profile_id: str) -> str | None:
        """Retrieve a DPAPI-encrypted API key."""
        try:
            keys = self._load_dpapi_keys()
            b64 = keys.get(profile_id)
            if b64 is None:
                return None
            encrypted = base64.b64decode(b64)
            result = win32crypt.CryptUnprotectData(
                encrypted, None, None, None, 0
            )
            # CryptUnprotectData returns (description: str, data: bytes)
            if isinstance(result, tuple) and len(result) > 1:
                data = result[1]
            elif isinstance(result, tuple):
                data = result[0]
            else:
                data = result
            return data.decode("utf-16-le")
        except Exception as exc:
            logger.warning(
                "DPAPI get failed for %s: %s", profile_id, exc
            )
            return None

    def _dpapi_delete_key(self, profile_id: str) -> bool:
        """Delete a DPAPI-encrypted API key."""
        try:
            keys = self._load_dpapi_keys()
            if profile_id in keys:
                del keys[profile_id]
                self._save_dpapi_keys(keys)
            return True
        except Exception as exc:
            logger.warning(
                "DPAPI delete failed for %s: %s", profile_id, exc
            )
            return False

    def _load_dpapi_keys(self) -> dict[str, str]:
        """Load the DPAPI key store file."""
        path = self._api_keys_path
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text("utf-8"))
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load DPAPI keys: %s", exc)
            return {}

    def _save_dpapi_keys(self, keys: dict[str, str]) -> None:
        """Save the DPAPI key store file atomically."""
        path = self._api_keys_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=str(self._path.parent),
                suffix=".tmp",
                prefix=".api_keys_",
            )
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(keys, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_path, str(path))
        except OSError as exc:
            logger.warning("Failed to save DPAPI keys: %s", exc)
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
