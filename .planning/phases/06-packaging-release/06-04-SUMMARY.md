---
phase: 06-packaging-release
plan: 04
subsystem: infra
tags: [github-actions, release-automation, checksums, artifact-verification]

requires:
  - phase: 06-packaging-release
    plan: 01
    provides: portable packaging and blocked policy
  - phase: 06-packaging-release
    plan: 02
    provides: license bundle and SBOM command
  - phase: 06-packaging-release
    plan: 03
    provides: release documentation and README

provides:
  - Release artifact verifier (verify_release_artifacts.py)
  - End-to-end release preparation script (prepare_release.ps1)
  - GitHub Actions tag-triggered release workflow
  - GitHub release checklist with pre-publish verification

affects: []

tech-stack:
  added: [softprops/action-gh-release]
  patterns: [cli-verifier, powershell-orchestration, github-actions-release]

key-files:
  created:
    - scripts/verify_release_artifacts.py
    - scripts/prepare_release.ps1
    - .github/workflows/release.yml
    - docs/GITHUB-RELEASE-CHECKLIST.md
    - tests/test_release_workflow.py

key-decisions:
  - "Release workflow triggers on v* tags only — manual push for full control over publication timing"
  - "Verifier treats blocked patterns as hard failures (exit 1) — CI fails if models or GPU DLLs appear"
  - "Workflow does not install huggingface-cli, curl, or Invoke-WebRequest — enforced by automated tests"
  - "SHA256SUMS.txt computed from all files in dist/release/ after build — catch-all for unlisted artifacts"

patterns-established:
  - "python CLI pattern: functions return (found, missing, blocked) tuple, main() renders output"
  - "PowerShell orchestration: sequential pipeline with throw-on-failure at each step"

requirements-completed: [REL-01, REL-02]

duration: 10min
completed: 2026-05-05
---

# Phase 6 Plan 04: GitHub Release Automation Summary

**Release artifact verifier with blocked-pattern enforcement, 6-step PowerShell release pipeline, tag-triggered GitHub Actions workflow with asset upload, and pre-publish checklist — 70 automated tests across the full release suite**

## Performance

- **Duration:** 10 min
- **Tasks:** 2
- **Files modified:** 5 (4 created, 1 created in Task 1)

## Accomplishments
- `scripts/verify_release_artifacts.py` — CLI scanner validates portable zip, SBOM, SHA256SUMS, notices, and rejects blocked patterns (exit 0/1)
- `scripts/prepare_release.ps1` — 6-step pipeline: tests → licence → SBOM → build → checksums → verify; Version parameter
- `.github/workflows/release.yml` — v* tag trigger, Windows runner, Python 3.12, pip install, prepare_release, smoke_offline, softprops/action-gh-release uploads 6 assets
- `docs/GITHUB-RELEASE-CHECKLIST.md` — Pre-tag checks, artifact inventory, blocked-artifact verification, SBOM publication, model side-loading, post-tag CI steps

## Task Commits

1. **Task 1: Release artifact verifier and workflow tests** - `4278ac4` (test)
2. **Task 2: Release prep script, GitHub workflow, and checklist** - `8aed85f` (feat)

## Files Created/Modified
- `scripts/verify_release_artifacts.py` — verify_release_dir() returns (found, missing, blocked); main() CLI with exit codes
- `scripts/prepare_release.ps1` — 6 sequential steps: pytest, licence bundle, SBOM, build, SHA-256, verify
- `.github/workflows/release.yml` — Tag-triggered (`v*`), Windows runner, Python 3.12, publishes zip/SBOM/checksums/notices/release docs
- `docs/GITHUB-RELEASE-CHECKLIST.md` — 8 pre-tag checks, 6 required artifacts, blocked-artifact list, SBOM/publication/model verification
- `tests/test_release_workflow.py` — 19 tests: verifier (missing/blocked/valid), workflow content (triggers/assets/forbidden strings), checklist, prepare_release script

## Decisions Made
- Workflow uses `softprops/action-gh-release@v1` for GitHub release management (well-maintained, no extra dependencies)
- prepare_release.ps1 uses throw-on-failure at each step — no partial releases
- Verifier requires `LICENSES/MODEL-NOTICES.md` when LICENSES/ exists — complete notice bundle or nothing
- Workflow tests assert absence of download commands (curl, Invoke-WebRequest) not just CUDA/cuDNN tokens

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Test for valid release dir was missing MODEL-NOTICES.md in temp fixture — fixed by adding it
- No other issues

## User Setup Required
None — no external service configuration required.

## Phase Completion
Phase 6 (Packaging & Release) is complete. All 4 plans delivered:
- 06-01: Portable packaging foundation and offline smoke checks
- 06-02: License bundle and SBOM support
- 06-03: Release documentation (README, LICENSE, PRIVACY, RELEASE, MODEL-SIDELOADING)
- 06-04: GitHub release automation, checksums, and artifact verification

---
*Phase: 06-packaging-release*
*Completed: 2026-05-05*
