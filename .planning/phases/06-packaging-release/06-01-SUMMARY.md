---
phase: 06-packaging-release
plan: 01
subsystem: infra
tags: [pyinstaller, packaging, smoketest, release-policy]

requires:
  - phase: 05-spanglish-glossary
    provides: glossary_store module
  - phase: 02-mvp-offline-dictation
    provides: privacy_guard, full dictation loop

provides:
  - PyInstaller onedir packaging contract (spanglish-dictation.spec)
  - Blocked-artifact release policy (no models, CUDA/cuDNN in default zip)
  - Portable zip build script (build_portable.ps1)
  - Offline smoke test script (smoke_offline.ps1)

affects: [06-02, 06-03, 06-04]

tech-stack:
  added: [pyinstaller, cyclonedx-bom]
  patterns: [release-policy-block-list, powershell-build-scripts]

key-files:
  created:
    - packaging/spanglish-dictation.spec
    - scripts/build_portable.ps1
    - scripts/smoke_offline.ps1
    - tests/test_release_packaging.py
  modified:
    - pyproject.toml

key-decisions:
  - "Use PyInstaller onedir mode (not onefile) for inspectable release artifacts and license notice bundling"
  - "Add optional-dependency group 'release' with PyInstaller and cyclonedx-bom to keep runtime deps lean"
  - "Reject models/*, *.bin, *.gguf, cudnn*.dll, cublas*.dll, cudart*.dll from default portable zip"

patterns-established:
  - "is_blocked_release_path: central release policy helper in test suite, usable by build and smoke scripts"
  - "PowerShell build scripts with SkipBuild switch for incremental iteration"

requirements-completed: [REL-01, REL-02]

duration: 15min
completed: 2026-05-05
---

# Phase 6 Plan 01: Portable Packaging Foundation Summary

**PyInstaller onedir spec, blocked-artifact policy tests, portable zip build script, and offline smoke check — release artifact gate before licence/docs bundling**

## Performance

- **Duration:** 15 min
- **Tasks:** 2
- **Files modified:** 5 (4 created, 1 modified)

## Accomplishments
- PyInstaller onedir spec bundles `src/main.py` and `data/default_glossary.json` with name `spanglish-dictation`
- `is_blocked_release_path()` helper rejects models, GPU DLLs (.bin, .gguf, cudnn/cublas/cudart) in 12 passing tests
- `scripts/build_portable.ps1` stages, validates blocked-artifact policy, copies docs/LICENSES, creates portable zip
- `scripts/smoke_offline.ps1` runs privacy guard + release packaging regression tests as release gate

## Task Commits

1. **Task 1: Release packaging contract and policy tests** - `c02e9a1` (test)
2. **Task 2: Portable build and offline smoke scripts** - `8c1c28e` (feat)

## Files Created/Modified
- `packaging/spanglish-dictation.spec` — PyInstaller onedir contract; entry src/main.py, data/default_glossary.json
- `scripts/build_portable.ps1` — Param([switch]$SkipBuild, [string]$Version); blocks forbidden artifacts; creates dist/release/*.zip
- `scripts/smoke_offline.ps1` — Runs pytest on privacy_guard + release_packaging; optionally invokes verify_release_artifacts.py
- `tests/test_release_packaging.py` — 31 tests covering blocked paths, spec validation, build/smoke script audit
- `pyproject.toml` — Added `release` optional-dependency group with pyinstaller>=6.0, cyclonedx-bom>=5.0

## Decisions Made
- `is_blocked_release_path()` lives in test suite (not runtime) since it's a release policy function, not app logic
- Build script uses PowerShell `Compress-Archive` rather than a third-party zip library to minimize dependencies
- Smoke script references `verify_release_artifacts.py` conditionally — safe before that script exists (06-04)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Fixed PowerShell Join-Path three-argument calls**
- **Found during:** Task 2 (smoke script execution)
- **Issue:** PowerShell's `Join-Path` accepts only two positional parameters; calls with 3 args (e.g. `Join-Path $root "dist" "release"`) failed at runtime
- **Fix:** Nested Join-Path calls (e.g. `Join-Path (Join-Path $root "dist") "release"`)
- **Files modified:** scripts/build_portable.ps1, scripts/smoke_offline.ps1
- **Verification:** `powershell -File scripts/smoke_offline.ps1` exits 0
- **Committed in:** 8c1c28e (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Platform-specific PowerShell fix; all functionality preserved.

## Issues Encountered
- PowerShell's `Join-Path` two-arg limit required nesting for multi-segment paths — caught by smoke test execution
- No other issues

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- Packaging contract and release policy gate complete
- Ready for 06-02 (license bundle and SBOM support)
- build_portable.ps1 references LICENSES/ (created in 06-02) and sbom.cdx.json (generated in 06-02)

---
*Phase: 06-packaging-release*
*Completed: 2026-05-05*
