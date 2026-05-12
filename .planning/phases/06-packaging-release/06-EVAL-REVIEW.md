# EVAL-REVIEW — Phase 06: packaging-release (Re-Audit)

**Audit Date:** 2026-05-11
**AI-SPEC Present:** No (no AI-SPEC.md exists anywhere in the project)
**Overall Score:** 88/100
**Verdict:** PRODUCTION READY — deploy with monitoring

---

## Overview

Phase 06 is the packaging-and-release phase for an offline Whisper.cpp-based Spanglish dictation app. This is a **re-audit** following the resolution of all 3 BLOCKER gaps identified in the original audit (2026-05-11, scored 46/100, "SIGNIFICANT GAPS — DO NOT DEPLOY").

**Quick task 260511-q9k closed all 3 blockers:** transcription quality gate, model artifact integrity cross-verification, and automated dictation end-to-end smoke test. Each has been verified on disk with passing tests.

**Phase 06 also delivered its original packaging goals:** PyInstaller portable zip, release artifact policies, SBOM + license notices, release documentation, and GitHub Actions release automation. All packaging infrastructure remains solid.

---

## Dimension Coverage

Evaluated against general AI eval best practices (from `ai-evals.md`). Re-auditing the same 7 dimensions from the original review.

| # | Dimension | Status (Δ) | Measurement | Finding |
|---|-----------|------------|-------------|---------|
| 1 | **Transcription Quality Validation Gate** | **COVERED** 🟢 (was MISSING 🔴) | Code-based (WER) | **RESOLVED.** `scripts/eval_transcription.py` computes per-clip and aggregate WER via `jiwer`. `tests/test_transcription_benchmark.py` enforces thresholds (base ≤30%, small ≤20% WER) with `@pytest.mark.skipif` guards. `--post-process` flag applies glossary normalization. 10 eval clips recorded with ground-truth transcripts. `prepare_release.ps1` step 8 runs optional eval. |
| 2 | **Model Artifact Integrity Verification** | **COVERED** 🟢 (was PARTIAL 🟡) | Code-based | **RESOLVED.** `models/model_checksums.json` is the single source of truth with rich schema (sha256, size_mb, url). All 3 prior hardcoded locations now read from JSON: `generate_license_bundle.py:54-58`, `test_release_docs.py:164-168`, `test_license_bundle.py:131-132`. `tests/test_model_integrity.py` (4 tests) cross-verifies JSON ↔ license bundle ↔ sideloading docs. `prepare_release.ps1` step 7 verifies local file hashes against checksums. |
| 3 | **Privacy/Offline Safety Enforcement** | **COVERED** 🟢 (unchanged) | Code-based | PrivacyGuard patches socket/urllib/ssl/QtNetwork at runtime. `smoke_offline.ps1` runs privacy regression tests. GitHub Actions workflow includes smoke test step. 100+ privacy tests pass. Enforcement verified at startup via self-test. |
| 4 | **SBOM & License Compliance** | **COVERED** 🟢 (unchanged) | Code-based | `generate_license_bundle.py` covers all 13 required tokens. `--check` validates token presence (exit 0/1). CycloneDX SBOM command scripted. CUDA/cuDNN redistribution explicitly BLOCKED. 12 license tests pass. |
| 5 | **Release Artifact Structural Verification** | **COVERED** 🟢 (unchanged) | Code-based | `verify_release_artifacts.py` checks: required files (portable zip, SBOM, SHA256SUMS.txt), blocked patterns (models, *.bin, *.gguf, CUDA/cuDNN DLLs), notice files. Exit code enforcement. 31 packaging policy tests pass. |
| 6 | **CI/CD Automation & Release Pipeline** | **COVERED** 🟢 (unchanged) | Code-based | GitHub Actions workflow triggered on `v*` tags. `prepare_release.ps1` is now 8-step: pytest → license → SBOM → build → checksums → verify → **model integrity (NEW)** → **eval (optional, NEW)**. No model downloads or CUDA/cuDNN references in CI. 19 workflow tests pass. |
| 7 | **Manual UX / Functional Verification** | **COVERED** 🟢 (was PARTIAL 🟡) | Code-based + Human | **RESOLVED.** `tests/test_dictation_smoke.py` (107 lines) runs real `Transcriber` with real model and eval WAV. Asserts str return and non-empty output with graceful skip guards. MANUAL-VERIFICATION.md (14-step human testing guide) still present. Both automated and manual coverage now exist. |

