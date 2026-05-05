---
phase: 03-model-profiles
plan: 03
subsystem: ui
tags: [pyside6, tray-menu, profile-switching, transcriber, diagnostics]
requires:
  - phase: 03-model-profiles
    provides: hardware detection + resolver flow and canonical profile registry from 03-01/03-02
provides:
  - Tray Profile submenu with canonical profile selection
  - Runtime profile-change handler that re-resolves and restarts transcriber
  - UI/integration tests for profile selection and restart/failure flows
affects: [phase-04-gui-tray-polish, runtime-ux, profile-settings]
tech-stack:
  added: []
  patterns: [signal-driven profile switching, restart-on-selection with resolver result handling]
key-files:
  created: [tests/test_profile_integration.py, .planning/phases/03-model-profiles/03-03-SUMMARY.md]
  modified: [src/shell_integration.py, src/main.py, tests/test_shell_integration.py]
key-decisions:
  - "Expose profile switching through tray radio actions while preserving existing tray action ordering and behavior."
  - "Centralize profile-change apply logic in a helper so restart/failure behavior is testable without full app boot."
patterns-established:
  - "Profile changes are applied by stop -> resolve_profile -> start, with notification/diagnostic branches for failures."
  - "Status panel and tooltip include profile/model context to make runtime selection visible in the shell."
requirements-completed: [PROF-01, PROF-02, PROF-03]
duration: 23min
completed: 2026-05-05
---

# Phase 3 Plan 03: Tray Profile Switching and Restart Wiring Summary

**System tray now exposes profile selection and applies profile changes by re-resolving local models and restarting the transcriber safely.**

## Performance

- **Duration:** 23 min
- **Started:** 2026-05-05T14:32:00Z
- **Completed:** 2026-05-05T14:55:00Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Added a `Profile` tray submenu with exclusive radio actions, checked state from settings, and `profile_changed` signal emission.
- Added profile-change handling in `main.py` to stop the active worker, resolve the new profile, restart the transcriber, and surface errors/advisories.
- Added shell and integration tests validating profile menu behavior, settings updates, signal flow, and restart/failure branches.

## Task Commits

1. **Task 1: Add profile submenu and profile display to ShellIntegration** - `b1cf520` (feat)
2. **Task 2: Wire profile change to transcriber restart in main.py** - `bd86d1d` (feat)
3. **Task 3: Add tests for profile UI and integration** - `9b66bdc` (test)

## Files Created/Modified
- `src/shell_integration.py` - Added profile menu, selection handling, optional model manager support, profile status text, and profile tooltip method.
- `src/main.py` - Added `_apply_profile_change()` and connected `shell.profile_changed` to resolver-driven restart flow.
- `tests/test_shell_integration.py` - Extended tray/status tests with profile submenu, checked state, settings update, signal emission, and profile tooltip assertions.
- `tests/test_profile_integration.py` - Added focused tests for stop→resolve→start success and missing-model notification failure paths.

## Decisions Made
- Kept profile switching local-only and deterministic: no downloads, no settings mutation outside explicit user tray selection.
- Used a dedicated helper in `main.py` to avoid brittle full-Qt integration for critical restart logic testing.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 3 complete: profile metadata, resolver behavior, and tray-level switching are all implemented and tested.
- Phase 4 can focus on broader GUI polish/settings UX using these established profile APIs and runtime signals.

## Self-Check: PASSED

- FOUND: `.planning/phases/03-model-profiles/03-03-SUMMARY.md`
- FOUND commit: `b1cf520`
- FOUND commit: `bd86d1d`
- FOUND commit: `9b66bdc`

---
*Phase: 03-model-profiles*
*Completed: 2026-05-05*
