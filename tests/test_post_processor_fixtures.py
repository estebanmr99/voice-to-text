"""Fixture-driven tests for PostProcessor normalization engine.

Tests all Phase 5 success criteria and edge cases using
parametrized pytest fixtures for exhaustiveness.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from glossary import GlossaryStore
from post_processor import PostProcessor


@pytest.fixture
def default_post_processor():
    """PostProcessor initialized with the shipped default glossary."""
    default_path = Path(__file__).parent.parent / "data" / "default_glossary.json"
    store = GlossaryStore(default_path=default_path, user_path=None)
    return PostProcessor(store)


@pytest.fixture
def post_processor_with_overrides(tmp_path):
    """PostProcessor with a user override: pr -> Pull Request."""
    default_path = Path(__file__).parent.parent / "data" / "default_glossary.json"
    user_glossary = tmp_path / "user_glossary.json"
    user_glossary.write_text(
        '{"entries": [{"input": "pr", "output": "Pull Request"}]}',
        encoding="utf-8",
    )
    store = GlossaryStore(default_path=default_path, user_path=user_glossary)
    return PostProcessor(store)


class TestSuccessCriteria:
    """Tests matching the 5 ROADMAP success criteria exactly."""

    def test_sc1_pr_normalized(self, default_post_processor):
        """SC1: 'mergear el pr' -> 'mergear el PR'"""
        assert default_post_processor.normalize("mergear el pr") == "mergear el PR"

    def test_sc2_hotfix_unchanged(self, default_post_processor):
        """SC2: 'pushea el hotfix' unchanged"""
        assert default_post_processor.normalize("pushea el hotfix") == "pushea el hotfix"

    def test_sc3_accents_preserved(self, default_post_processor):
        """SC3: Accents and Spanish framing preserved"""
        assert default_post_processor.normalize("hacer un deploy rápido") == "hacer un deploy rápido"

    def test_sc4_no_translation(self, default_post_processor):
        """SC4: No translation -- 'deployar' stays 'deployar'"""
        result = default_post_processor.normalize("voy a deployar el hotfix")
        # 'deploy' is in 'deployar' but the glossary uses whole-word matching
        # so 'deploy' should NOT replace inside 'deployar'
        assert "deployar" in result
        # 'deploy' as a standalone word WOULD match, but it's embedded here
        # Check that deployar is preserved intact (not changed to deploy)
        assert "deployar" in result

    def test_sc5_user_override(self, post_processor_with_overrides):
        """SC5: User override works -- pr -> Pull Request"""
        assert post_processor_with_overrides.normalize("mergear el pr") == "mergear el Pull Request"


class TestWordBoundary:
    """Whole-word matching prevents partial word replacement."""

    @pytest.mark.parametrize("input_text,expected", [
        ("el pr está listo", "el PR está listo"),         # matches standalone "pr"
        ("el proceso de build", "el proceso de build"),    # "pr" inside "proceso" -- NO match
        ("preparar el deploy", "preparar el deploy"),      # "pr" inside "preparar" -- NO match
        ("el api está caído", "el API está caído"),        # matches "api"
        ("capital del país", "capital del país"),          # "api" inside "capital" -- NO match
    ])
    def test_whole_word_only(self, default_post_processor, input_text, expected):
        assert default_post_processor.normalize(input_text) == expected


class TestEdgeCases:
    """Edge cases and robustness."""

    def test_empty_string(self, default_post_processor):
        assert default_post_processor.normalize("") == ""

    def test_whitespace_only(self, default_post_processor):
        assert default_post_processor.normalize("   ") == "   "

    def test_multiple_matches_in_sentence(self, default_post_processor):
        result = default_post_processor.normalize("el pr y el api")
        assert "PR" in result
        assert "API" in result

    def test_punctuation_preserved(self, default_post_processor):
        result = default_post_processor.normalize("deploy, pr.")
        assert result == "deploy, PR."

    def test_preview_equals_normalize(self, default_post_processor):
        text = "mergear el pr"
        assert default_post_processor.preview(text) == default_post_processor.normalize(text)

    def test_no_matching_entries_returns_original(self, default_post_processor):
        assert default_post_processor.normalize("hola mundo") == "hola mundo"

    def test_applied_rules_tracking(self, default_post_processor):
        rules = default_post_processor.get_applied_rules("mergear el pr")
        assert "pr" in rules

    def test_case_insensitive_input_matching(self, default_post_processor):
        """'PR', 'Pr', and 'pr' all match the 'pr' entry."""
        assert default_post_processor.normalize("mergear el PR") == "mergear el PR"
        assert default_post_processor.normalize("mergear el Pr") == "mergear el PR"


class TestSpanglishVerbForms:
    """Spanglish verb forms should NOT be changed by the glossary."""

    def test_pushear_unchanged(self, default_post_processor):
        assert default_post_processor.normalize("voy a pushear el código") == "voy a pushear el código"

    def test_mergear_unchanged(self, default_post_processor):
        assert default_post_processor.normalize("tienes que mergear el pr") == "tienes que mergear el PR"

    def test_deployar_unchanged(self, default_post_processor):
        assert default_post_processor.normalize("vamos a deployar") == "vamos a deployar"

    def test_commitear_unchanged(self, default_post_processor):
        assert default_post_processor.normalize("acabo de commitear") == "acabo de commitear"


class TestNewAcronyms:
    """Tests for newly added acronym entries in expanded glossary."""

    def test_ui_normalized(self, default_post_processor):
        assert default_post_processor.normalize("el ui está roto") == "el UI está roto"

    def test_ux_normalized(self, default_post_processor):
        assert default_post_processor.normalize("mejorar el ux") == "mejorar el UX"

    def test_db_normalized(self, default_post_processor):
        assert default_post_processor.normalize("conectarse a la db") == "conectarse a la DB"

    def test_vm_normalized(self, default_post_processor):
        assert default_post_processor.normalize("crear una vm") == "crear una VM"

    def test_os_normalized(self, default_post_processor):
        assert default_post_processor.normalize("el os no arranca") == "el OS no arranca"

    def test_ip_normalized(self, default_post_processor):
        assert default_post_processor.normalize("cambiar la ip") == "cambiar la IP"

    def test_dns_normalized(self, default_post_processor):
        assert default_post_processor.normalize("configurar el dns") == "configurar el DNS"
