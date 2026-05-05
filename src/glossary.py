"""Glossary data module — loading, validation, and merging of glossary entries.

Provides :class:`GlossaryEntry` dataclass and :class:`GlossaryStore` for
managing default and user glossary files. User entries override defaults
on ``input`` key collision.
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from settings_store import SettingsStore

logger = logging.getLogger(__name__)


@dataclass
class GlossaryEntry:
    """A single glossary entry — term mapping with optional context."""

    input: str
    """"Lowercase matching key (what Whisper produces)."""
    output: str
    """Correct rendering to apply."""
    context: str = ""
    """Optional note — not used in matching."""


class GlossaryStore:
    """Loads, validates, and merges glossary entries from default and user files.

    On construction, the *default_path* is always loaded first. If *user_path*
    is provided, user entries are merged on top — entries with the same ``input``
    key replace defaults.

    Parameters
    ----------
    default_path : Path
        Path to the built-in default glossary JSON file.
    user_path : Path | None
        Optional path to a user glossary JSON file.
    """

    def __init__(
        self,
        default_path: Path,
        user_path: Path | None = None,
    ) -> None:
        self._default_path = default_path
        self._user_path = user_path

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self) -> list[GlossaryEntry]:
        """Return merged glossary entries: defaults + user overrides.

        User entries with the same ``input`` key replace default entries.
        Missing or corrupt user files are handled gracefully — defaults
        are always returned.
        """
        defaults = self._load_json(self._default_path)
        if defaults is None:
            return []

        # Build dict so user overrides can replace by input key
        merged: dict[str, dict[str, Any]] = {}
        for entry in defaults:
            merged[entry["input"]] = entry

        # Merge user glossary on top
        if self._user_path is not None:
            user_entries = self._load_json(self._user_path)
            if user_entries is not None:
                for entry in user_entries:
                    merged[entry["input"]] = entry

        return [
            GlossaryEntry(
                input=e["input"],
                output=e["output"],
                context=e.get("context", ""),
            )
            for e in merged.values()
        ]

    @staticmethod
    def _load_json(path: Path) -> list[dict[str, Any]] | None:
        """Load glossary entries list from a JSON file.

        Returns ``None`` if the file is missing or corrupt.
        """
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, dict) or "entries" not in data:
                logger.warning("Glossary file %s missing 'entries' key.", path)
                return None
            if not isinstance(data["entries"], list):
                logger.warning("Glossary file %s 'entries' is not a list.", path)
                return None
            return data["entries"]
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load glossary from %s: %s", path, exc)
            return None

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self, entries: list[dict[str, Any]]) -> list[str]:
        """Validate a list of entry dicts.

        Returns an empty list on success, or a list of error strings on failure.

        Checks:
        - Each entry has ``"input"`` (str, non-empty)
        - Each entry has ``"output"`` (str, non-empty)
        """
        errors: list[str] = []
        for i, entry in enumerate(entries):
            idx_label = f"entry {i}"
            if not isinstance(entry, dict):
                errors.append(f"{idx_label}: not a dict")
                continue

            inp = entry.get("input")
            if not isinstance(inp, str) or not inp.strip():
                errors.append(f"{idx_label}: missing or empty 'input' field")

            out = entry.get("output")
            if not isinstance(out, str) or not out.strip():
                errors.append(f"{idx_label}: missing or empty 'output' field")

        return errors

    # ------------------------------------------------------------------
    # Import / Export
    # ------------------------------------------------------------------

    def import_glossary(self, source_path: Path) -> list[str]:
        """Import a glossary JSON file as the user glossary.

        Validates the file, then copies it to the user glossary location
        (:attr:`_user_path`). Returns an empty list on success, or a list
        of error strings on failure.

        The imported entries will override defaults on conflict when
        :meth:`load` is next called.
        """
        # Check file exists and is readable
        if not source_path.exists():
            return [f"File not found: {source_path}"]

        try:
            with source_path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
        except json.JSONDecodeError:
            return ["Invalid JSON in glossary file"]
        except OSError as exc:
            return [f"Cannot read file: {exc}"]

        # Validate schema
        entries = data.get("entries", []) if isinstance(data, dict) else []
        if not isinstance(data, dict) or not isinstance(entries, list):
            return ['Glossary file must have an "entries" list']

        errors = self.validate(entries)
        if errors:
            return errors

        # Copy to user glossary location
        if self._user_path is None:
            return ["No user glossary path configured"]

        try:
            self._user_path.parent.mkdir(parents=True, exist_ok=True)
            with self._user_path.open("w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
        except OSError as exc:
            return [f"Failed to write user glossary: {exc}"]

        return []

    def export_glossary(self, dest_path: Path) -> None:
        """Export the current merged glossary to a JSON file.

        Writes defaults + user entries in the same schema as
        ``default_glossary.json`` for round-trip compatibility.

        Creates parent directories if needed. Raises :class:`OSError`
        only on write failure.
        """
        entries = self.get_entries_as_dicts()
        data: dict[str, Any] = {
            "entries": entries,
            "version": 1,
            "description": "Spanglish Dictation glossary export",
        }
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with dest_path.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")

    def get_entries_as_dicts(self) -> list[dict[str, Any]]:
        """Return current merged entries as a list of dicts.

        Each dict has ``"input"``, ``"output"``, and optionally ``"context"``
        (omitted when empty).
        """
        result: list[dict[str, Any]] = []
        for entry in self.load():
            item: dict[str, Any] = {
                "input": entry.input,
                "output": entry.output,
            }
            if entry.context:
                item["context"] = entry.context
            result.append(item)
        return result

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @staticmethod
    def from_settings(settings: "SettingsStore") -> "GlossaryStore":
        """Factory: create a GlossaryStore from settings.

        Uses ``settings.get("glossary_path")`` for the user glossary location.
        The default glossary path is resolved relative to the project root.
        """
        from pathlib import Path as _Path

        default_path = _Path(__file__).parent.parent / "data" / "default_glossary.json"
        user_path_str: str = settings.get("glossary_path", "")
        user_path = _Path(user_path_str) if user_path_str else None
        return GlossaryStore(default_path=default_path, user_path=user_path)
