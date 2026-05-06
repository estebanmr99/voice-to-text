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

logger = logging.getLogger(__name__)


class SettingsStore:
    """Persistent key-value store backed by a local JSON file.

    Known settings are exposed as typed properties with sensible defaults.
    Arbitrary keys can be read/written via :meth:`get` and :meth:`set`.

    The store attempts to load existing data on construction.  If the file
    is missing or corrupt, it silently starts from defaults.
    """

    _DEFAULTS: dict[str, Any] = {
        "hotkey_push_to_talk": "Ctrl+Shift+Space",
        "hotkey_toggle": "Ctrl+Shift+D",
        "audio_device_index": None,
        "vad_profile": "webrtc",
        "model_profile": "cpu-portable",
        "paste_mode": "immediate",
        "language": "auto",
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
