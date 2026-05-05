# Project State

## Project Reference

**Building:** Windows Offline Spanglish Dictation — Turn technical Spanglish speech into pasted text without network.

## Current Position

**Phase:** 1 of 6 — Planning and Architecture
**Status:** Complete — Architecture locked, benchmarks designed, canonical files reconstructed, Python toolchain installed, models side-loaded
**Progress:** [████████░░] 70%

## Recent Decisions

- 2026-05-04: Locked modular monolith architecture with 10 modules and explicit interfaces
- 2026-05-04: Established strict no-runtime-network privacy policy
- 2026-05-04: Defined conservative license matrix (CUDA/cuDNN redistribution BLOCKED)
- 2026-05-04: Created benchmark plan with 10 candidate rows (all pending local execution)
- 2026-05-04: Reconstructed canonical GSD files (PROJECT.md, STATE.md, ROADMAP.md, REQUIREMENTS.md, AGENTS.md)
- 2026-05-05: Installed Python 3.12.10 and pytest 9.0.3 via winget
- 2026-05-05: Side-loaded whisper.cpp models: base (141MB) and small (465MB) for AMD Ryzen 5 3600 + RTX 2070 Super workstation
- 2026-05-05: Created model registry with checksums, hardware profile recommendations, and faster-whisper download instructions

## Pending Todos

- Side-load local VAD assets (WebRTC, Silero) when needed for benchmarks
- Execute ASR/VAD benchmarks for available models (base, small)
- Begin Phase 2 MVP implementation

## Blockers/Concerns

1. **No production code exists** — Greenfield repo, no src/ or tests/ yet
2. **GSD `gsd-sdk init` requires Claude login** — Canonical files hand-written; future `/gsd-*` commands in OpenCode work fine

## Session Continuity

Last session: 2026-05-05 04:15–04:45
Stopped at: Models side-loaded for workstation. Ready to advance to Phase 2 MVP Offline Dictation.
Resume file: None (no .continue-here or HANDOFF.json)

## Task Status

| Task | Status | Blocker |
|------|--------|---------|
| 1. GSD tooling recovery | DONE | Canonical files hand-written; `gsd-sdk` CLI available for non-LLM queries |
| 2. Architecture/privacy/licensing | DONE | — |
| 3. ASR/VAD benchmark | PARTIAL | 2 of 10 ASR models available (base, small); VAD assets pending |
| 4. MVP dictation loop | READY | Python + models available, start Phase 2 |
| 5. Model profiles | BLOCKED | Needs Task 4 |
| 6. GUI/tray polish | BLOCKED | Needs Task 4 |
| 7. Spanglish glossary | BLOCKED | Needs Task 4 |
| 8. Packaging/release | BLOCKED | Needs Tasks 4-7 |

## Next Action

1. Run `/gsd-plan-phase 2` to create Phase 2 execution plans
2. Or run `/gsd-discuss-phase 2` first to gather MVP context
3. MVP can use `ggml-base.bin` as default shipping model
