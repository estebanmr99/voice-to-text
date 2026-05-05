"""Redacted local-only event logging.

Diagnostics writes structured JSON-line events to dated log files.
**All values are redacted** — only event names, timestamps, and key names
are ever persisted.  Transcript text, audio device names, and any other
PII must never appear in logs.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_MAX_LOG_FILES = 10
_MAX_LOG_SIZE_BYTES = 1 * 1024 * 1024  # 1 MB


class Diagnostics:
    """Redacted local-only event logger.

    Events are written as JSON lines to ``app-YYYY-MM-DD.log`` files inside
    the configured log directory.  Only key names are recorded; all values
    are stripped to prevent accidental leakage of transcript content or PII.
    """

    def __init__(self, log_dir: Path | None = None) -> None:
        self._log_dir = log_dir or Path.home() / ".spanglish-dictation" / "logs"
        self._ensure_dir()
        self._current_log = self._log_dir / f"app-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.log"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_dir(self) -> None:
        """Create the log directory if it does not exist."""
        self._log_dir.mkdir(parents=True, exist_ok=True)

    def get_log_path(self) -> Path:
        """Return the path to today's log file."""
        return self._current_log

    def _rotate_if_needed(self) -> None:
        """Keep at most *_MAX_LOG_FILES* log files, each under 1 MB.

        If the current log exceeds the size limit, it is renamed with a
        millisecond timestamp suffix and a new file is started.
        Old files beyond the limit are deleted.
        """
        # Rotate current log if oversized
        if self._current_log.exists() and self._current_log.stat().st_size >= _MAX_LOG_SIZE_BYTES:
            suffix = datetime.now(timezone.utc).strftime("%H%M%S%f")[:-3]
            rotated = self._current_log.with_suffix(f".log.{suffix}")
            self._current_log.rename(rotated)
            self._current_log = self._log_dir / f"app-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.log"

        # Prune old files (newest first) — always run, even if current log doesn't exist yet.
        # Leave room for the current log file we're about to write.
        log_files = sorted(
            self._log_dir.glob("app-*.log*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        # If current log already exists, it counts toward the limit; otherwise reserve 1 slot.
        keep_count = _MAX_LOG_FILES - (0 if self._current_log.exists() else 1)
        for old in log_files[keep_count:]:
            old.unlink()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def event(self, name: str, **kwargs: object) -> None:
        """Log a structured, redacted event.

        Parameters
        ----------
        name:
            Event type (e.g. ``"dictation_started"``).
        **kwargs:
            Contextual keys.  **Only the key names are written**; values
            are discarded to guarantee redaction.

        Example
        -------
        >>> diag.event("dictation_started", audio_device="Microphone (Realtek)")
        {"t": "2026-05-04T12:00:00+00:00", "e": "dictation_started", "keys": ["audio_device"]}
        """
        self._rotate_if_needed()
        payload = {
            "t": datetime.now(timezone.utc).isoformat(),
            "e": name,
            "keys": sorted(kwargs.keys()),
        }
        with self._current_log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
