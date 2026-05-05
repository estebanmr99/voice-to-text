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
