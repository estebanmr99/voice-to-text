# Project Instructions

## Project

Windows Offline Spanglish Dictation — A Windows-first, fully offline desktop voice-to-text app for technical Spanglish. Python + PySide6 shell with whisper.cpp CPU backend and faster-whisper NVIDIA dev backend.

## GSD Workflow

This project uses the Get Shit Done (GSD) workflow. All planning artifacts live under `.planning/`.

### Current Phase

Phase 1: Planning & Architecture — Partially complete. Architecture docs, privacy policy, license matrix, and benchmark plan created. Canonical project files reconstructed by hand due to GSD tooling recovery.

### Next Phase

Phase 2: MVP Offline Dictation — Blocked by missing Python toolchain.

### Critical Constraints

1. **No runtime network** — App must never make network calls at runtime
2. **No telemetry** — No analytics, crash uploads, or usage metrics
3. **No retained audio/transcripts** — Data-in-motion only by default
4. **Windows-first** — User-mode, no admin required
5. **Legal conservative** — All dependencies marked candidate/verify/blocked until approved

### Architecture

Modular monolith with 10 modules:
- ShellIntegration (PySide6/Qt tray, hotkey, panel)
- AudioCapture (sounddevice/PortAudio/WASAPI)
- SpeechDetector (WebRTC VAD default, Silero VAD accurate)
- Transcriber (whisper.cpp CPU, faster-whisper NVIDIA dev)
- ModelManager (local profiles, checksums, hardware detection)
- PostProcessor (deterministic Spanglish glossary)
- PasteController (Win32 clipboard + SendInput)
- PrivacyGuard (offline enforcement, redaction)
- SettingsStore (local preferences, no sync)
- Diagnostics (redacted local-only events)

### Blockers

- Python toolchain missing (python/py/uv/pytest unavailable)
- Local model assets missing (whisper.cpp models, VAD assets)
- GSD `gsd-sdk init` requires Claude login (unavailable in OpenCode)

### Commands

- Resume: `/gsd-resume` or check `.planning/STATE.md`
- Plan phase: `/gsd-plan-phase N`
- Discuss phase: `/gsd-discuss-phase N`
- Execute phase: `/gsd-execute-phase N`

## Coding Standards

- Python 3.11+
- Type hints where feasible
- pytest for testing
- No production code in planning phases
- No model binaries in git
- Commit planning docs atomically

## Stack

- Python + PySide6/Qt
- pywin32/ctypes for Win32 integration
- sounddevice/PortAudio for audio
- whisper.cpp (CPU shipping backend)
- faster-whisper/CTranslate2 (NVIDIA dev backend)
- WebRTC VAD (default), Silero VAD (accurate profile)
