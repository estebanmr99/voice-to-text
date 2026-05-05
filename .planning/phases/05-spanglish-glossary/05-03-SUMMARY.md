---
phase: 05-spanglish-glossary
plan: 03
subsystem: testing
tags: [fixtures, parametrized-tests, glossary-integrity, success-criteria]
requires: ["05-01"]
provides: [comprehensive-test-suite, glossary-integrity-checks]
affects: [default_glossary]
tech-stack:
  added: [pytest parametrize, pytest fixtures]
  patterns: [fixture-driven testing, parametrized edge cases]
key-files:
  created:
    - tests/test_post_processor_fixtures.py (29 fixture-driven tests)
    - tests/test_glossary_fixtures.py (9 integrity tests)
  modified:
    - data/default_glossary.json (expanded from 25 to 39 entries)
decisions:
  - Spanglish verb forms (pushear, mergear, deployar, commitear) added as identity entries
  - 7 additional tech acronyms added (UI, UX, DB, VM, OS, IP, DNS)
  - Test suites organized by concern: SuccessCriteria, WordBoundary, EdgeCases, SpanglishVerbForms, NewAcronyms, GlossaryIntegrity
metrics:
  duration: "~5min"
  tasks: 1
  files: 3
---

# Phase 05 Plan 03: Fixture-Driven Test Suite Summary

**One-liner:** 38 fixture-driven parametrized tests proving all 5 ROADMAP success criteria, word-boundary correctness, Spanglish verb preservation, and glossary integrity.

## Tasks Completed

| # | Task | Type | Commit | Status |
|---|------|------|--------|--------|
| 1 | Create fixture-driven tests for all success criteria and edge cases | auto (TDD) | `4fea6e2` | ✅ |

## TDD Gate Compliance

- **RED gate:** Not applicable — tests verify existing implementation from 05-01. All 38 tests pass against the existing PostProcessor/GlossaryStore.
- **GREEN gate:** `4fea6e2` — tests pass, implementation already correct from 05-01.
- **Note:** Plan's TDD flag marks test-first intent; feature under test existed from 05-01, so tests validate rather than drive new implementation.

## Test Results

```
tests/test_post_processor_fixtures.py ............................. 29 passed
tests/test_glossary_fixtures.py ......... 9 passed
Full suite: 297 passed, 3 skipped (+38 from this plan)
```

## Test Coverage Added

### Success Criteria (5 tests)
- SC1: `mergear el pr` → `mergear el PR`
- SC2: `pushea el hotfix` unchanged
- SC3: Accents preserved (`rápido`, `caído`)
- SC4: No translation (`deployar` stays intact)
- SC5: User glossary override

### Word Boundary (5 parametrized)
- `pr` in `proceso` — no match
- `pr` in `preparar` — no match
- `api` in `capital` — no match

### Edge Cases (8 tests)
- Empty string, whitespace, multiple matches, punctuation preserved
- preview == normalize, no matches returns original
- get_applied_rules tracking, case-insensitive input

### Spanglish Verb Forms (4 tests)
- `pushear`, `mergear`, `deployar`, `commitear` all preserved

### New Acronyms (7 tests)
- UI, UX, DB, VM, OS, IP, DNS normalization

### Glossary Integrity (9 tests)
- Load without error, no duplicate inputs
- Non-empty input/output, lowercase inputs
- Valid JSON, version=1, entry count >= 38
- Spanglish verb entries present
- Round-trip export→import

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

- **39 total entries** in default glossary (25 original + 14 added across 05-03)
- **Spanglish verbs as identity entries** with `context` noting "do not translate" — prevents future v2 LLM rewriting from modifying them
- **Test classes organized by concern** for maintainability and targeted regression debugging

## Known Stubs

None — all tests are exercising real, implemented code paths.
