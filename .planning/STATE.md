---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: complete
stopped_at: v0.2.0 shipped - hotkey PTT fix, Azure/ITS backlog captured
last_updated: "2026-05-23T00:00:00-06:00"
progress:
  total_phases: 7
  completed_phases: 5
  total_plans: 18
  completed_plans: 18
  percent: 100
---

# Project State

## Project Reference

**Building:** Windows Offline Spanglish Dictation — Turn technical Spanglish speech into pasted text without network.

## Current Position

Phase: 06 (packaging-release) — COMPLETE
Plan: 4 of 4
**Phase:** Quick task 260505-w0l — release publication
**Status:** `v0.1.0` public release shipped — follow-up verification only
**Progress:** [██████████] 100%

## Recent Decisions

- 2026-05-04: Locked modular monolith architecture with 10 modules and explicit interfaces
- 2026-05-04: Established strict no-runtime-network privacy policy
- 2026-05-04: Defined conservative license matrix (CUDA/cuDNN redistribution BLOCKED)
- 2026-05-04: Created benchmark plan with 10 candidate rows (all pending local execution)
- 2026-05-04: Reconstructed canonical GSD files (PROJECT.md, STATE.md, ROADMAP.md, REQUIREMENTS.md, AGENTS.md)
- 2026-05-05: Installed Python 3.12.10 and pytest 9.0.3 via winget
- 2026-05-05: Side-loaded whisper.cpp models: base (141MB) and small (465MB) for AMD Ryzen 5 3600 + RTX 2070 Super workstation
- 2026-05-05: Created model registry with checksums, hardware profile recommendations, and faster-whisper download instructions
- 2026-05-04: Completed Phase 2 research: validated PySide6 tray/hotkey, sounddevice, pywhispercpp, webrtcvad, pywin32 clipboard/SendInput, PyInstaller packaging
- 2026-05-04: Created 5 Phase 2 execution plans (02-01 through 02-05) covering scaffold, audio+VAD, transcriber worker, paste controller, and dictation loop wiring
- 2026-05-04: **02-01 scaffold complete** — Python src-layout, SettingsStore, Diagnostics, PySide6 tray shell committed
- 2026-05-04: Used manual QApplication fixture instead of pytest-qt to minimize dev dependencies
- 2026-05-04: Created programmatic fallback tray icon for Windows (no bundled PNG assets)
- 2026-05-04: **02-02 audio+VAD complete** — AudioCapture (sounddevice/PortAudio), SpeechDetector (webrtcvad), integration tests committed
- 2026-05-05: **02-04 PasteController complete** — SendInput/clipboard paste with backup/restore, automatic fallback, retry logic, and comprehensive mocked unit tests
- 2026-05-05: **02-03 Transcriber complete** — ModelManager with JSON registry, pywhispercpp worker process via multiprocessing, crash recovery with backoff
- 2026-05-05: **02-05 Wire dictation loop complete** — PrivacyGuard with runtime network blocking, ShellIntegration with global hotkey and tray, DictationLoop orchestrating full audio→VAD→transcribe→paste, main.py wired
- 2026-05-05: **04-01 Settings Dialog complete** — tray action opens full settings dialog with validation and persistence
- 2026-05-05: **04-02 Confirmation Mode complete** — editable confirm-before-paste flow wired through DictationLoop and main
- 2026-05-05: **04-03 Tray Polish complete** — grouped tray menu, state-aware actions, dismissible status panel, double-click reveal
- 2026-05-05: Phase 5 Spanglish Glossary plans created (05-01, 05-02, 05-03)
- 2026-05-05: Fixed whisper.cpp input normalization, language propagation, and toggle-stop transcription so desktop dictation matches the real audio pipeline
- 2026-05-05: Replaced broken Win32 hotkey handling with pynput global hotkeys, added continuous dictation, and synced settings changes back into the live tray shell
- 2026-05-05: Hardened runtime reliability with atomic settings saves, more tolerant VAD/paste retries, sample-rate negotiation for microphone backends, and full regression coverage (378 passed, 3 skipped)
- 2026-05-05: Completed quick task 260505-v8d — publish-ready docs finalized, `.sisyphus/` removed from public repo path, GitHub repo created, and local release bundle verified
- 2026-05-05: Published public GitHub release `v0.1.0` at `https://github.com/estebanmr99/voice-to-text/releases/tag/v0.1.0` with portable zip, SBOM, and SHA256SUMS.txt assets
- 2026-05-05: Added canonical release notes at `docs/releases/v0.1.0.md` and locked release docs/tests to the real `gh release edit v0.1.0 --notes-file` flow
- 2026-05-05: Fixed tag-triggered release workflow publication permissions after GitHub Actions returned 403 on `softprops/action-gh-release`

