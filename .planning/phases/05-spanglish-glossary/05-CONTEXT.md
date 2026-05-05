# Phase 5: Spanglish Glossary - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning
**Source:** Architectural decisions and roadmap requirements

<domain>
## Phase Boundary

Implement deterministic post-processing for technical Spanglish terms. The PostProcessor module applies a user-editable glossary to normalize transcript output without translation, LLM rewriting, or meaning change. This phase creates the normalization engine, default glossary, import/export, and wires everything into the existing dictation loop.

**In scope:**
- PostProcessor module with normalize() and preview() methods
- GlossaryStore for loading, validating, merging glossary entries
- Default built-in glossary with Spanglish technical terms
- Import/export of user glossary files (JSON format)
- Wiring PostProcessor into DictationLoop between transcription and paste
- Fixture-driven tests proving all success criteria

**Out of scope:**
- LLM-powered rewriting (deferred to v2)
- Cloud-based glossary sync (violates offline guarantee)
- Translation to English-only or Spanish-only output
- Model binary management or transcription improvements

</domain>

<decisions>
## Implementation Decisions

### Glossary Format
- D-01: Glossary entries stored as JSON arrays with `{"input": "pr", "output": "PR", "context": "optional"}` schema — simple, deterministic, and editable by hand
- D-02: Default glossary bundled at `data/default_glossary.json` — ships with the app, not in user-writable space
- D-03: User glossary at `~/.spanglish-dictation/user_glossary.json` (alongside settings) — loaded on top of defaults, user entries override defaults on conflict
- D-04: Import/export uses the same JSON format as `user_glossary.json` — no conversion needed

### Normalization Engine
- D-05: `PostProcessor.normalize()` applies entries as whole-word replacement (word-boundary-aware) in a single pass — no multi-pass re-application
- D-06: Case-insensitive matching for input terms, preserving the original casing style of the output — "PR" not "pr"
- D-07: Accented Spanish text (á, é, í, ó, ú, ñ, ü) is never modified — glossary entries are applied as additions, not replacements of accented text
- D-08: Punctuation and whitespace around matched terms are preserved exactly
- D-09: `PostProcessor.preview()` returns the normalized text without pasting — used by confirmation mode

### Integration
- D-10: PostProcessor is wired into DictationLoop between transcription and paste — immediate mode pastes normalized text, confirmation mode shows normalized text in the edit dialog
- D-11: GlossaryStore reads SettingsStore.glossary_path for custom glossary location — falls back to default path if empty
- D-12: PostProcessor is a pure function module — no Qt, no network, no audio, testable in isolation
- D-13: Empty or missing user glossary is not an error — defaults are always loaded first

### the agent's Discretion
- Exact set of Spanglish terms in the default glossary (beyond the success criteria examples)
- Internal data structure for glossary lookup (trie, sorted list, dict — optimize for correctness first)
- Whether to preserve original casing or force glossary casing on partial matches

</decisions>

<canonical_refs>
## Canonical References

### Architecture
- `.planning/architecture/ARCHITECTURE.md` — Module architecture, PostProcessor responsibility, dataflow order
- `.planning/architecture/INTERFACES.md` — Post-Processing Interface contract: normalize(), validate_glossary(), preview()

### Existing Integration Points
- `src/dictation_loop.py` — Current transcription→paste flow, confirmation mode hook
- `src/settings_store.py` — glossary_path setting already persisted
- `src/settings_dialog.py` — Glossary path browser UI already exists
- `src/main.py` — Module wiring and initialization
- `src/confirmation_dialog.py` — Receives text for edit-before-paste

</canonical_refs>

<specifics>
## Specific Ideas

- Success criteria examples: `mergear el pr` → `mergear el PR`, `pushea el hotfix` remains unchanged, accents preserved, no translation
- The glossary must handle both individual terms ("pr" → "PR") and Spanglish verb forms ("deployar" → "deployar" with no change since it's already correct)
- Override semantics: if user glossary says "pr" → "Pull Request", that overrides the default "pr" → "PR"
- Whole-word matching only: "pr" matches the word "pr" but not the "pr" in "process"
- The normalize function must handle the Whisper output format — typically lowercase with minimal punctuation

</specifics>

<deferred>
## Deferred Ideas

- LLM-powered context-aware rewriting (v2 requirement)
- Cloud glossary sync (violates offline guarantee)
- Auto-learning from user corrections (v2 at earliest)
- Multiple glossary file format support beyond JSON (only JSON for v1)
- Per-window application rules (different glossaries for different apps)

</deferred>

---
*Phase: 05-spanglish-glossary*
*Context gathered: 2026-05-05 via architecture review and requirements analysis*