"""Tests for glossary.py — GlossaryStore and GlossaryEntry."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from glossary import GlossaryStore, GlossaryEntry


@pytest.fixture
def default_glossary_path():
    return Path(__file__).parent.parent / "data" / "default_glossary.json"


class TestGlossaryStoreLoad:
    """Tests for GlossaryStore.load() and basic operations."""

    def test_loads_default_glossary(self, default_glossary_path):
        store = GlossaryStore(default_path=default_glossary_path, user_path=None)
        entries = store.load()
        assert len(entries) > 0
        assert all(isinstance(e, GlossaryEntry) for e in entries)

    def test_load_returns_entries_list(self, default_glossary_path):
        store = GlossaryStore(default_path=default_glossary_path, user_path=None)
        entries = store.load()
        # Verify we have some known entries
        inputs = [e.input for e in entries]
        assert "pr" in inputs
        assert "api" in inputs
        assert "deploy" in inputs

    def test_user_glossary_overrides_defaults(self, default_glossary_path, tmp_path):
        user_path = tmp_path / "user_glossary.json"
        user_path.write_text(
            json.dumps({"entries": [{"input": "pr", "output": "Pull Request"}]}),
            encoding="utf-8",
        )
        store = GlossaryStore(default_path=default_glossary_path, user_path=user_path)
        entries = store.load()
        # Find the "pr" entry — should be the user override
        pr_entries = [e for e in entries if e.input == "pr"]
        assert len(pr_entries) == 1
        assert pr_entries[0].output == "Pull Request"


class TestGlossaryStoreValidation:
    """Tests for GlossaryStore.validate()."""

    def test_valid_entries_pass(self, default_glossary_path):
        store = GlossaryStore(default_path=default_glossary_path, user_path=None)
        entries = [
            {"input": "test", "output": "TEST"},
            {"input": "api", "output": "API", "context": "note"},
        ]
        errors = store.validate(entries)
        assert errors == []

    def test_missing_input_raises_error(self, default_glossary_path):
        store = GlossaryStore(default_path=default_glossary_path, user_path=None)
        entries = [{"output": "TEST"}]
        errors = store.validate(entries)
        assert len(errors) > 0
        assert any("input" in e.lower() for e in errors)

    def test_missing_output_raises_error(self, default_glossary_path):
        store = GlossaryStore(default_path=default_glossary_path, user_path=None)
        entries = [{"input": "test"}]
        errors = store.validate(entries)
        assert len(errors) > 0
        assert any("output" in e.lower() for e in errors)

    def test_empty_input_raises_error(self, default_glossary_path):
        store = GlossaryStore(default_path=default_glossary_path, user_path=None)
        entries = [{"input": "", "output": "TEST"}]
        errors = store.validate(entries)
        assert len(errors) > 0

    def test_empty_output_raises_error(self, default_glossary_path):
        store = GlossaryStore(default_path=default_glossary_path, user_path=None)
        entries = [{"input": "test", "output": ""}]
        errors = store.validate(entries)
        assert len(errors) > 0


class TestGlossaryStoreMissingUserFile:
    """Tests for graceful handling of missing/corrupt user glossary."""

    def test_missing_user_glossary_returns_defaults_only(self, default_glossary_path, tmp_path):
        nonexistent = tmp_path / "nonexistent.json"
        store = GlossaryStore(default_path=default_glossary_path, user_path=nonexistent)
        entries = store.load()
        assert len(entries) > 0
        # Should have default entries only
        inputs = [e.input for e in entries]
        assert "pr" in inputs

    def test_corrupt_user_json_returns_defaults_only(self, default_glossary_path, tmp_path):
        user_path = tmp_path / "bad.json"
        user_path.write_text("not valid json {{{", encoding="utf-8")
        store = GlossaryStore(default_path=default_glossary_path, user_path=user_path)
        entries = store.load()
        assert len(entries) > 0
        # Should have default entries only
        inputs = [e.input for e in entries]
        assert "pr" in inputs


class TestGlossaryStoreFromSettings:
    """Tests for GlossaryStore.from_settings() factory."""

    def test_from_settings_creates_store(self, default_glossary_path):
        from unittest.mock import MagicMock
        settings = MagicMock()
        settings.get.return_value = ""
        # Need to patch the default path since from_settings uses it internally
        with pytest.MonkeyPatch().context() as mp:
            # Actually, from_settings should get the user path from settings.get("glossary_path")
            store = GlossaryStore.from_settings(settings)
            assert isinstance(store, GlossaryStore)


class TestGlossaryEntry:
    """Tests for GlossaryEntry dataclass."""

    def test_entry_creation(self):
        entry = GlossaryEntry(input="pr", output="PR")
        assert entry.input == "pr"
        assert entry.output == "PR"
        assert entry.context == ""

    def test_entry_with_context(self):
        entry = GlossaryEntry(input="api", output="API", context="application programming interface")
        assert entry.input == "api"
        assert entry.output == "API"
        assert entry.context == "application programming interface"


class TestGlossaryImportExport:
    """Tests for GlossaryStore.import_glossary() and export_glossary()."""

    @pytest.fixture
    def store_with_user_path(self, default_glossary_path, tmp_path):
        user_path = tmp_path / "user_glossary.json"
        return GlossaryStore(default_path=default_glossary_path, user_path=user_path), tmp_path

    def test_import_valid_glossary(self, store_with_user_path):
        store, tmp = store_with_user_path
        source = tmp / "import_source.json"
        source.write_text(
            json.dumps({"entries": [{"input": "pr", "output": "Pull Request"}]}),
            encoding="utf-8",
        )
        errors = store.import_glossary(source)
        assert errors == []
        # After import, load() should include user override
        entries = store.load()
        pr_entries = [e for e in entries if e.input == "pr"]
        assert pr_entries[0].output == "Pull Request"

    def test_import_invalid_json(self, store_with_user_path):
        store, tmp = store_with_user_path
        source = tmp / "bad.json"
        source.write_text("not json {{{", encoding="utf-8")
        errors = store.import_glossary(source)
        assert len(errors) > 0
        assert any("Invalid JSON" in e for e in errors)

    def test_import_missing_keys(self, store_with_user_path):
        store, tmp = store_with_user_path
        source = tmp / "missing_keys.json"
        source.write_text(
            json.dumps({"entries": [{"output": "PR"}]}),  # missing "input"
            encoding="utf-8",
        )
        errors = store.import_glossary(source)
        assert len(errors) > 0

    def test_import_nonexistent_file(self, store_with_user_path):
        store, tmp = store_with_user_path
        source = tmp / "nonexistent.json"
        errors = store.import_glossary(source)
        assert len(errors) > 0
        assert any("File not found" in e for e in errors)

    def test_export_creates_file(self, store_with_user_path):
        store, tmp = store_with_user_path
        dest = tmp / "exported.json"
        store.export_glossary(dest)
        assert dest.exists()
        data = json.loads(dest.read_text(encoding="utf-8"))
        assert "entries" in data
        assert isinstance(data["entries"], list)
        assert len(data["entries"]) > 0

    def test_export_round_trip(self, default_glossary_path, tmp_path):
        """Export defaults, then import that file as user glossary, verify entries match."""
        user_path = tmp_path / "user.json"
        store = GlossaryStore(default_path=default_glossary_path, user_path=user_path)
        export_path = tmp_path / "exported.json"
        store.export_glossary(export_path)

        # Import the export as user glossary
        errors = store.import_glossary(export_path)
        assert errors == [], f"Import errors: {errors}"

        # The imported entries should now override defaults
        exported = json.loads(export_path.read_text(encoding="utf-8"))
        imported_entries = store.load()
        # Count should match (all defaults exported + re-imported)
        assert len(imported_entries) == len(exported["entries"])

    def test_export_includes_user_overrides(self, store_with_user_path):
        store, tmp = store_with_user_path
        # First set a user override
        user_source = tmp / "override_source.json"
        user_source.write_text(
            json.dumps({"entries": [{"input": "pr", "output": "Pull Request"}]}),
            encoding="utf-8",
        )
        store.import_glossary(user_source)

        # Export and verify override appears
        dest = tmp / "exported.json"
        store.export_glossary(dest)
        data = json.loads(dest.read_text(encoding="utf-8"))
        pr_entries = [e for e in data["entries"] if e["input"] == "pr"]
        assert len(pr_entries) == 1
        assert pr_entries[0]["output"] == "Pull Request"

    def test_import_no_user_path_configured(self, default_glossary_path, tmp_path):
        """Import fails if no user_path is set."""
        store = GlossaryStore(default_path=default_glossary_path, user_path=None)
        source = tmp_path / "source.json"
        source.write_text(
            json.dumps({"entries": [{"input": "test", "output": "TEST"}]}),
            encoding="utf-8",
        )
        errors = store.import_glossary(source)
        assert len(errors) > 0
        assert any("No user glossary path" in e for e in errors)

    def test_get_entries_as_dicts(self, default_glossary_path):
        store = GlossaryStore(default_path=default_glossary_path, user_path=None)
        entries = store.get_entries_as_dicts()
        assert isinstance(entries, list)
        assert all(isinstance(e, dict) for e in entries)
        assert all("input" in e and "output" in e for e in entries)