**Coverage Score:** 7/7 (100%)

---

## Infrastructure Audit

| Component | Status (Δ) | Score | Finding |
|-----------|------------|-------|---------|
| Eval tooling (jiwer WER) | **Installed** 🟢 (was Not found 🔴) | 1.0 | `jiwer>=3.0` added to `[project.optional-dependencies] dev` in `pyproject.toml:41`. Used by `eval_transcription.py` for WER computation. Community-standard ASR eval tool. |
| Reference dataset | **Present** 🟢 (was Missing 🔴) | 1.0 | `data/eval/transcripts.jsonl` — 10 ground-truth phrases covering en/es/spanglish/tech. 10 WAV files on disk (96 KB each, real recorded audio). `scripts/record_eval_clips.py` for expansion. `data/eval/README.md` documents layout and usage. WAVs gitignored, only JSONL + README in version control. |
| CI/CD integration | **Present** 🟢 | 1.0 | `.github/workflows/release.yml` runs full 8-step pipeline: test → license → SBOM → build → checksums → verify → model integrity → eval (optional). All 394+ tests run. Privacy smoke test included. No model/CUDA/cuDNN in CI. PR CI still missing (workflow is tag-only — see warnings). |
| Online guardrails | **Partial** 🟡 | 0.5 | PrivacyGuard implemented and enforced at `main.py` line 1 — real monkey-patching of socket/urllib/ssl/QtNetwork. Self-test verified. No quality guardrails (transcription confidence threshold enforcement, hallucination check) — partially mitigated by pre-deployment WER benchmark gate. |
| Tracing | **Not configured** 🔴 | 0.0 | No tracing, observability, or monitoring tooling. By design: the app is zero-telemetry, fully offline. `src/diagnostics.py` exists (redacted event logging) but is not wired into any evaluation feedback loop. No documented monitoring plan for users/admins. |

**Infrastructure Score:** 3.5/5 = 70%

---

## Scoring Summary

| Component | Raw Score | Weighted |
|-----------|-----------|----------|
| Dimension Coverage (7 dims) | 100% (7/7) | × 0.6 = 60.0 |
| Infrastructure Audit (5 comps) | 70% (3.5/5) | × 0.4 = 28.0 |
| **Overall** | | **88.0 / 100** |

### Improvement from Original Audit

| Metric | Original (2026-05-11) | Current (2026-05-11) | Δ |
|--------|----------------------|----------------------|---|
| Coverage Score | 57% (4/7) | 100% (7/7) | **+43pp** |
| Infrastructure Score | 30% (1.5/5) | 70% (3.5/5) | **+40pp** |
| Overall Score | **46/100** | **88/100** | **+42pp** |
| Verdict | SIGNIFICANT GAPS — DO NOT DEPLOY | **PRODUCTION READY** | — |
| Blocker Gaps | 3 | **0** | **-3** |

### Verdict

```
88/100 → PRODUCTION READY — deploy with monitoring
```

---

## BLOCKER Gap Resolution (All 3 Resolved)

### 1. [RESOLVED] No Transcription Quality Validation Gate — Dimension 1

**Original finding:** No reference audio dataset, no WER script, no accuracy threshold gate. 394 unit tests all mock the transcriber.

**Resolution evidence:**
- `scripts/eval_transcription.py` (350 lines) — full WER benchmark CLI with `compute_wer_for_model()` export for test reuse. Uses `jiwer` for WER computation. Supports `--model-path`, `--data-dir`, `--threshold`, `--n-threads`, `--post-process` flags. Exit codes: 0 (pass), 1 (threshold exceeded), 2 (no clips).
- `tests/test_transcription_benchmark.py` (73 lines) — base model threshold 30% WER, small model threshold 20% WER. Calibrated to measured performance on mixed EN/ES dataset. `@pytest.mark.skipif` guards for graceful absence.
- `data/eval/` — 10 eval clips recorded (01.wav–10.wav, 96 KB each, real audio), `transcripts.jsonl` with 10 ground-truth phrases, `README.md` documenting layout.
- `data/eval/transcripts.jsonl` covers: English greeting, Spanish greeting, Spanglish tech ("merge the PR"), English tech ("API endpoint returns JSON"), Spanish tech ("hacer el deploy"), mixed Spanglish ("revísame el PR"), tech commands and CI vocabulary.
- `scripts/record_eval_clips.py` (169 lines) — interactive recording tool with `--device` arg and summary report.
- `prepare_release.ps1` step 8 runs eval_transcription.py as optional gate.
- `jiwer>=3.0` in `pyproject.toml` dev deps.

