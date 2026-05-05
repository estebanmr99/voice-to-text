# Requirements

## v1 Requirements

### Privacy & Security

- [ ] **PRIV-01**: App must never make runtime network calls for ASR, telemetry, model downloads, updates, or any purpose
- [ ] **PRIV-02**: No retained audio or transcripts by default; diagnostics are redacted and local-only
- [ ] **TEST-01**: Privacy tests must fail if network calls (socket, HTTP, telemetry, download) are introduced
- [ ] **TEST-02**: Missing or corrupt local model paths return local errors without network attempts

### Core Dictation

- [ ] **CORE-01**: Activate dictation via global hotkey with push-to-talk and toggle modes
- [ ] **CORE-02**: Capture microphone audio with local device selection, WASAPI-compatible backend
- [ ] **CORE-03**: Detect speech start/end using VAD with selectable profiles (WebRTC default, Silero accurate)
- [ ] **CORE-04**: Transcribe offline using local quantized Whisper models via whisper.cpp or faster-whisper
- [ ] **CORE-05**: Post-process transcripts with deterministic Spanglish technical glossary (no LLM rewriting)
- [ ] **CORE-06**: Paste final text into focused Windows app via clipboard + SendInput
- [ ] **CORE-07**: Preserve and restore previous clipboard contents where feasible
- [ ] **CORE-08**: Show status via system tray icon and floating topmost panel
- [ ] **CORE-09**: Run without admin rights for normal use

### Architecture

- [ ] **MOD-01**: Backend-switchable architecture with explicit ports/adapters for ASR, VAD, paste, post-processing
- [ ] **MOD-02**: Separate transcriber worker process to keep UI responsive and isolate model memory

### Model Profiles

- [ ] **PROF-01**: CPU portable profile with whisper.cpp quantized model for Intel/AMD laptops without GPU
- [ ] **PROF-02**: CPU high-accuracy profile with larger whisper.cpp quantized model
- [ ] **PROF-03**: NVIDIA dev profile with faster-whisper/CTranslate2 for RTX development/benchmark

### GUI & UX

- [ ] **GUI-01**: Tray menu exposes Start/Stop, Settings, Profile, Paste Mode, Exit
- [ ] **GUI-02**: Confirmation/edit-before-paste mode as user-selectable option (immediate paste remains default)
- [ ] **GUI-03**: Settings panel for hotkeys, audio device, model profile, VAD profile, glossary path

### Release

- [ ] **REL-01**: Open source project, legal for GitHub, cloneable/installable without cloud services or paid APIs
- [ ] **REL-02**: SBOM and license notices for all runtime dependencies and model assets

## v2 Requirements (Deferred)

- Local LLM-powered rewriting assistant (beyond deterministic glossary)
- macOS/Linux support
- Auto-update mechanism
- Cloud sync or account system
- In-app runtime model downloads

## Out of Scope

- Cloud ASR, paid APIs, accounts, sync — violates offline guarantee
- Telemetry, analytics, crash uploads — violates privacy policy
- Local LLM generative assistant — scope creep for v1
- Model binaries in git history — legal/licensing constraint
- CUDA/cuDNN redistribution — blocked until explicit license approval
- Windows admin-required installation — user-mode only

## Traceability

| REQ-ID | Description | Phase | Plan | Status |
|--------|-------------|-------|------|--------|
| PRIV-01 | No runtime network | 1 | 01-02 | Defined |
| PRIV-02 | Zero-retention defaults | 1 | 01-02 | Defined |
| TEST-01 | Network-blocking privacy tests | 1 | 01-02 | Defined |
| TEST-02 | Missing model offline behavior | 1 | 01-03 | Defined |
| CORE-01 | Global hotkey activation | 2 | 02-05 | Defined |
| CORE-02 | Microphone capture | 2 | 02-02 | Defined |
| CORE-03 | VAD speech detection | 2 | 02-02 | Defined |
| CORE-04 | Offline transcription | 2 | 02-03 | Defined |
| CORE-05 | Spanglish glossary | 5 | 05-01 | Defined |
| CORE-06 | Paste into focused app | 2 | 02-04 | Defined |
| CORE-07 | Clipboard restore | 2 | 02-04 | Defined |
| CORE-08 | Tray + floating panel | 4 | 04-02 | Defined |
| CORE-09 | No admin required | 2 | 02-01 | Defined |
| MOD-01 | Backend-switchable architecture | 1 | 01-02 | Defined |
| MOD-02 | Worker process isolation | 1 | 01-02 | Defined |
| PROF-01 | CPU portable profile | 3 | 03-01 | Defined |
| PROF-02 | CPU high-accuracy profile | 3 | 03-01 | Defined |
| PROF-03 | NVIDIA dev profile | 3 | 03-01 | Defined |
| GUI-01 | Tray menu | 4 | 04-01 | Defined |
| GUI-02 | Confirmation mode | 4 | 04-04 | Defined |
| GUI-03 | Settings panel | 4 | 04-03 | Defined |
| REL-01 | Open source / GitHub legal | 6 | 06-03 | Defined |
| REL-02 | SBOM + license notices | 6 | 06-02 | Defined |
