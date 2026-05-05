---
phase: 05-spanglish-glossary
plan: 01
subsystem: post-processing
tags: [glossary, normalization, post-processor, tdd]
requires: []
provides: [PostProcessor, GlossaryStore, default_glossary]
affects: [dictation_loop, main]
tech-stack:
  added: [re (regex), json (glossary format), dataclasses]
  patterns: [whole-word regex replacement, merge-by-key override, from_settings factory]
key-files:
  created:
    - src/glossary.py (GlossaryStore + GlossaryEntry)
    - src/post_processor.py (PostProcessor with normalize/preview/get_applied_rules)
    - data/default_glossary.json (25 Spanglish technical terms)
    - tests/test_glossary.py (13 tests)
    - tests/test_post_processor.py (16 tests)
  modified:
    - src/dictation_loop.py (post_processor parameter, normalization in _on_speech_end)
    - src/main.py (GlossaryStore+PostProcessor construction and injection)
    - tests/test_dictation_loop.py (6 new PostProcessor integration tests)
decisions:
  - D-04: User glossary at ~/.spanglish-dictation/user_glossary.json alongside settings
  - D-05: normalize() applies whole-word regex in single pass, case-insensitive
  - D-09: preview() equals normalize() — alias for confirmation mode clarity
  - D-10: PostProcessor wired between transcription and paste/confirm branch
metrics:
  duration: "~12min"
  tasks: 2
  files: 8
---

# Phase 05 Plan 01: PostProcessor + GlossaryStore Summary

**One-liner:** Deterministic whole-word glossary normalization engine with 25-term Spanglish default glossary, wired into DictationLoop for both immediate and confirmation paste modes.

## Tasks Completed

| # | Task | Type | Commits | Status |
|---|------|------|---------|--------|
| 1 | Create PostProcessor, GlossaryStore, and default glossary | auto (TDD) | `402a783` (RED), `69c716b` (GREEN) | ✅ |
| 2 | Wire PostProcessor into DictationLoop and main.py | auto | `b121985` | ✅ |

## TDD Gate Compliance

- **RED gate:** `402a783` — `test(05-01): add failing tests for PostProcessor and GlossaryStore` — 28 tests, all failing with `ModuleNotFoundError`
- **GREEN gate:** `69c716b` — `feat(05-01): implement PostProcessor and GlossaryStore` — 28 tests pass
- **REFACTOR:** Not applicable — no refactoring needed; implementation was clean on first pass

## Test Results

```
tests/test_glossary.py ....... 13 passed
tests/test_post_processor.py .. 16 passed
tests/test_dictation_loop.py .. 26 passed (6 new PostProcessor integration)
Full suite: 247 passed, 3 skipped (no regressions)
```

## Success Criteria Verification

1. ✅ `mergear el pr` → `mergear el PR` via `PostProcessor.normalize()`
2. ✅ `pushea el hotfix` remains unchanged (no false matches)
3. ✅ Accented Spanish text preserved exactly (á, ó — no stripping)
4. ✅ No translation or meaning change — only casing/acronym formatting
5. ✅ PostProcessor wired into DictationLoop between transcription and paste
6. ✅ Default glossary ships at `data/default_glossary.json`
7. ✅ User glossary at `~/.spanglish-dictation/user_glossary.json` overrides defaults
8. ✅ All existing tests pass without modification

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

- **Whole-word regex approach** chosen over trie/string replacement: simpler to implement, easy to verify correctness, bounded by entry count
- **User entries override by `input` key** rather than append: prevents duplicate entries, gives user full control
- **Entries stored as dict during merge** then converted to `GlossaryEntry` list: efficient lookup by key during merge, clean public API

## Known Stubs

None — all components fully wired with real data flow.

## Handoff

- Next plan: `05-02` (import/export UI)
- `dictation_loop.py` now accepts `PostProcessor | None` — default `None` preserves backward compat
- `main.py` constructs `GlossaryStore.from_settings(settings)` and `PostProcessor(glossary_store)`
