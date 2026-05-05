---
phase: 05-spanglish-glossary
plan: 02
subsystem: glossary-ui
tags: [glossary, import, export, settings-dialog]
requires: ["05-01"]
provides: [import_glossary, export_glossary, settings-ui]
affects: [settings_dialog, shell_integration, settings_store, main]
tech-stack:
  added: [shutil (glossary import), QFileDialog (import/export UI)]
  patterns: [validate-before-write, round-trip JSON compatibility]
key-files:
  created: []
  modified:
    - src/glossary.py (import_glossary, export_glossary, get_entries_as_dicts)
    - src/settings_dialog.py (Import/Export buttons, glossary_store parameter)
    - src/settings_store.py (glossary_path typed property)
    - src/shell_integration.py (glossary_store parameter passthrough)
    - src/main.py (glossary_store injected into ShellIntegration)
    - tests/test_glossary.py (9 import/export tests)
    - tests/test_settings_dialog.py (3 UI tests)
decisions:
  - import copies validated JSON to user_path location (not in-place reference)
  - export uses same schema as default_glossary.json for round-trip compatibility
  - glossary_store flows: main.py -> ShellIntegration -> SettingsDialog
metrics:
  duration: "~10min"
  tasks: 2
  files: 7
---

# Phase 05 Plan 02: Glossary Import/Export Summary

**One-liner:** JSON glossary import/export with validation and Settings Dialog UI buttons, fully wired through ShellIntegration.

## Tasks Completed

| # | Task | Type | Commit | Status |
|---|------|------|--------|--------|
| 1 | Add import/export methods to GlossaryStore | auto | `afed874` | ✅ |
| 2 | Add Import/Export buttons to Settings Dialog | auto | `c1c219e` | ✅ |

## Test Results

```
tests/test_glossary.py .............. 22 passed (9 new import/export)
tests/test_settings_dialog.py ...... 9 passed (3 new UI button tests)
Full suite: 259 passed, 3 skipped (no regressions)
```

## Success Criteria Verification

1. ✅ User can import a valid glossary JSON via Settings → Glossary → Import
2. ✅ Invalid JSON shows warning dialog with error messages, no crash
3. ✅ User can export merged glossary (defaults + overrides) as shareable JSON
4. ✅ Export JSON matches import schema (round-trip compatibility)
5. ✅ Imported glossary overrides take effect immediately (on next normalize call)
6. ✅ All existing tests continue to pass

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

- **Import copies to user_path** rather than referencing source path: prevents broken references if source is moved/deleted
- **Export omits empty context** for cleaner output, includes context only when present
- **glossary_store flows through ShellIntegration** to avoid creating a second instance in SettingsDialog

## Known Stubs

None — all components fully wired.
