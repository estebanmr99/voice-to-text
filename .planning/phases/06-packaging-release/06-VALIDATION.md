---
phase: 06-packaging-release
status: draft
created: 2026-05-05
---

# Phase 06 Validation Strategy

## Required Automated Gates

1. Packaging unit checks: `python -m pytest tests/test_release_packaging.py -q`
2. Privacy regression: `python -m pytest tests/test_privacy_guard.py -q`
3. License bundle check: `python scripts/generate_license_bundle.py --check`
4. Release artifact verifier: `python scripts/verify_release_artifacts.py dist/release`
5. Portable build dry run: `powershell -ExecutionPolicy Bypass -File scripts/build_portable.ps1 -SkipBuild`

## Nyquist Sampling Points

- Inspect portable zip contents for absent `models/`, `*.bin`, `*.gguf`, `cudnn*.dll`, `cublas*.dll`, `cudart*.dll`.
- Inspect `dist/release/sbom.cdx.json` for runtime dependencies from `requirements.txt`.
- Inspect `LICENSES/THIRD-PARTY-NOTICES.md` for PySide6, sounddevice/PortAudio, numpy, pywhispercpp/whisper.cpp, pywin32, WebRTC VAD, model assets, and blocked CUDA/cuDNN note.
- Inspect release docs for side-loading, checksums, and no-runtime-network language.
