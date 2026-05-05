# Phase 3: Model Profiles - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 3 delivers local model/profile management for offline ASR. It must resolve CPU portable, CPU high-accuracy, and NVIDIA dev profiles from local model files and detected hardware, without runtime downloads, cloud fallback, telemetry, or model binaries in git.

</domain>

<decisions>
## Implementation Decisions

### Profile Selection
- **D-01:** On startup, auto-select the first valid local profile instead of failing when the preferred or recommended profile is unavailable.
- **D-02:** If hardware recommends `nvidia-dev` but only a CPU model is valid locally, use the CPU profile immediately and record the NVIDIA recommendation as advisory context.
- **D-03:** Runtime fallback must not overwrite `SettingsStore.model_profile`; user preference remains intact even when a different valid profile is used temporarily.
- **D-04:** CPU profile resolution should prefer `cpu-portable` first for responsiveness. Users can explicitly choose `cpu-high-accuracy` later.

### Registry Scope
- **D-05:** Canonical v1 profile names are `cpu-portable`, `cpu-high-accuracy`, and `nvidia-dev`. These names map to backend/model entries; downstream code should not use raw model names like `base` as profile names.
- **D-06:** Phase 3 should seed only the existing v1 model slots: `base` and `small`. Do not seed the full benchmark matrix yet.
- **D-07:** Missing checksum metadata is a warning, not a blocker. If `checksum_sha256` is present, checksum validation must be enforced and mismatch must fail closed.
- **D-08:** Registry entries must include source URL, license/status, size, backend compatibility, and profile compatibility before a profile can select them. License/status may remain `candidate` or `verify before release`; full legal approval is not required for local dev use.

### NVIDIA Boundary
- **D-09:** `nvidia-dev` should be visible as an optional dev/benchmark profile only. It must not become the shipping default in Phase 3.
- **D-10:** Phase 3 should capture NVIDIA profile metadata and dependency boundaries only. Do not implement a `faster-whisper`/CTranslate2 backend in this phase.
- **D-11:** If `nvidia-dev` is selected but dependency or model assets are missing, return a local error with optional setup guidance and offer CPU fallback behavior in auto-resolution paths. Do not download anything.
- **D-12:** Hardware detection for NVIDIA is advisory only. Detect NVIDIA/VRAM where feasible, but never auto-install dependencies, require exact RTX hardware, or fetch CUDA/cuDNN/model assets.

### the agent's Discretion
- Planner may choose exact module/function names for profile resolver and hardware detector, as long as existing `ModelManager`, `SettingsStore`, and `Transcriber` seams are extended rather than replaced.
- Researcher should investigate Windows-safe local hardware detection options, but must preserve advisory-only behavior and no-runtime-network constraints.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project State and Requirements
- `.planning/PROJECT.md` — Defines product boundary, core value, active requirements, and hard offline/privacy constraints.
- `.planning/REQUIREMENTS.md` — Defines `PROF-01`, `PROF-02`, `PROF-03`, and `TEST-02`; confirms profile scope and missing/corrupt model behavior.
- `.planning/ROADMAP.md` — Defines Phase 3 goal, success criteria, and planned model profile work.
- `.planning/STATE.md` — Current project status, Phase 2 completion state, local setup notes, and side-loaded model context.

### Architecture and Interface Contracts
- `.planning/architecture/ARCHITECTURE.md` — Locks modular monolith architecture, `ModelManager` responsibility, worker isolation, no runtime downloads, and CUDA/cuDNN release constraint.
- `.planning/architecture/INTERFACES.md` — Defines `ModelManager` profile operations: `list_profiles()`, `resolve_profile(settings, hardware_info)`, `validate_model(local_model_ref)`, and `describe_missing_model(local_model_ref)`.
- `.planning/architecture/LICENSE-MATRIX.md` — Defines conservative dependency/model license posture; CUDA/cuDNN redistribution remains blocked.

### Benchmark and Failure Contracts
- `.planning/benchmarks/ASR-VAD-BENCHMARK.md` — Candidate ASR matrix, profile buckets, local benchmark requirements, and default selection gates.
- `.planning/benchmarks/MISSING-MODEL-OFFLINE.md` — Required local-only missing/corrupt model failure contract.

### Prior Implementation Summary
- `.planning/phases/02-mvp-offline-dictation/02-03-SUMMARY.md` — Existing `ModelManager`, JSON registry, `Transcriber`, worker process, and established extension seams for Phase 3.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/model_manager.py` — Existing `ModelInfo` dataclass, JSON registry persistence, path validation, optional SHA256 validation, and side-load guidance.
- `src/transcriber.py` — Existing worker lifecycle accepts a `ModelInfo`; can restart worker when selected model changes.
- `src/transcriber_worker.py` — Existing CPU whisper.cpp worker via `pywhispercpp`; should remain shipping CPU path.
- `src/settings_store.py` — Existing `model_profile` setting defaults to `cpu-portable`, but current registry model slots are named `base` and `small`; Phase 3 must reconcile this mismatch.
- `src/main.py` — Startup currently uses `model_manager.get_default_model()` and starts `Transcriber`; Phase 3 profile resolver should connect here.
- `tests/test_model_manager.py` — Existing registry, validation, checksum, missing-model tests; extend for profile resolution and metadata strictness.

### Established Patterns
- Local JSON registry seeded on first `ModelManager` use.
- Missing models return local guidance strings with manual URLs but no fetch logic.
- Checksums are optional today; Phase 3 should preserve optional absence but enforce present checksums.
- Worker process receives local model path only; no URL, downloader, or network-aware resolver belongs in runtime path.
- Tests mock heavy dependencies and avoid loading real model binaries.

### Integration Points
- `ModelManager` should own profile registry and profile resolution.
- `SettingsStore.model_profile` should store canonical profile name, not raw model slot name.
- `main.py` startup should ask `ModelManager` for resolved active profile/model rather than first valid model.
- `Transcriber.start(model_info)` remains profile-agnostic and should receive selected local model metadata.
- Diagnostics should log profile/model identifiers and error categories only, not audio or transcript contents.

</code_context>

<specifics>
## Specific Ideas

- User explicitly chose practical local fallback over strict hardware matching.
- User wants `nvidia-dev` visible enough for RTX workstation development, but bounded as dev/benchmark metadata until backend and licensing work mature.
- Current local side-loaded models are `ggml-base.bin` and `ggml-small.bin`; Phase 3 should build on those rather than expanding registry slots prematurely.

</specifics>

<deferred>
## Deferred Ideas

- Implementing a real `faster-whisper`/CTranslate2 backend is deferred beyond Phase 3 context unless future planning explicitly scopes it.
- Shipping NVIDIA runtime support or redistributing CUDA/cuDNN remains deferred until explicit license approval.
- Full UI profile chooser/settings polish belongs to Phase 4; Phase 3 may expose enough data/hooks for it.

</deferred>

---

*Phase: 3-Model Profiles*
*Context gathered: 2026-05-05*
