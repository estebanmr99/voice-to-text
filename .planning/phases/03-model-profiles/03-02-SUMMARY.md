---
phase: 03-model-profiles
plan: 02
subsystem: api
tags: [python, windows, wmic, profile-resolution, startup]
requires:
  - phase: 03-model-profiles
    provides: profile/model registry metadata and canonical profile definitions from 03-01
provides:
  - Windows-safe hardware detector with advisory NVIDIA detection
  - Profile resolver selecting first valid local model without mutating user preference
  - Startup wiring that uses hardware + profile resolution instead of first-valid model scan
affects: [phase-03-plan-03, phase-04-gui-tray-polish, startup-flow]
tech-stack:
  added: []
  patterns: [fixed-argument subprocess with timeout, non-throwing resolver result object]
key-files:
  created: [src/hardware_detector.py, src/profile_resolver.py, tests/test_hardware_detector.py, tests/test_profile_resolver.py, .planning/phases/03-model-profiles/03-02-SUMMARY.md]
  modified: [src/main.py]
key-decisions:
  - "Use fixed-arg WMIC call with 5s timeout for advisory NVIDIA detection, with graceful fallback on failure."
  - "Resolver always returns structured result and never writes SettingsStore.model_profile during fallback."
patterns-established:
  - "Profile resolution validates models through ModelManager before startup transcriber activation."
  - "NVIDIA selection emits advisory guidance instead of hard failure when dependencies/models are unavailable."
requirements-completed: [PROF-01, PROF-02, PROF-03, TEST-02]
duration: 21min
completed: 2026-05-05
---

# Phase 3 Plan 02: Hardware Detection and Profile Resolution Summary

**Startup now resolves canonical profile preference to the first valid local model using hardware advisories, without overwriting user settings.**

## Performance

- **Duration:** 21 min
- **Started:** 2026-05-05T14:10:00Z
- **Completed:** 2026-05-05T14:31:00Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- Implemented `detect_hardware()` with CPU detection and advisory NVIDIA discovery via fixed WMIC command + timeout.
- Implemented `resolve_profile()` fallback chain honoring user preference immutability and checksum-based model validation.
- Rewired `main.py` startup to hardware-detect → resolve profile → start transcriber or show missing-model guidance + advisories.

## Task Commits

1. **Task 1: Implement hardware_detector.py with Windows-safe detection** - `6caf798` (feat)
2. **Task 2: Implement profile_resolver.py with fallback logic** - `d76ff74` (feat)
3. **Task 3: Wire profile resolution into main.py startup** - `45ba952` (feat)

## Files Created/Modified
- `src/hardware_detector.py` - Added `HardwareInfo` and non-throwing local hardware detection.
- `tests/test_hardware_detector.py` - Added mocked WMIC/NVIDIA detection tests including timeout/failure cases.
- `src/profile_resolver.py` - Added `ProfileResolutionResult` and deterministic profile/model fallback resolution.
- `tests/test_profile_resolver.py` - Added resolver tests for valid path, fallback path, unknown profile, checksum mismatch, and NVIDIA advisories.
- `src/main.py` - Replaced `get_default_model()` startup block with profile resolution flow and richer diagnostics.

## Decisions Made
- Preserved strict no-runtime-network boundary by using local-only WMIC/NVML checks and no dependency installation behavior.
- Chose structured resolver return object instead of exceptions to keep startup robust and diagnosable.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 3 plan 03 can build on this by integrating profile switching controls and richer UI feedback.
- Startup path now carries enough profile/fallback context for tray/status presentation.

## Self-Check: PASSED

- FOUND: `.planning/phases/03-model-profiles/03-02-SUMMARY.md`
- FOUND commit: `6caf798`
- FOUND commit: `d76ff74`
- FOUND commit: `45ba952`

---
*Phase: 03-model-profiles*
*Completed: 2026-05-05*
