"""Tests for profile resolution and fallback logic."""

from __future__ import annotations

import hashlib
from pathlib import Path

from hardware_detector import HardwareInfo
from model_manager import ModelManager
from profile_resolver import resolve_profile
from settings_store import SettingsStore


def _settings(tmp_path: Path, profile: str) -> SettingsStore:
    s = SettingsStore(path=tmp_path / "settings.json")
    s.model_profile = profile
    return s


def _write_model_file(path: Path, content: bytes = b"data") -> str:
    path.write_bytes(content)
    return hashlib.sha256(content).hexdigest()


def test_resolve_cpu_portable_valid(tmp_path: Path) -> None:
    mgr = ModelManager(models_dir=tmp_path)
    _write_model_file(tmp_path / "ggml-base.bin")
    settings = _settings(tmp_path, "cpu-portable")

    result = resolve_profile(settings, mgr, HardwareInfo())
    assert result.model_info is not None
    assert result.model_info.name == "base"
    assert result.fallback_applied is False


def test_resolve_cpu_portable_fallback_to_small(tmp_path: Path) -> None:
    mgr = ModelManager(models_dir=tmp_path)
    _write_model_file(tmp_path / "ggml-small.bin")
    settings = _settings(tmp_path, "cpu-portable")

    result = resolve_profile(settings, mgr, HardwareInfo())
    assert result.model_info is not None
    assert result.model_info.name == "small"
    assert result.fallback_applied is True


def test_resolve_nvidia_dev_no_gpu(tmp_path: Path) -> None:
    mgr = ModelManager(models_dir=tmp_path)
    _write_model_file(tmp_path / "ggml-small.bin")
    settings = _settings(tmp_path, "nvidia-dev")

    result = resolve_profile(settings, mgr, HardwareInfo(has_nvidia_gpu=False))
    assert result.model_info is not None
    assert "no NVIDIA GPU detected" in result.advisory_message


def test_resolve_nvidia_dev_has_gpu_but_missing_model(tmp_path: Path) -> None:
    mgr = ModelManager(models_dir=tmp_path)
    _write_model_file(tmp_path / "ggml-base.bin")
    settings = _settings(tmp_path, "nvidia-dev")

    result = resolve_profile(settings, mgr, HardwareInfo(has_nvidia_gpu=True))
    assert result.model_info is not None
    assert result.model_info.name == "base"
    assert "Using CPU fallback" in result.advisory_message


def test_resolve_no_valid_models(tmp_path: Path) -> None:
    mgr = ModelManager(models_dir=tmp_path)
    settings = _settings(tmp_path, "cpu-portable")

    result = resolve_profile(settings, mgr, HardwareInfo())
    assert result.model_info is None
    assert result.error_message


def test_resolve_preserves_user_setting(tmp_path: Path) -> None:
    mgr = ModelManager(models_dir=tmp_path)
    _write_model_file(tmp_path / "ggml-small.bin")
    settings = _settings(tmp_path, "cpu-portable")

    _ = resolve_profile(settings, mgr, HardwareInfo())
    assert settings.model_profile == "cpu-portable"


def test_resolve_unknown_profile_uses_shipping_default(tmp_path: Path) -> None:
    mgr = ModelManager(models_dir=tmp_path)
    _write_model_file(tmp_path / "ggml-base.bin")
    settings = _settings(tmp_path, "unknown-profile")

    result = resolve_profile(settings, mgr, HardwareInfo())
    assert result.model_info is not None
    assert result.profile_used == "cpu-portable"


def test_resolve_corrupt_model_fails_checksum(tmp_path: Path) -> None:
    mgr = ModelManager(models_dir=tmp_path)
    base_path = tmp_path / "ggml-base.bin"
    base_path.write_bytes(b"corrupt")

    base = mgr.get_model("base")
    base.checksum_sha256 = "0" * 64
    mgr.register_model(base)

    _write_model_file(tmp_path / "ggml-small.bin")
    settings = _settings(tmp_path, "cpu-portable")
    result = resolve_profile(settings, mgr, HardwareInfo())

    assert result.model_info is not None
    assert result.model_info.name == "small"
    assert result.fallback_applied is True
