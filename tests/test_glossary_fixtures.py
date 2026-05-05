"""Fixture-driven tests for default glossary integrity."""

from __future__ import annotations

import json
from pathlib import Path

from glossary import GlossaryStore

DEFAULT_GLOSSARY = Path(__file__).parent.parent / "data" / "default_glossary.json"


class TestDefaultGlossaryIntegrity:
    """Validate the shipped default glossary file."""

    def test_loads_without_error(self):
        store = GlossaryStore(default_path=DEFAULT_GLOSSARY, user_path=None)
        entries = store.load()
        assert len(entries) > 0

    def test_no_duplicate_inputs(self):
        store = GlossaryStore(default_path=DEFAULT_GLOSSARY, user_path=None)
        entries = store.load()
        inputs = [e.input for e in entries]
        duplicates = [i for i in inputs if inputs.count(i) > 1]
        assert len(duplicates) == 0, f"Duplicate inputs found: {set(duplicates)}"

    def test_all_entries_have_non_empty_input_and_output(self):
        store = GlossaryStore(default_path=DEFAULT_GLOSSARY, user_path=None)
        entries = store.load()
        for entry in entries:
            assert entry.input.strip(), f"Empty input in entry: {entry}"
            assert entry.output.strip(), f"Empty output for input '{entry.input}'"

    def test_all_entries_are_lowercase_input(self):
        """Default glossary inputs should be lowercase for case-insensitive matching."""
        store = GlossaryStore(default_path=DEFAULT_GLOSSARY, user_path=None)
        entries = store.load()
        for entry in entries:
            assert entry.input == entry.input.lower(), (
                f"Non-lowercase input: '{entry.input}'"
            )

    def test_json_is_valid_and_has_entries_key(self):
        data = json.loads(DEFAULT_GLOSSARY.read_text(encoding="utf-8"))
        assert "entries" in data
        assert isinstance(data["entries"], list)
        assert len(data["entries"]) > 0

    def test_json_has_version(self):
        data = json.loads(DEFAULT_GLOSSARY.read_text(encoding="utf-8"))
        assert "version" in data
        assert data["version"] == 1

    def test_entry_count(self):
        """Verify the expanded glossary has at least the original 25 + new terms."""
        store = GlossaryStore(default_path=DEFAULT_GLOSSARY, user_path=None)
        entries = store.load()
        assert len(entries) >= 38  # original 25 + 7 new acronyms + 4 identity + 4 verbs + 2 others

    def test_spanglish_verb_entries_exist(self):
        """Verify Spanglish verb identity entries are present."""
        store = GlossaryStore(default_path=DEFAULT_GLOSSARY, user_path=None)
        inputs = [e.input for e in store.load()]
        for verb in ("pushear", "mergear", "deployar", "commitear"):
            assert verb in inputs, f"Missing Spanglish verb: '{verb}'"

    def test_round_trip_via_export_import(self, tmp_path):
        """Export default glossary, import as user glossary, entries match."""
        store = GlossaryStore(default_path=DEFAULT_GLOSSARY, user_path=None)
        original_entries = store.load()

        export_path = tmp_path / "exported.json"
        store.export_glossary(export_path)

        user_path = tmp_path / "user.json"
        store2 = GlossaryStore(default_path=DEFAULT_GLOSSARY, user_path=user_path)
        errors = store2.import_glossary(export_path)
        assert errors == [], f"Import errors: {errors}"

        imported_entries = store2.load()
        # Count should match — all entries from default get exported and re-imported
        assert len(imported_entries) == len(original_entries)
