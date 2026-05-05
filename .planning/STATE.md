# Project State

## Project Reference

**Building:** Windows Offline Spanglish Dictation — Turn technical Spanglish speech into pasted text without network.

## Current Position

**Phase:** 1 of 6 — Planning and Architecture
**Status:** Partially complete — Architecture locked, benchmarks designed, implementation blocked by missing tooling
**Progress:** [██████░░░░] 35%

## Recent Decisions

- 2026-05-04: Locked modular monolith architecture with 10 modules and explicit interfaces
- 2026-05-04: Established strict no-runtime-network privacy policy
- 2026-05-04: Defined conservative license matrix (CUDA/cuDNN redistribution BLOCKED)
- 2026-05-04: Created benchmark plan with 10 candidate rows (all pending local execution)
- 2026-05-04: Documented GSD tooling recovery attempts; `gsd-sdk` remains shell-invisible without Claude login

## Pending Todos

- Fix Python toolchain availability (python/py/uv/pytest all missing)
- Side-load local whisper.cpp models for benchmark execution
- Side-load local VAD assets (WebRTC, Silero)
- Reconstruct canonical GSD files (this file, PROJECT.md, ROADMAP.md, REQUIREMENTS.md)
- Execute ASR/VAD benchmarks once models available
- Begin MVP implementation (Task 4)

## Blockers/Concerns

1. **Python toolchain missing** — Blocks Tasks 4-8 implementation and testing
2. **Local model assets missing** — Blocks Task 3 benchmark execution
3. **GSD canonical files missing** — Blocked Task 1 completion; hand-reconstructing now
4. **No production code exists** — Greenfield repo, no src/ or tests/ yet

## Session Continuity

Last session: 2026-05-04 20:40–03:54
Stopped at: GSD tooling partially recovered (`gsd-sdk` v1.40.0 installed and visible on PATH, but `init` requires Claude login). Canonical planning files being hand-reconstructed from Omo's architecture and benchmark work.
Resume file: None (no .continue-here or HANDOFF.json)

## Task Status

| Task | Status | Blocker |
|------|--------|---------|
| 1. GSD tooling recovery | PARTIAL | `gsd-sdk init` needs Claude login |
| 2. Architecture/privacy/licensing | DONE | — |
| 3. ASR/VAD benchmark | PARTIAL | No local models/VAD assets |
| 4. MVP dictation loop | BLOCKED | No Python toolchain |
| 5. Model profiles | BLOCKED | Needs Task 4 + models |
| 6. GUI/tray polish | BLOCKED | Needs Task 4 |
| 7. Spanglish glossary | BLOCKED | No Python + needs Task 4 |
| 8. Packaging/release | BLOCKED | Needs Tasks 4-7 |

## Next Action

After canonical files are committed:
1. Install Python toolchain (or verify availability)
2. Side-load whisper.cpp tiny/base models
3. Begin Task 4 MVP implementation
