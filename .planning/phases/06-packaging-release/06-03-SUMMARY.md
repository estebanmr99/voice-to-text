---
phase: 06-packaging-release
plan: 03
subsystem: docs
tags: [readme, license, privacy, sideloading, release-guide]

requires:
  - phase: 06-packaging-release
    plan: 01
    provides: portable packaging contract
  - phase: 06-packaging-release
    plan: 02
    provides: license notices, SBOM command

provides:
  - Public README with offline/privacy/sideloading guarantees
  - MIT LICENSE with copyright holder
  - Release guide with full checklist
  - Model side-loading guide with checksums and download URLs
  - Public privacy statement with exact runtime guarantees

affects: [06-04]

tech-stack:
  added: []
  patterns: [content-validation-tests, privacy-guarantee-docs]

key-files:
  created:
    - README.md
    - LICENSE
    - docs/RELEASE.md
    - docs/MODEL-SIDELOADING.md
    - docs/PRIVACY.md
    - tests/test_release_docs.py

key-decisions:
  - "Privacy statement mirrors ARCHITECTURE/PRIVACY.md guarantees verbatim — single source of truth"
  - "Model side-loading docs include both curl commands and checksum verification steps"
  - "Release guide references smoke_offline.ps1 and blocked artifact patterns directly"

patterns-established:
  - "Content-validation tests: pathlib-based string assertions on public docs"
  - "Privacy guarantees as documented requirements, not marketing — 'no runtime network' not 'privacy-first'"

requirements-completed: [REL-01, REL-02]

duration: 10min
completed: 2026-05-05
---

# Phase 6 Plan 03: Release Documentation Summary

**GitHub-ready README, MIT license, model side-loading guide with SHA-256 checksums, release checklist, and public privacy statement — 20 automated content validation tests**

## Performance

- **Duration:** 10 min
- **Tasks:** 2
- **Files modified:** 6 (all created)

## Accomplishments
- README.md states offline, no telemetry, no runtime downloads, and links to all docs and licenses
- MIT LICENSE with Spanglish Dictation Team as copyright holder
- docs/RELEASE.md — 6-step checklist spanning build, smoke, SBOM, checksums, and blocked artifact policy
- docs/MODEL-SIDELOADING.md — ggml-base.bin/ggml-small.bin with sizes, hashes, curl commands, verification steps
- docs/PRIVACY.md — public statement mirroring ARCHITECTURE/PRIVACY.md: 7 runtime guarantees, data handling table, no-cloud-fallback

## Task Commits

1. **Task 1: Release documentation tests** - `609a7e6` (test)
2. **Task 2: GitHub-ready release docs and MIT license** - `5cd3e8f` (feat)

## Files Created/Modified
- `README.md` — Repository landing page: what it does, privacy, install, development, release artifacts
- `LICENSE` — Standard MIT License text, copyright Spanglish Dictation Team
- `docs/RELEASE.md` — Build, smoke, SBOM, checksums, blocked artifact list, before-publish checklist
- `docs/MODEL-SIDELOADING.md` — Model directory, two models with SHA-256, curl commands, verification, NVIDIA dev profile
- `docs/PRIVACY.md` — 7 runtime guarantees, data handling table, no cloud fallback, no retained transcripts by default
- `tests/test_release_docs.py` — 20 tests: README, LICENSE, RELEASE, MODEL-SIDELOADING, PRIVACY content validation

## Decisions Made
- Privacy docs use "no runtime network" phrasing consistently (not "offline-first") to match architecture
- Checksums in MODEL-SIDELOADING.md are verbatim from MODEL-REGISTRY.md — single source of truth
- Release checklist includes `cyclonedx_py` command as user instruction, not auto-run script step

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness
- Repository is GitHub-ready with README, LICENSE, and full documentation
- Ready for 06-04 (GitHub release automation and checksum verification)
- Release docs reference `scripts/verify_release_artifacts.py` (to be created in 06-04)

---
*Phase: 06-packaging-release*
*Completed: 2026-05-05*
