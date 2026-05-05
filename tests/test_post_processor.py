"""Tests for post_processor.py — PostProcessor normalization engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from glossary import GlossaryStore
from post_processor import PostProcessor


@pytest.fixture
def default_processor():
    """PostProcessor initialized with the shipped default glossary."""
    default_path = Path(__file__).parent.parent / "data" / "default_glossary.json"
    store = GlossaryStore(default_path=default_path, user_path=None)
    return PostProcessor(store)


class TestPostProcessorNormalize:
    """Tests for PostProcessor.normalize()."""

    def test_pr_normalized(self, default_processor):
        """'mergear el pr' → 'mergear el PR'"""
        assert default_processor.normalize("mergear el pr") == "mergear el PR"

    def test_hotfix_unchanged(self, default_processor):
        """'pushea el hotfix' remains unchanged."""
        assert default_processor.normalize("pushea el hotfix") == "pushea el hotfix"

    def test_accents_preserved(self, default_processor):
        """Accented Spanish text preserved exactly."""
        assert default_processor.normalize("hacer un deploy rápido") == "hacer un deploy rápido"

    def test_api_normalized(self, default_processor):
        """'el api está caído' → 'el API está caído'"""
        assert default_processor.normalize("el api está caído") == "el API está caído"

    def test_pr_whole_word_only(self, default_processor):
        """'crear un pr' matches whole word only — not 'proceso'."""
        assert default_processor.normalize("crear un pr") == "crear un PR"

    def test_preview_returns_normalized(self, default_processor):
        """preview() returns normalized text."""
        text = "mergear el pr"
        assert default_processor.preview(text) == default_processor.normalize(text)

    def test_empty_string(self, default_processor):
        """Empty string returns empty string."""
        assert default_processor.normalize("") == ""

    def test_no_matches_returns_original(self, default_processor):
        """Text with no glossary matches returns unchanged."""
        assert default_processor.normalize("hola mundo") == "hola mundo"

    def test_multiple_matches_in_sentence(self, default_processor):
        """Multiple glossary terms in one sentence all get normalized."""
        result = default_processor.normalize("el pr y el api")
        assert "PR" in result
        assert "API" in result

    def test_case_insensitive_matching(self, default_processor):
        """Case-insensitive matching: 'PR', 'Pr', 'pr' all match."""
        assert default_processor.normalize("mergear el PR") == "mergear el PR"
        assert default_processor.normalize("mergear el Pr") == "mergear el PR"

    def test_punctuation_preserved(self, default_processor):
        """Punctuation around matched terms is preserved."""
        assert default_processor.normalize("deploy, pr.") == "deploy, PR."

    def test_get_applied_rules(self, default_processor):
        """get_applied_rules returns matched input terms."""
        rules = default_processor.get_applied_rules("mergear el pr")
        assert "pr" in rules

    def test_get_applied_rules_no_matches(self, default_processor):
        """get_applied_rules returns empty list when nothing matches."""
        rules = default_processor.get_applied_rules("hola mundo")
        assert rules == []

    def test_no_translation_of_verb_forms(self, default_processor):
        """Spanglish verb forms are not modified — 'deployar' stays 'deployar'."""
        result = default_processor.normalize("voy a deployar el hotfix")
        # "deployar" should be preserved — the glossary has "deploy" as entry, not "deployar"
        # Whole-word matching: "deploy" does NOT match inside "deployar"
        assert "deployar" in result


class TestPostProcessorWithOverrides:
    """Tests with user glossary overrides."""

    def test_user_override_applied(self, tmp_path):
        """User glossary entry overrides default."""
        default_path = Path(__file__).parent.parent / "data" / "default_glossary.json"
        user_path = tmp_path / "user_glossary.json"
        user_path.write_text(
            '{"entries": [{"input": "pr", "output": "Pull Request"}]}',
            encoding="utf-8",
        )
        store = GlossaryStore(default_path=default_path, user_path=user_path)
        processor = PostProcessor(store)
        assert processor.normalize("mergear el pr") == "mergear el Pull Request"
