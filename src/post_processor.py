"""Post-processor for deterministic Spanglish glossary normalization.

Applies glossary entries as whole-word, case-insensitive replacements to
transcription text. No translation, no LLM rewriting, no meaning change.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from glossary import GlossaryStore, GlossaryEntry


class PostProcessor:
    """Apply glossary normalization to transcription text.

    Loads glossary entries eagerly on construction and applies them as
    word-boundary-aware regex replacements in :meth:`normalize`.

    Parameters
    ----------
    glossary_store : GlossaryStore
        The store providing merged glossary entries.
    """

    def __init__(self, glossary_store: "GlossaryStore") -> None:
        self._store = glossary_store
        self._entries: list["GlossaryEntry"] = glossary_store.load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def normalize(self, text: str) -> str:
        """Apply glossary entries to *text* and return normalized result.

        Each glossary entry is matched as a whole word (word-boundary-aware)
        using case-insensitive regex. A single pass is made — each word
        position is matched at most once, in entry order.

        Returns the normalized text. Empty string returns empty string.
        Text with no matches returns the original text unchanged.
        """
        if not text:
            return text

        result = text
        for entry in self._entries:
            pattern = re.compile(
                rf"\b{re.escape(entry.input)}\b",
                re.IGNORECASE,
            )
            result = pattern.sub(entry.output, result)

        return result

    def preview(self, text: str) -> str:
        """Same as :meth:`normalize` — alias for confirmation mode."""
        return self.normalize(text)

    def get_applied_rules(self, text: str) -> list[str]:
        """Return list of **input** terms that matched in *text*.

        Does NOT log or return raw transcript text — only the glossary
        input keys that were matched.
        """
        if not text:
            return []

        matched: list[str] = []
        for entry in self._entries:
            pattern = re.compile(
                rf"\b{re.escape(entry.input)}\b",
                re.IGNORECASE,
            )
            if pattern.search(text):
                matched.append(entry.input)

        return matched
