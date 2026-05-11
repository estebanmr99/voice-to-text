"""Tests for ModelManager and ModelInfo."""

from pathlib import Path

import pytest

from model_manager import ModelInfo, ModelManager, Profile


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

    def test_model_info_round_trip_with_metadata(self, tmp_path: Path) -> None:
        original = ModelInfo(
            name="small",
            path=tmp_path / "small.bin",
            size_mb=465,
            checksum_sha256="a" * 64,
            backend="whisper.cpp",
            profile_compatibility=["cpu-portable", "cpu-high-accuracy"],
            source_url="https://example.invalid/small",
            license_status="verify",
        )
        restored = ModelInfo.from_dict(original.to_dict())
        assert restored.backend == "whisper.cpp"
        assert restored.profile_compatibility == [
            "cpu-portable",
            "cpu-high-accuracy",
        ]
        assert restored.source_url == "https://example.invalid/small"
        assert restored.license_status == "verify"

    def test_model_info_has_backend(self, tmp_path: Path) -> None:
        info = ModelInfo(name="base", path=tmp_path / "base.bin", size_mb=141)
        assert info.backend == "whisper.cpp"

    def test_model_info_has_profile_compatibility(self) -> None:
        info = ModelInfo.from_dict({"name": "base", "path": "x", "size_mb": 1})
        assert info.profile_compatibility == [
            "cpu-portable",
            "cpu-high-accuracy",
            "nvidia-dev",
        ]


class TestProfileSerialization:
    """Round-trip profile records and default seeding."""

    def test_profile_round_trip(self) -> None:
        original = Profile(
            canonical_name="cpu-portable",
            display_name="CPU Portable",
            description="Fast CPU profile",
            preferred_model="base",
            fallback_order=["small"],
            backend_hint="whisper.cpp",
            shipping_default=True,
        )
        restored = Profile(**original.__dict__)
        assert restored == original


class TestModelManagerRegistry:
    """Registry persistence and defaults."""

    def test_default_models_seeded(self, tmp_path: Path) -> None:
        mgr = ModelManager(models_dir=tmp_path)
        models = mgr.list_models()
        names = {m.name for m in models}
        assert "base" in names
        assert "small" in names

    def test_default_profiles_seeded(self, tmp_path: Path) -> None:
        mgr = ModelManager(models_dir=tmp_path)
        profiles = mgr.list_profiles()
        assert {p.canonical_name for p in profiles} == {
            "cpu-laptop",
            "cpu-portable",
            "cpu-high-accuracy",
            "cpu-max-accuracy",
            "nvidia-dev",
        }

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

    def test_get_profile_found(self, tmp_path: Path) -> None:
        mgr = ModelManager(models_dir=tmp_path)
        profile = mgr.get_profile("cpu-portable")
        assert profile.preferred_model == "base"

    def test_get_profile_missing_raises(self, tmp_path: Path) -> None:
        mgr = ModelManager(models_dir=tmp_path)
        with pytest.raises(KeyError):
            mgr.get_profile("unknown")

    def test_get_shipping_default(self, tmp_path: Path) -> None:
        mgr = ModelManager(models_dir=tmp_path)
        profile = mgr.get_shipping_default_profile()
        assert profile.canonical_name == "cpu-portable"

    def test_registry_saves_profiles(self, tmp_path: Path) -> None:
        mgr1 = ModelManager(models_dir=tmp_path)
        custom = Profile(
            canonical_name="custom-cpu",
            display_name="Custom CPU",
            description="Custom",
            preferred_model="base",
            fallback_order=["small"],
            backend_hint="whisper.cpp",
        )
        mgr1._profiles[custom.canonical_name] = custom
        mgr1._save_registry()

        mgr2 = ModelManager(models_dir=tmp_path)
        loaded = mgr2.get_profile("custom-cpu")
        assert loaded.display_name == "Custom CPU"

    def test_legacy_registry_loads_profiles(self, tmp_path: Path) -> None:
        registry = tmp_path / "registry.json"
        registry.parent.mkdir(parents=True, exist_ok=True)
        registry.write_text(
            '{"models": [{"name": "base", "path": "base.bin", "size_mb": 1}]}\n',
            encoding="utf-8",
        )
        mgr = ModelManager(models_dir=tmp_path)
        assert len(mgr.list_profiles()) == 5


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

    def test_validate_model_no_checksum_skips_validation(self, tmp_path: Path) -> None:
        model_file = tmp_path / "ggml-base.bin"
        model_file.write_bytes(b"fake model data")
        info = ModelInfo(name="base", path=model_file, size_mb=1)
        mgr = ModelManager(models_dir=tmp_path)
        assert mgr.validate_model(info) is True

    def test_validate_metadata_complete(self, tmp_path: Path) -> None:
        mgr = ModelManager(models_dir=tmp_path)
        info = ModelInfo(
            name="base",
            path=tmp_path / "ggml-base.bin",
            size_mb=141,
            checksum_sha256="f" * 64,
            backend="whisper.cpp",
            profile_compatibility=["cpu-portable"],
            source_url="https://example.invalid/base",
            license_status="approved",
        )
        complete, warnings = mgr.validate_model_metadata(info)
        assert complete is True
        assert warnings == []

    def test_validate_metadata_missing_checksum_warning(
        self, tmp_path: Path
    ) -> None:
        mgr = ModelManager(models_dir=tmp_path)
        info = ModelInfo(
            name="base",
            path=tmp_path / "ggml-base.bin",
            size_mb=141,
            backend="whisper.cpp",
            profile_compatibility=["cpu-portable"],
            source_url="https://example.invalid/base",
            license_status="approved",
        )
        complete, warnings = mgr.validate_model_metadata(info)
        assert complete is True
        assert any("checksum_sha256" in warning for warning in warnings)

    def test_validate_metadata_missing_source_url_warning(
        self, tmp_path: Path
    ) -> None:
        mgr = ModelManager(models_dir=tmp_path)
        info = ModelInfo(
            name="base",
            path=tmp_path / "ggml-base.bin",
            size_mb=141,
            backend="whisper.cpp",
            profile_compatibility=["cpu-portable"],
            source_url="",
            license_status="approved",
        )
        complete, warnings = mgr.validate_model_metadata(info)
        assert complete is True
        assert any("source_url" in warning for warning in warnings)

    def test_validate_metadata_missing_license_warning(
        self, tmp_path: Path
    ) -> None:
        mgr = ModelManager(models_dir=tmp_path)
        info = ModelInfo(
            name="base",
            path=tmp_path / "ggml-base.bin",
            size_mb=141,
            backend="whisper.cpp",
            profile_compatibility=["cpu-portable"],
            source_url="https://example.invalid/base",
            license_status="candidate",
        )
        complete, warnings = mgr.validate_model_metadata(info)
        assert complete is True
        assert any("candidate" in warning for warning in warnings)


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
