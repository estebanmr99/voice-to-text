"""Glossary data module — loading, validation, and merging of glossary entries.

Provides :class:`GlossaryEntry` dataclass and :class:`GlossaryStore` for
managing default and user glossary files. User entries override defaults
on ``input`` key collision.
"""

from __future__ import annotations

import json
import logging
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
