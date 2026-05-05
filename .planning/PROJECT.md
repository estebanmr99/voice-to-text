# Windows Offline Spanglish Dictation

## What This Is

A Windows-first, 100% offline desktop voice-to-text application for technical Spanglish dictation. It runs from the system tray, activates via global hotkey, captures microphone audio, detects speech segments using VAD, transcribes offline using local Whisper models, applies deterministic post-processing for technical terms, and pastes the result into the previously focused Windows application.

## Core Value

Turn technical Spanglish speech into correctly formatted pasted text without ever sending audio or text to the internet.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] **PRIV-01**: App must never make runtime network calls for ASR, telemetry, model downloads, or updates
- [ ] **PRIV-02**: No retained audio or transcripts by default; redacted diagnostics only
- [ ] **CORE-01**: Activate dictation via global hotkey (push-to-talk and toggle modes)
- [ ] **CORE-02**: Capture microphone audio with device selection and WASAPI-compatible backend
- [ ] **CORE-03**: Detect speech start/end using VAD with selectable profiles
- [ ] **CORE-04**: Transcribe offline using local quantized Whisper models
- [ ] **CORE-05**: Post-process transcripts with deterministic Spanglish technical glossary
- [ ] **CORE-06**: Paste final text into focused Windows app via clipboard + SendInput
- [ ] **CORE-07**: Preserve and restore previous clipboard contents where feasible
- [ ] **CORE-08**: Show status via system tray icon and floating topmost panel
- [ ] **CORE-09**: Run without admin rights for normal use
- [ ] **MOD-01**: Backend-switchable architecture for ASR, VAD, paste, post-processing
- [ ] **MOD-02**: Worker process isolation for transcription to keep UI responsive
- [ ] **PROF-01**: CPU portable profile with whisper.cpp quantized model
- [ ] **PROF-02**: CPU high-accuracy profile with larger whisper.cpp model
- [ ] **PROF-03**: NVIDIA dev profile with faster-whisper/CTranslate2
- [ ] **GUI-01**: Tray menu with Start/Stop, Settings, Profile, Paste Mode, Exit
- [ ] **GUI-02**: Confirmation/edit-before-paste mode as user-selectable option
- [ ] **GUI-03**: Settings panel for hotkeys, device, model, VAD profile, glossary
- [ ] **TEST-01**: Privacy tests fail if network calls are introduced
- [ ] **TEST-02**: Missing/corrupt model paths return local errors without network attempts
- [ ] **REL-01**: Open source, legal for GitHub, cloneable without cloud services
- [ ] **REL-02**: SBOM and license notices for all dependencies and model assets

### Out of Scope

- Cloud ASR, paid APIs, accounts, sync — violates offline guarantee
- Telemetry, auto-update, runtime model downloads — violates privacy policy
- Local LLM rewriting or generative assistant behavior — scope creep beyond deterministic post-processing
- Production model binaries in git history — legal/licensing constraint
- CUDA/cuDNN redistribution — blocked until license review
- macOS/Linux support — Windows-first MVP

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python + PySide6/Qt shell | Best balance for Windows desktop UX, tray support, Python ASR ecosystem | Locked |
| whisper.cpp shipping CPU backend | Portable CPU-first inference, no GPU stack required for users | Candidate pending benchmark |
| faster-whisper/CTranslate2 dev backend | Useful for NVIDIA RTX development and benchmarks | Candidate pending benchmark |
| WebRTC VAD default, Silero VAD accurate profile | Fast default + accurate fallback for noisy rooms | Candidate pending benchmark |
| Separate transcriber worker process | Keeps UI responsive, isolates model memory | Locked |
| Modular monolith with explicit ports/adapters | Clear replacement points for backends | Locked |
| No runtime network, zero-retention defaults | Privacy-first design | Locked |

## Constraints

- **Hard offline**: No runtime network for any purpose
- **No telemetry**: No analytics, crash uploads, usage metrics
- **No retained data**: No audio or transcript logs by default
- **Windows-first**: User-mode, no admin required
- **Legal conservative**: All dependencies and models are `candidate` or `verify before release` until explicit approval

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-04 after architecture lock and benchmark design*
