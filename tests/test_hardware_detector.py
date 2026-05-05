"""Tests for local hardware detection."""

from __future__ import annotations

import subprocess
from types import SimpleNamespace

from hardware_detector import HardwareInfo, detect_hardware


def test_detect_hardware_returns_hardware_info(monkeypatch) -> None:
    monkeypatch.setattr("platform.processor", lambda: "AMD Ryzen 5 3600")
    monkeypatch.setattr("os.cpu_count", lambda: 12)
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="Name\nIntel UHD\n"),
    )

    info = detect_hardware()
    assert isinstance(info, HardwareInfo)
    assert info.cpu_name == "AMD Ryzen 5 3600"
    assert info.cpu_logical_cores == 12


def test_detect_hardware_no_nvidia(monkeypatch) -> None:
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="Name\nIntel UHD\n"),
    )
    info = detect_hardware()
    assert info.has_nvidia_gpu is False
    assert info.nvidia_gpu_name == ""


def test_detect_hardware_has_nvidia(monkeypatch) -> None:
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout="Name\nNVIDIA GeForce RTX 2070 Super\n",
        ),
    )
    monkeypatch.setattr("hardware_detector._try_detect_vram_mb", lambda: None)
    info = detect_hardware()
    assert info.has_nvidia_gpu is True
    assert info.nvidia_gpu_name == "NVIDIA GeForce RTX 2070 Super"


def test_detect_hardware_wmic_failure(monkeypatch) -> None:
    def _raise(*args, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd="wmic")

    monkeypatch.setattr("subprocess.run", _raise)
    info = detect_hardware()
    assert info.has_nvidia_gpu is False


def test_detect_hardware_wmic_timeout(monkeypatch) -> None:
    def _raise(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="wmic", timeout=5)

    monkeypatch.setattr("subprocess.run", _raise)
    info = detect_hardware()
    assert info.has_nvidia_gpu is False


def test_detect_hardware_nvml_vram(monkeypatch) -> None:
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout="Name\nNVIDIA Quadro RTX\n",
        ),
    )
    monkeypatch.setattr("hardware_detector._try_detect_vram_mb", lambda: 8192)
    info = detect_hardware()
    assert info.has_nvidia_gpu is True
    assert info.vram_mb == 8192
