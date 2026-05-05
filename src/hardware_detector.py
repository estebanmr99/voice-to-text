"""Windows-safe hardware detection helpers (advisory only)."""

from __future__ import annotations

import ctypes
import logging
import os
import platform
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class HardwareInfo:
    cpu_name: str = ""
    cpu_logical_cores: int = 0
    has_nvidia_gpu: bool = False
    nvidia_gpu_name: str = ""
    vram_mb: int | None = None


def _try_detect_vram_mb() -> int | None:
    """Attempt optional VRAM detection via local nvml.dll."""
    try:
        nvml = ctypes.WinDLL("nvml.dll")
        # Lightweight availability check only; full NVML binding is deferred.
        if hasattr(nvml, "nvmlInit_v2"):
            return None
    except Exception as exc:  # pragma: no cover - platform/driver dependent
        logger.debug("NVML not available: %s", exc)
    return None


def detect_hardware() -> HardwareInfo:
    """Detect local CPU and advisory NVIDIA presence.

    Never raises; returns best-effort local metadata only.
    """
    info = HardwareInfo()

    try:
        info.cpu_name = platform.processor() or ""
    except Exception as exc:
        logger.warning("CPU name detection failed: %s", exc)

    try:
        info.cpu_logical_cores = os.cpu_count() or 0
    except Exception as exc:
        logger.warning("CPU core detection failed: %s", exc)

    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                candidate = line.strip()
                if not candidate:
                    continue
                lower = candidate.lower()
                if any(token in lower for token in ("nvidia", "geforce", "rtx", "quadro")):
                    info.has_nvidia_gpu = True
                    info.nvidia_gpu_name = candidate
                    info.vram_mb = _try_detect_vram_mb()
                    break
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("GPU detection failed: %s", exc)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Unexpected hardware detection failure: %s", exc)

    return info