### 2. [RESOLVED] Model Artifact Integrity Not Automatically Verified — Dimension 2

**Original finding:** SHA-256 hashes hardcoded in 3 places with no cross-verification. Release pipeline never verifies model file integrity against documented hashes.

**Resolution evidence:**
- `models/model_checksums.json` — single source of truth with rich schema (sha256, size_mb, url) for `ggml-base.bin` and `ggml-small.bin`.
- `scripts/generate_license_bundle.py:54-58` reads from JSON at module level.
- `tests/test_release_docs.py:164,168` reads from JSON as properties.
- `tests/test_license_bundle.py:131-132` reads from JSON.
- `tests/test_model_integrity.py` (53 lines, 4 tests) — cross-verifies JSON exists, expected models present with 64-char hashes, matches `generate_license_bundle.MODEL_METADATA`, matches `docs/MODEL-SIDELOADING.md`. CI-compatible (no model binaries required). All 4 pass.
- `prepare_release.ps1` step 7: runs `test_model_integrity.py` + local `Get-FileHash` verification against checksums.
- `.github/workflows/release.yml` includes "Verify model integrity" step.

### 3. [RESOLVED] No Automated Dictation End-to-End Test — Dimension 7

**Original finding:** Every "dictation" test uses mocked hardware. Manual verification guide is thorough but entirely human-dependent.

**Resolution evidence:**
- `tests/test_dictation_smoke.py` (107 lines) — real-model smoke test. Imports real `Transcriber`, `ModelManager`, `ModelInfo`. Loads eval WAV from disk, calls `transcriber.start()`, `transcriber.transcribe()`, asserts `isinstance(text, str)` and `len(text) > 0`. `finally` block ensures `transcriber.stop()`.
- Double skip guards: `@pytest.mark.skipif(not _has_model)` + `@pytest.mark.skipif(not _has_eval_wav)`. Verified: 3 tests skip correctly when no model/WAV present.
- Not an accuracy test — validates model loads, worker process starts, audio flows, text returns. Sufficient for regression detection.

---

## Critical Gaps

**None.** All 3 original BLOCKER gaps are resolved. No new BLOCKER gaps identified.

---

## Remaining Warnings (Not Blockers)

### WARNING 1: No PR CI Workflow

**Status:** MISSING — no `.github/workflows/ci.yml` exists. The only CI workflow (`release.yml`) is tag-triggered only.

**Impact:** Regressions in eval thresholds, model integrity, or packaging policy are only caught at release time, not during PR review. A PR that breaks the WER benchmark or model integrity tests would pass review and be merged without detection.

**Remediation (estimated 1 hour):**
- Create `.github/workflows/ci.yml` triggered on `push` and `pull_request` to `main`
- Run: `python -m pytest tests/test_model_integrity.py tests/test_release_docs.py -q`
- Also run the full test suite: `python -m pytest tests/ -q`
- Do NOT include eval_transcription.py or test_transcription_benchmark.py in CI (requires local models and WAVs)
- Would catch regressions in model checksum cross-verification, doc integrity, and packaging policy on every PR

### WARNING 2: No Local Monitoring Strategy Documented

**Status:** MISSING — `src/diagnostics.py` exists (100 lines, redacted event logger) but is not wired into any evaluation feedback loop. No documented plan for users/admins to monitor quality signals.

**Impact:** Users have no way to detect transcription quality degradation over time without running the benchmark themselves. Degradation from whisper.cpp version bumps, quantization changes, or OS updates goes unnoticed.

**Remediation (estimated 2 hours):**
- Add a `docs/MONITORING.md` documenting how to use diagnostics logs for quality tracking
- Consider logging WER benchmark results to diagnostics
- Add a periodic check that alerts users if aggregate WER exceeds threshold

### WARNING 3: No Online Quality Guardrails

**Status:** PARTIAL — PrivacyGuard is robust but no transcription confidence threshold or hallucination check exists at runtime.

**Impact:** If whisper.cpp returns low-confidence or hallucinated output, the app pastes it without warning the user. Pre-deployment WER benchmarks catch regression but cannot catch per-utterance quality issues.

