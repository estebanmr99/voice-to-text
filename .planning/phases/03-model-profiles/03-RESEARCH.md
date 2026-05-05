# Phase 3: Model Profiles — Research

**Date:** 2026-05-05
**Phase:** 03-model-profiles

## Question

What do I need to know to PLAN the Model Profiles phase well?

## Standard Stack

- **Python 3.11+** — Existing codebase uses dataclasses, type hints, pathlib
- **JSON file storage** — Registry already persisted as JSON; extend for profiles
- **ctypes / wmic** — Windows hardware detection without external dependencies
- **No new PyPI dependencies** — Hardware detection should use stdlib + ctypes to preserve offline guarantee

## Architecture Patterns

- **Extend, don't replace** — ModelManager, SettingsStore, Transcriber seams from Phase 2 must remain intact
- **Profile as mapping layer** — Profile names (`cpu-portable`, `cpu-high-accuracy`, `nvidia-dev`) map to model slots + backend hints; they do not replace model registry entries
- **Advisory hardware detection** — Detect NVIDIA/VRAM where feasible, but never auto-install, download, or require exact hardware
- **Fail closed on checksums** — Missing checksum = warning; present checksum = enforced mismatch failure

## Registry Extension

Current registry stores `ModelInfo` objects keyed by model name (`base`, `small`).
Phase 3 needs:

1. **Profile definitions** — Map canonical profile name → preferred model name + fallback order + backend hint
2. **Model metadata expansion** — Add `backend` (`whisper.cpp` | `faster-whisper`), `profile_compatibility` list, `source_url`, `license_status`
3. **Profile resolution API** — `resolve_profile(settings, hardware_info)` → `ModelInfo` with auto-fallback

## Hardware Detection (Windows, no admin)

### CPU detection
- `platform.processor()` — human-readable name
- `os.cpu_count()` — logical cores (already used for `n_threads`)

### NVIDIA detection (advisory only)
- **Option A: `ctypes` + `nvml.dll`** — Most reliable, but `nvml.dll` only present with NVIDIA driver install. LoadLibrary may fail on non-NVIDIA systems.
- **Option B: `wmic path win32_VideoController`** — Available on all Windows systems, returns GPU names. Parse for "NVIDIA" / "GeForce" / "RTX". No driver dependency.
- **Option C: `subprocess` + `nvidia-smi`** — Requires CUDA toolkit or driver install. Overkill for advisory detection.

**Decision:** Use Option B (`wmic`) as primary — universally available, no extra dependencies. Optionally try Option A if `nvml.dll` exists for VRAM size. Both are advisory; failure = assume CPU profile.

### No-runtime-network enforcement
- `wmic` is a local WMI query — no network
- `nvml.dll` is local driver component — no network
- No telemetry or hardware fingerprinting

## Don't Hand-roll

- **Don't build a model downloader** — Side-load guidance only, per PRIV-01
- **Don't implement faster-whisper backend** — Phase 3 captures metadata only; backend implementation deferred
- **Don't auto-install CUDA/cuDNN** — D-12 explicitly prohibits this
- **Don't bundle model binaries** — Already prohibited; registry points to side-loaded paths

## Common Pitfalls

1. **Overwriting user preference** — D-03: fallback must not mutate `SettingsStore.model_profile`
2. **Profile name leakage** — Downstream code must use canonical profile names, not raw model names like `base`
3. **NVIDIA default creep** — D-09: `nvidia-dev` must never become shipping default
4. **Checksum paranoia** — D-07: missing checksum is warning, not blocker. Don't force users to compute SHA256.
5. **Registry migration** — Existing `registry.json` from Phase 2 lacks new fields. Must load gracefully (missing keys → defaults).

## Profile Resolution Flow

```
resolve_profile(settings.model_profile, hardware_info):
  1. preferred = settings.model_profile (e.g., "nvidia-dev")
  2. Look up profile definition for "nvidia-dev"
     - preferred_model = "small" (or future NVIDIA-specific slot)
     - backend = "faster-whisper"
     - fallback_profiles = ["cpu-high-accuracy", "cpu-portable"]
  3. Validate preferred_model locally
     - If valid → return ModelInfo with advisory note if hardware mismatch
     - If invalid → try fallback_profiles in order
  4. If no valid model found → return None + error context
  5. NEVER overwrite settings.model_profile
```

## Security Notes

- `wmic` subprocess with fixed arguments is safe — no user input reaches shell
- `nvml.dll` loading via `ctypes.windll` is safe — local system DLL
- Registry JSON is user-writable by design (side-load instructions may edit it)

## Out of Scope (Deferred)

- faster-whisper/CTranslate2 backend implementation
- CUDA/cuDNN redistribution or bundling
- Auto-download of models
- Full settings dialog (Phase 4)
- Benchmark execution (Phase 1 artifact, separate task)

---
*Research complete — sufficient to plan Phase 3*
