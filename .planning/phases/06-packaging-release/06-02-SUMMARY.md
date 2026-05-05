---
phase: 06-packaging-release
plan: 02
subsystem: infra
tags: [licensing, sbom, cyclonedx, notices]

requires:
  - phase: 06-packaging-release
    plan: 01
    provides: portable packaging contract

provides:
  - License notice bundle generator (generate_license_bundle.py)
  - THIRD-PARTY-NOTICES.md covering all runtime deps
  - MODEL-NOTICES.md with model metadata and checksums
  - CycloneDX SBOM command for release building

affects: [06-03, 06-04]

tech-stack:
  added: [cyclonedx-bom]
  patterns: [notice-token-validation, --check-verification, frozenset-required-tokens]

key-files:
  created:
    - scripts/generate_license_bundle.py
    - LICENSES/THIRD-PARTY-NOTICES.md
    - LICENSES/MODEL-NOTICES.md
    - tests/test_license_bundle.py

key-decisions:
  - "Use frozenset for REQUIRED_NOTICE_TOKENS — immutable, hashable, prevents accidental mutation during release"
  - "Include both runtime deps and optional dev-backend deps (faster-whisper, CTranslate2) in notices for transparency"
  - "CUDA/cuDNN redistribution section stays BLOCKED with explicit conditions for future approval"
  - "SBOM command printed as instruction line — user runs cyclonedx_py separately to avoid network/install coupling"

patterns-established:
  - "--check / --write CLI pattern for deterministic, testable notice generation"
  - "Conservative notice posture: all rows marked 'verify before release' until legal review"

requirements-completed: [REL-02]

duration: 10min
completed: 2026-05-05
---

# Phase 6 Plan 02: License Bundle & SBOM Summary

**Conservative release license notices for all 13 required tokens, CycloneDX SBOM instruction, and 12 automated coverage tests — legal gate before public distribution**

## Performance

- **Duration:** 10 min
- **Tasks:** 2
- **Files modified:** 4 (all created)

## Accomplishments
- `scripts/generate_license_bundle.py` with --write/--check CLI, frozenset token validation, and SBOM command
- `LICENSES/THIRD-PARTY-NOTICES.md` — PySide6/Qt, sounddevice/PortAudio, numpy, pywhispercpp/whisper.cpp, pywin32, WebRTC VAD, faster-whisper/CTranslate2, CUDA/cuDNN BLOCKED
- `LICENSES/MODEL-NOTICES.md` — ggml-base.bin and ggml-small.bin with SHA-256, source URL, model-binary exclusion statement
- `tests/test_license_bundle.py` — 12 tests: token coverage, --check passes/fails, --write creates files, script integration

## Task Commits

1. **Task 1: License bundle generator and coverage tests** - `81f6c6a` (test)
2. **Task 2: Write conservative notices** - `433b3e9` (feat)

## Files Created/Modified
- `scripts/generate_license_bundle.py` — 13 required tokens, --write/--check flags, CycloneDX SBOM instruction
- `LICENSES/THIRD-PARTY-NOTICES.md` — Runtime dependency notices with licence posture and redistribution constraints
- `LICENSES/MODEL-NOTICES.md` — Model asset metadata, SHA-256 checksums, side-load guidance, exclusion statement
- `tests/test_license_bundle.py` — Token coverage, check/write validation, script integration tests

## Decisions Made
- Token check is combined (both files together) rather than per-file — a token in either file satisfies the requirement
- Generator uses str.format() template with parameterised model metadata rather than hardcoding SHA values
- SBOM is an instruction line, not an auto-run command — avoids pip install coupling during release

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- frozenset not sliceable in test — fixed by converting to sorted list before slicing
- No other issues

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- License bundle and SBOM support complete
- Ready for 06-03 (release documentation)
- LICENSES/ directory available for build_portable.ps1 to copy into portable zip

---
*Phase: 06-packaging-release*
*Completed: 2026-05-05*