**Remediation (estimated 3-4 hours):**
- Investigate whisper.cpp confidence scores (whisper.cpp has `whisper_full_get_probability_from_token_data`)
- Add optional confidence threshold in `transcriber.py` that rejects below-threshold output
- Surface low-confidence warnings in status panel or confirmation dialog

### WARNING 4: Eval Dataset Is Minimum Size

**Status:** PARTIAL — 10 eval clips meets the "10-20" minimum from best practices but is at the low end.

**Impact:** Limited coverage of edge cases: different accents, microphone qualities, background noise levels, domain vocabulary variations.

**Remediation (estimated 30 min periodic):**
- Expand to 20+ clips as real failure modes are discovered in production
- The recording tool (`scripts/record_eval_clips.py`) is ready for this

---

## Remediation Plan

### Must fix before production:
**None.** All BLOCKER gaps are resolved. The system can ship.

### Should fix soon (WARNING):
1. **Add PR CI workflow** — `.github/workflows/ci.yml` for pre-merge regression detection
2. **Document monitoring strategy** — `docs/MONITORING.md` for local quality tracking via diagnostics
3. **Add quality guardrails** — confidence threshold enforcement in transcriber
4. **Expand eval dataset** — grow from 10 to 20+ clips covering more edge cases

### Nice to have:
- Rename `data/eval/` WAV files to match transcript IDs exactly (already done: `01.wav`–`10.wav`)
- Consider CI-compatible eval subset (synthetic audio or very small model) for PR CI

---

## Files Found (New Eval Infrastructure)

### Created by quick task 260511-q9k:

| File | Purpose | Lines | Status |
|------|---------|-------|--------|
| `data/eval/README.md` | Eval dataset documentation | 58 | Verified on disk |
| `data/eval/transcripts.jsonl` | 10 ground-truth transcription phrases | 10 lines | Verified on disk |
| `data/eval/01.wav`–`10.wav` | Recorded audio clips for WER benchmarks | ~96 KB each | Verified on disk (real audio) |
| `scripts/record_eval_clips.py` | Interactive recording tool for eval dataset expansion | 169 | Verified on disk |
| `scripts/eval_transcription.py` | WER benchmark CLI with `compute_wer_for_model()` | 350 | Verified on disk |
| `tests/test_dictation_smoke.py` | Real-model end-to-end smoke test | 107 | Verified on disk |
| `tests/test_transcription_benchmark.py` | WER threshold regression tests (base: 30%, small: 20%) | 73 | Verified on disk |
| `tests/test_model_integrity.py` | Cross-verification of model checksums across JSON, license, docs | 53 | Verified on disk |

### Modified by quick task 260511-q9k:

| File | Change | Status |
|------|--------|--------|
| `models/model_checksums.json` | Created as single source of truth for SHA-256 | Verified on disk |
| `pyproject.toml` | Added `jiwer>=3.0` to dev deps | Verified |
| `.gitignore` | Updated to allow `model_checksums.json` in git, ignore eval WAVs | Verified |
| `scripts/generate_license_bundle.py` | Now reads checksums from `model_checksums.json` | Verified (line 54-58) |
| `tests/test_release_docs.py` | Model hash properties now read from JSON | Verified (line 164, 168) |
| `tests/test_license_bundle.py` | Model hashes now read from JSON | Verified (line 131-132) |
| `scripts/prepare_release.ps1` | 8-step pipeline: added step 7 (model integrity) + step 8 (optional eval) | Verified |
| `.github/workflows/release.yml` | Added "Verify model integrity" step | Verified |

### Remaining gaps (unchanged from original):

| Missing | Impact |
|---------|--------|
| `.github/workflows/ci.yml` | No PR CI (tag-release only) |
| `docs/MONITORING.md` | No documented monitoring strategy |
| Online confidence guardrails | Runtime quality enforcement absent |

---

## Verification Commit Trail

All 3 q9k commits verified in git log:

| Hash | Message | Evidence |
|------|---------|----------|
| `9ef31c8` | feat(260511-q9k): create eval dataset, checksum source of truth, consolidate deps | `data/eval/`, `models/model_checksums.json`, modified pyproject.toml/.gitignore |
| `0d38087` | feat(260511-q9k): create WER benchmark, dictation smoke test, model integrity tests | `scripts/eval_transcription.py`, 3 new test files |
| `d003e3e` | feat(260511-q9k): integrate eval and model integrity checks into release pipeline | `scripts/prepare_release.ps1` (8 steps), `.github/workflows/release.yml` |

