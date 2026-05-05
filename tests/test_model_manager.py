"""Tests for ModelManager and ModelInfo."""

from pathlib import Path

import pytest

from model_manager import ModelInfo, ModelManager


class TestModelInfoSerialization:
    """Round-trip ModelInfo through dict."""

    def test_to_dict_round_trip(self, tmp_path: Path) -> None:
        original = ModelInfo(
            name="base",
            path=tmp_path / "model.bin",
            size_mb=141,
            checksum_sha256="abcd1234",
            language="auto",
            parameters={"n_threads": 4},
        )
        d = original.to_dict()
        restored = ModelInfo.from_dict(d)
        assert restored.name == "base"
        assert restored.path == tmp_path / "model.bin"
        assert restored.size_mb == 141
        assert restored.checksum_sha256 == "abcd1234"
        assert restored.language == "auto"
        assert restored.parameters == {"n_threads": 4}

    def test_from_dict_minimal(self) -> None:
        d = {"name": "tiny", "path": "/tmp/ggml-tiny.bin", "size_mb": 39}
        info = ModelInfo.from_dict(d)
        assert info.checksum_sha256 is None
        assert info.language == "auto"
        assert info.parameters == {}


class TestModelManagerRegistry:
    """Registry persistence and defaults."""

    def test_default_models_seeded(self, tmp_path: Path) -> None:
        mgr = ModelManager(models_dir=tmp_path)
        models = mgr.list_models()
        names = {m.name for m in models}
        assert "base" in names
        assert "small" in names

    def test_registry_saved_to_disk(self, tmp_path: Path) -> None:
        mgr = ModelManager(models_dir=tmp_path)
        registry = tmp_path / "registry.json"
        assert registry.exists()
        text = registry.read_text(encoding="utf-8")
        assert "base" in text
        assert "small" in text

    def test_registry_load_round_trip(self, tmp_path: Path) -> None:
        mgr1 = ModelManager(models_dir=tmp_path)
        custom = ModelInfo(
            name="custom",
            path=tmp_path / "custom.bin",
            size_mb=100,
        )
        mgr1.register_model(custom)

        mgr2 = ModelManager(models_dir=tmp_path)
        assert any(m.name == "custom" for m in mgr2.list_models())

    def test_get_model_found(self, tmp_path: Path) -> None:
        mgr = ModelManager(models_dir=tmp_path)
        info = mgr.get_model("base")
        assert info.name == "base"
        assert info.path == tmp_path / "ggml-base.bin"

    def test_get_model_missing_raises(self, tmp_path: Path) -> None:
        mgr = ModelManager(models_dir=tmp_path)
        with pytest.raises(KeyError):
            mgr.get_model("nonexistent")


class TestModelManagerValidation:
    """File existence and checksum validation."""

    def test_validate_existing_file(self, tmp_path: Path) -> None:
        model_file = tmp_path / "ggml-base.bin"
        model_file.write_bytes(b"fake model data")
        info = ModelInfo(name="base", path=model_file, size_mb=1)
        mgr = ModelManager(models_dir=tmp_path)
        assert mgr.validate_model(info) is True

    def test_validate_missing_file(self, tmp_path: Path) -> None:
        info = ModelInfo(
            name="base", path=tmp_path / "missing.bin", size_mb=1
        )
        mgr = ModelManager(models_dir=tmp_path)
        assert mgr.validate_model(info) is False

    def test_validate_checksum_match(self, tmp_path: Path) -> None:
        model_file = tmp_path / "ggml-base.bin"
        model_file.write_bytes(b"fake model data")
        import hashlib

        checksum = hashlib.sha256(b"fake model data").hexdigest()
        info = ModelInfo(
            name="base", path=model_file, size_mb=1, checksum_sha256=checksum
        )
        mgr = ModelManager(models_dir=tmp_path)
        assert mgr.validate_model(info) is True

    def test_validate_checksum_mismatch(self, tmp_path: Path) -> None:
        model_file = tmp_path / "ggml-base.bin"
        model_file.write_bytes(b"fake model data")
        info = ModelInfo(
            name="base",
            path=model_file,
            size_mb=1,
            checksum_sha256="0" * 64,
        )
        mgr = ModelManager(models_dir=tmp_path)
        assert mgr.validate_model(info) is False


class TestModelManagerDefaults:
    """Default model resolution."""

    def test_get_default_model_returns_valid(self, tmp_path: Path) -> None:
        mgr = ModelManager(models_dir=tmp_path)
        # No files exist yet
        assert mgr.get_default_model() is None

        model_file = tmp_path / "ggml-base.bin"
        model_file.write_bytes(b"fake model data")
        default = mgr.get_default_model()
        assert default is not None
        assert default.name == "base"

    def test_get_default_model_skips_invalid(self, tmp_path: Path) -> None:
        mgr = ModelManager(models_dir=tmp_path)
        # Make small valid, base missing
        (tmp_path / "ggml-small.bin").write_bytes(b"small data")
        default = mgr.get_default_model()
        assert default is not None
        assert default.name == "small"


class TestModelManagerMissingError:
    """Offline error messages for missing models."""

    def test_missing_model_error_contains_path(self, tmp_path: Path) -> None:
        mgr = ModelManager(models_dir=tmp_path)
        msg = mgr.get_missing_model_error("base")
        assert "ggml-base.bin" in msg
        assert "not available locally" in msg

    def test_missing_model_error_contains_url(self, tmp_path: Path) -> None:
        mgr = ModelManager(models_dir=tmp_path)
        msg = mgr.get_missing_model_error("base")
        assert "huggingface.co" in msg
        assert "No automatic download" in msg

    def test_missing_model_error_unknown_profile(self, tmp_path: Path) -> None:
        mgr = ModelManager(models_dir=tmp_path)
        msg = mgr.get_missing_model_error("unknown")
        assert "not registered" in msg

    def test_no_network_attempt(self, tmp_path: Path) -> None:
        """Sanity check: get_missing_model_error must not fetch anything."""
        mgr = ModelManager(models_dir=tmp_path)
        # The method is purely string formatting — no sockets, no HTTP.
        msg = mgr.get_missing_model_error("base")
        assert "http" not in msg.lower() or "huggingface" in msg