## Pending Todos

- Run a clean-machine post-release smoke test by downloading `v0.1.0` from GitHub Releases and confirming side-loaded-model startup
- Execute ASR/VAD benchmarks for available models (base, small)
- Run manual end-to-end verification on the Logitech Brio path across MME/WASAPI and confirm global hotkeys behave correctly in UAT
- Confirm the next tag-triggered release workflow succeeds end-to-end now that `contents: write` is explicit

## Blockers/Concerns

1. **GSD `gsd-sdk init` requires Claude login** — Canonical files hand-written; future `/gsd-*` commands in OpenCode work fine
2. **webrtcvad has no PyPI wheel for Windows** — Resolved by `webrtcvad-wheels==2.0.11` in pyproject.toml; import path verified as `import webrtcvad`
3. **Manual device/backend validation still required** — Automated tests pass, but Logitech Brio behavior across MME/WASAPI and real global hotkey capture still needs direct UAT confirmation
4. **GitHub Actions publish step initially returned 403 for `v0.1.0`** — Public release was created successfully with `gh release create`; workflow now declares `permissions: contents: write` for future tags

### Quick Tasks Completed

| # | Description | Date | Commit | Status | Directory |
|---|-------------|------|--------|--------|-----------|
| 260511-q9k | Close EVAL-REVIEW gaps: create reference audio dataset, WER benchmark, model integrity checks, dictation smoke test, and integrate into release pipeline | 2026-05-12 | d003e3e | Verified | [260511-q9k-close-eval-review-gaps-create-reference-](./quick/260511-q9k-close-eval-review-gaps-create-reference-/) |
| 260523-hj8 | Fix PTT hotkey using pynput HotKey + canonical press/release listener | 2026-05-23 | f8db4db | Verified | |

## Session Continuity

Last activity: 2026-05-23 - Shipped v0.2.0: PTT hotkey fix + release
Last session: 2026-05-23T00:00:00-06:00
Stopped at: v0.2.0 shipped, milestone v1.0 complete
Resume file: .planning/quick/260505-w0l-i-generated-everything-manually-and-was-/260505-w0l-SUMMARY.md

## Task Status

| Task | Status | Blocker |
|------|--------|---------|
| 1. GSD tooling recovery | DONE | Canonical files hand-written; `gsd-sdk` CLI available for non-LLM queries |
| 2. Architecture/privacy/licensing | DONE | — |
| 3. ASR/VAD benchmark | PARTIAL | 2 of 10 ASR models available (base, small); VAD assets pending |
| 4. MVP dictation loop | DONE | 02-01 through 02-05 complete; full push-to-talk loop wired |
| 5. Model profiles | DONE | Phase 3 complete |
| 6. GUI/tray polish | DONE | 04-01 through 04-03 complete |
| 7. Spanglish glossary | READY | 05-01 through 05-03 ready; follow-up bug-fix/polish pass committed |
| 8. Packaging/release | DONE | Public GitHub release `v0.1.0` shipped with portable zip, SBOM, and SHA256SUMS.txt |

## Next Action

1. Verify GitHub Actions release workflow completed for v0.2.0
2. Download v0.2.0 portable zip from GitHub Releases and test on clean machine
3. Plan Phase 7: Azure API & ITS data support

## Session Handoff

- Handoff file: `.planning/phases/02-mvp-offline-dictation/.continue-here.md`
- Structured state: `.planning/HANDOFF.json`
- Status: **COMPLETE** — v0.2.0 shipped with working PTT; milestone v1.0 achieved

## Performance Metrics

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 02-01 P1 | — | — | — |
| Phase 02-02 P2 | — | — | — |
| Phase 02-04 P4 | — | — | — |
| Phase 02-03 P3 | 30min | 2 tasks | 5 files |
| Phase 04-01 P1 | 25min | 2 tasks | 3 files |
| Phase 04-02 P2 | 20min | 3 tasks | 5 files |
| Phase 04-03 P3 | 30min | 3 tasks | 3 files |
| Phase 05-spanglish-glossary P01 | 12min | 2 tasks | 8 files |
| Phase 05-spanglish-glossary P02 | 10min | 2 tasks | 7 files |
| Phase 05-spanglish-glossary P03 | 5min | 1 tasks | 3 files |