---

## Key Data Flow Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `models/model_checksums.json` | `scripts/generate_license_bundle.py` | `json.loads(...read_text())` line 54-58 | ✓ WIRED |
| `models/model_checksums.json` | `tests/test_release_docs.py` | `json.loads(...read_text())` line 164 | ✓ WIRED |
| `models/model_checksums.json` | `tests/test_license_bundle.py` | `json.loads(...read_text())` line 131-132 | ✓ WIRED |
| `models/model_checksums.json` | `docs/MODEL-SIDELOADING.md` | `test_model_integrity.py` grep assertion line 52-53 | ✓ WIRED |
| `data/eval/transcripts.jsonl` | `scripts/eval_transcription.py` | `json.loads()` for each line, line 191-198 | ✓ WIRED |
| `data/eval/*.wav` | `scripts/eval_transcription.py` | `_load_wav()` → `transcriber.transcribe()` | ✓ FLOWING |
| `scripts/eval_transcription.py` | `tests/test_transcription_benchmark.py` | `from eval_transcription import compute_wer_for_model` | ✓ FLOWING |
| `scripts/eval_transcription.py` | `scripts/prepare_release.ps1` | Step 8 calls `eval_transcription.py` | ✓ WIRED |
| `tests/test_model_integrity.py` | `scripts/prepare_release.ps1` | Step 7 runs `pytest test_model_integrity.py` | ✓ WIRED |
| `tests/test_model_integrity.py` | `.github/workflows/release.yml` | "Verify model integrity" step | ✓ WIRED |

---

## Files Found (Phase 06 — Eval-Related, Complete Inventory)

### Test files (now 93 total):
| File | Tests | Lines | Purpose |
|------|-------|-------|---------|
| `tests/test_release_packaging.py` | 22 | 170 | Blocked artifact policy, spec validation, build/smoke script audit |
| `tests/test_license_bundle.py` | 12 | 165 | Token coverage, --check/--write behavior, reads from model_checksums.json |
| `tests/test_release_docs.py` | 20 | 211 | README, LICENSE, RELEASE, SIDELOADING, PRIVACY — reads checksums from JSON |
| `tests/test_release_workflow.py` | 19 + 13 subclass | 227 | Verifier, workflow content, checklist hygiene, prepare_release script |
| `tests/test_model_integrity.py` | **4 (NEW)** | **53** | **Cross-verifies checksums across JSON, license bundle, and docs** |
| `tests/test_dictation_smoke.py` | **1 (NEW)** | **107** | **Real-transcriber end-to-end smoke test with skip guards** |
| `tests/test_transcription_benchmark.py` | **2 (NEW)** | **73** | **WER threshold regression tests (base: 30%, small: 20%) with skip guards** |

### Scripts:
| File | Purpose |
|------|---------|
| `scripts/build_portable.ps1` | Staged artifact → portable zip with blocked-pattern enforcement |
| `scripts/smoke_offline.ps1` | Runs privacy + packaging regression tests |
| `scripts/generate_license_bundle.py` | License notice generation + --check/--write CLI (reads model_checksums.json) |
| `scripts/verify_release_artifacts.py` | Release directory structural verification |
| `scripts/prepare_release.ps1` | **8-step release pipeline (was 6)** with model integrity + optional eval |
| `scripts/eval_transcription.py` | **WER benchmark CLI (NEW)** |
| `scripts/record_eval_clips.py` | **Eval dataset recording tool (NEW)** |

### Infrastructure:
| File | Purpose |
|------|---------|
| `.github/workflows/release.yml` | Tag-triggered GitHub Actions release with model integrity step |
| `packaging/spanglish-dictation.spec` | PyInstaller onedir contract |
| `LICENSES/THIRD-PARTY-NOTICES.md` | 13-token runtime dependency notices |
| `LICENSES/MODEL-NOTICES.md` | Model metadata + checksums |
| `models/model_checksums.json` | **Single source of truth for SHA-256 (NEW)** |
| `docs/MANUAL-VERIFICATION.md` | 14-step human verification guide |
| `docs/GITHUB-RELEASE-CHECKLIST.md` | Pre-publish checklist |
| `data/eval/README.md` | **Eval dataset docs (NEW)** |
| `data/eval/transcripts.jsonl` | **10 ground-truth transcription phrases (NEW)** |
| `data/eval/01.wav–10.wav` | **Recorded eval audio clips (NEW, gitignored)** |

---
