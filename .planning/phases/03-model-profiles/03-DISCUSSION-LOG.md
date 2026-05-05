# Phase 3: Model Profiles - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-05
**Phase:** 3-Model Profiles
**Areas discussed:** Profile selection, Registry scope, NVIDIA boundary

---

## Profile Selection

| Question | Option | Description | Selected |
|----------|--------|-------------|----------|
| Default startup behavior when user has no valid profile/model? | Auto choose valid | Pick first valid local profile by hardware priority; no download. | yes |
| Default startup behavior when user has no valid profile/model? | Keep setting fail | Respect selected `model_profile`; show missing/corrupt guidance if invalid. | |
| Default startup behavior when user has no valid profile/model? | Ask on launch | Show chooser when no valid profile; bigger UI dependency before Phase 4. | |
| If hardware recommends `nvidia-dev` but only CPU model exists? | Use CPU now | Prefer valid local model over ideal hardware match; log recommendation. | yes |
| If hardware recommends `nvidia-dev` but only CPU model exists? | Fail for NVIDIA | Require exact recommended profile; user must side-load GPU model first. | |
| If hardware recommends `nvidia-dev` but only CPU model exists? | Prompt chooser | Ask user; creates Phase 4 UI dependency. | |
| Should profile resolver save auto-selected fallback to settings? | Do not overwrite | Runtime fallback temporary; user preference stays intact. | yes |
| Should profile resolver save auto-selected fallback to settings? | Save fallback | Persist working profile; avoids repeated fallback but may hide preferred GPU intent. | |
| Should profile resolver save auto-selected fallback to settings? | Save only if none | Persist only when setting missing/unknown; preserve explicit user choice. | |
| How should resolver order CPU profiles on common laptop/desktop CPU? | Portable first | Start with `cpu-portable`/base for responsiveness; user can choose high accuracy. | yes |
| How should resolver order CPU profiles on common laptop/desktop CPU? | Accuracy first | Prefer `cpu-high-accuracy`/small-or-larger if valid; slower default. | |
| How should resolver order CPU profiles on common laptop/desktop CPU? | Hardware tiered | Desktop/high RAM gets accuracy; laptops get portable. More heuristics. | |

**User's choice:** Auto-select valid local profile, use CPU fallback when NVIDIA assets are missing, do not overwrite user settings, and prefer CPU portable first.
**Notes:** User chose pragmatic runtime behavior over strict hardware matching or early UI prompts.

---

## Registry Scope

| Question | Option | Description | Selected |
|----------|--------|-------------|----------|
| Canonical v1 profile names? | Three roadmap names | `cpu-portable`, `cpu-high-accuracy`, `nvidia-dev`; map to model/backend entries. | yes |
| Canonical v1 profile names? | Model names only | Use `base`, `small`, etc.; simpler but conflicts with SettingsStore default. | |
| Canonical v1 profile names? | Profiles plus models | Expose both profile and model separately; more flexible, bigger UI/settings surface. | |
| Which model slots should seed registry for Phase 3 v1? | Base small only | Match side-loaded assets and current code; add metadata/profile mapping now. | yes |
| Which model slots should seed registry for Phase 3 v1? | Benchmark matrix | Seed tiny/base/small/medium/large-v3-turbo/faster-whisper rows; many missing slots. | |
| Which model slots should seed registry for Phase 3 v1? | Only installed | Create registry from local files found; less guidance for side-load. | |
| How strict should checksum metadata be before model can run? | Warn if absent | Allow local side-loaded model without checksum; verify when checksum exists. | yes |
| How strict should checksum metadata be before model can run? | Require checksum | Best integrity but blocks current base/small unless known hashes recorded. | |
| How strict should checksum metadata be before model can run? | Skip checksum | Fastest; weakens TEST-02 corrupt model requirement. | |
| License/source metadata strictness before selecting profile? | Required metadata | Source URL/license/status/size required in registry; license can remain verify-before-release. | yes |
| License/source metadata strictness before selecting profile? | Best effort | Run if path exists even if metadata incomplete; less planning safety. | |
| License/source metadata strictness before selecting profile? | Approved only | Only run models with approved license; blocks current candidate/verify posture. | |

**User's choice:** Use roadmap profile names, seed base/small only, warn when checksum absent, require license/source/size/backend/profile metadata.
**Notes:** User chose small v1 scope aligned with existing code and local assets.

---

## NVIDIA Boundary

| Question | Option | Description | Selected |
|----------|--------|-------------|----------|
| How visible should `nvidia-dev` be in Phase 3? | Visible dev only | Show as optional dev/benchmark profile, never shipping default. | yes |
| How visible should `nvidia-dev` be in Phase 3? | Hidden until ready | Keep out of UI/settings until faster-whisper implementation proven. | |
| How visible should `nvidia-dev` be in Phase 3? | Equal profile | Treat like normal selectable profile if hardware present; risk licensing confusion. | |
| Should Phase 3 implement faster-whisper backend or only profile metadata? | Metadata only | Record dev profile and dependency boundary; defer backend implementation until benchmark/research plan. | yes |
| Should Phase 3 implement faster-whisper backend or only profile metadata? | Optional backend | Add faster-whisper adapter now behind optional dependency; more risk/scope. | |
| Should Phase 3 implement faster-whisper backend or only profile metadata? | Stub adapter | Create interface stub returning local error; may be dead code. | |
| What should `nvidia-dev` do when selected but dependency/model missing? | Local error + fallback option | No download; explain optional setup and continue CPU if auto-resolution path. | yes |
| What should `nvidia-dev` do when selected but dependency/model missing? | Hard local error | Fail selected profile until user installs deps/models; stricter but rougher. | |
| What should `nvidia-dev` do when selected but dependency/model missing? | Hide profile | Do not expose until dependency/model present; less guidance. | |
| Hardware detection target for NVIDIA dev profile? | Detect advisory | Detect NVIDIA/VRAM if possible, but advisory only; never auto-install or require. | yes |
| Hardware detection target for NVIDIA dev profile? | Require exact RTX | Only recommend on known RTX hardware; more accurate, more detection work. | |
| Hardware detection target for NVIDIA dev profile? | Manual only | Do not detect GPU; user opts into `nvidia-dev` manually. | |

**User's choice:** Make NVIDIA dev visible but bounded, metadata-only in Phase 3, with local errors and advisory hardware detection.
**Notes:** CUDA/cuDNN redistribution remains blocked; faster-whisper backend implementation is not part of Phase 3 context.

---

## the agent's Discretion

- Exact resolver and hardware detector module/function names.
- Exact JSON registry schema shape, as long as required metadata and profile mappings are represented.
- Exact local error class/category naming, as long as missing/corrupt/dependency/backend failures are local-only and testable.

## Deferred Ideas

- Real `faster-whisper`/CTranslate2 backend implementation.
- Shipping NVIDIA runtime support or CUDA/cuDNN redistribution.
- Full settings/profile chooser UI polish for Phase 4.
