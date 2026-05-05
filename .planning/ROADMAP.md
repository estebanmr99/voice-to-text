# Roadmap

## Phase Overview

| # | Phase | Goal | Requirements | Status |
|---|-------|------|--------------|--------|
| 1 | Planning & Architecture | Lock architecture, privacy, licensing, benchmark design | PRIV-01, PRIV-02, MOD-01, MOD-02, TEST-01, TEST-02 | In Progress |
| 2 | MVP Offline Dictation | 5/5 | Complete | |
| 3 | Model Profiles | 3/3 | Complete   | 2026-05-05 |
| 4 | GUI & Tray Polish | 3/3 | Complete   | 2026-05-05 |
| 5 | Spanglish Glossary | Deterministic technical term normalization | CORE-05 | In Progress |
| 6 | Packaging & Release | Windows installer, SBOM, license notices, GitHub release | REL-01–02 | Blocked |

---

## Phase 1: Planning & Architecture

**Goal:** Define the complete architecture, privacy policy, license matrix, and benchmark plan before writing production code.

**Requirements:**
- PRIV-01: Runtime offline guarantee
- PRIV-02: Zero-retention defaults
- MOD-01: Backend-switchable architecture
- MOD-02: Worker process isolation
- TEST-01: Privacy tests for network blocking
- TEST-02: Missing model offline behavior

**Success Criteria:**
1. Architecture docs define all 10 modules and their interfaces
2. Privacy doc states non-negotiable runtime policy
3. License matrix marks all components as candidate/verify/blocked
4. Benchmark plan includes fixture definitions and candidate matrix
5. No production code created during this phase

**Plans:**
- 01-01: Recover GSD tooling and generate planning artifacts
- 01-02: Lock architecture, privacy, and licensing decisions
- 01-03: Design ASR/VAD benchmark plan and fixtures

---

## Phase 2: MVP Offline Dictation

**Goal:** Build the smallest working dictation loop that can activate, capture, transcribe, and paste.

**Requirements:**
- CORE-01: Global hotkey activation
- CORE-02: Microphone audio capture
- CORE-03: VAD speech detection
- CORE-04: Offline transcription
- CORE-06: Paste into focused app
- CORE-07: Clipboard restore
- CORE-09: No admin required

**Success Criteria:**
1. Push-to-talk records one utterance and pastes into Notepad
2. Toggle mode starts/stops without getting stuck
3. Clipboard previous text restored after paste
4. Privacy test passes (no network calls)
5. App runs on Windows user account

**Plans:** 4/5 plans executed

**Wave 1** *(no dependencies)*
- [x] 02-01: Scaffold Python project with PySide6 shell — `pyproject.toml`, `SettingsStore`, `Diagnostics`, tray icon

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 02-02: Implement AudioCapture + SpeechDetector (WebRTC VAD) — `sounddevice` capture, `webrtcvad` detection
- [x] 02-04: Implement PasteController with Win32 clipboard/SendInput — `SendInput` primary, clipboard fallback+restore

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 02-03: Integrate whisper.cpp transcriber worker — `pywhispercpp` in `multiprocessing.Process`, `ModelManager`

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 02-05: Wire dictation loop and add error states — `DictationLoop`, `ShellIntegration`, `PrivacyGuard`, hotkey wiring

**Cross-cutting constraints:**
- No runtime network (PRIV-01) — enforced by `PrivacyGuard` in 02-05
- No admin required (CORE-09) — `RegisterHotKey` without elevation, user-mode clipboard access
- Zero retention (PRIV-02) — audio buffers in-memory only, cleared after transcription

---

## Phase 3: Model Profiles

**Goal:** Add local model management with hardware-specific profiles.

**Requirements:**
- PROF-01: CPU portable profile
- PROF-02: CPU high-accuracy profile
- PROF-03: NVIDIA dev profile
- TEST-02: Missing/corrupt model offline behavior

**Success Criteria:**
1. Profile selection maps hardware to expected backend
2. Missing model returns local error with side-load guidance
3. Corrupt model fails checksum validation
4. Model registry includes source URL, license, checksum, size

**Plans:**3/3 plans complete
- 03-01: Implement ModelManager with local registry
- 03-02: Add profile resolution and hardware detection
- 03-03: Integrate profile switching into UI

---

## Phase 4: GUI & Tray Polish

**Goal:** Polish the system tray UX, floating panel, settings, and confirmation mode.

**Requirements:**
- GUI-01: Tray menu with all actions
- GUI-02: Confirmation/edit-before-paste mode
- GUI-03: Settings panel for all preferences
- CORE-08: Tray icon and floating status panel

**Success Criteria:**
1. Tray exposes Start/Stop, Settings, Profile, Paste Mode, Exit
2. Floating panel shows Idle/Listening/Processing/Ready/Error
3. Confirmation mode allows edit/accept/cancel
4. Immediate paste remains default
5. UI stays responsive during transcription

**Status:** Complete — 3/3 plans executed

**Plans:**3/3 plans complete
- 04-01: Settings Dialog — comprehensive PySide6 dialog for all preferences, wired to tray
- 04-02: Confirmation Mode Flow — editable confirmation dialog before paste, wired to dictation loop
- 04-03: Tray & Status Panel Polish — grouped menu, state-aware actions, dismissible panel with profile info

**Wave Structure**
- **Wave 1** *(no dependencies)*
  - [x] 04-01: Settings Dialog
  - [x] 04-02: Confirmation Mode Flow
- **Wave 2** *(blocked on Wave 1 completion)*
  - [x] 04-03: Tray & Status Panel Polish

---

## Phase 5: Spanglish Glossary

**Goal:** Implement deterministic post-processing for technical Spanglish terms.

**Requirements:**
- CORE-05: Deterministic Spanglish technical glossary

**Success Criteria:**
1. `mergear el pr` → `mergear el PR`
2. `pushea el hotfix` remains unchanged
3. Accents and Spanish framing preserved
4. No translation or meaning change
5. User-editable glossary with import/export

**Plans:** 3 plans

**Wave 1** *(no dependencies)*
- [x] 05-01: Core PostProcessor, GlossaryStore, default glossary, and dictation loop wiring
- [x] 05-03: Fixture-driven tests for all success criteria and edge cases

**Wave 2** *(depends on Wave 1)*
- [x] 05-02: User glossary import/export UI and persistence

---

## Phase 6: Packaging & Release

**Goal:** Create Windows release artifacts with proper licensing and documentation.

**Requirements:**
- REL-01: Open source, legal for GitHub
- REL-02: SBOM and license notices

**Success Criteria:**
1. Portable zip installs and runs without admin
2. Offline smoke test passes with network disabled
3. LICENSES/ covers every dependency
4. SBOM generated and published
5. GitHub release docs explain model side-loading
6. No bundled models or CUDA DLLs without approval

**Plans:** 4 plans

**Wave 1** *(no dependencies)*
- [x] 06-01: Portable packaging foundation and offline smoke checks
- [ ] 06-02: SBOM and conservative license bundle generation

**Wave 2** *(depends on Wave 1)*
- [ ] 06-03: GitHub-ready release documentation, model side-loading, privacy, and MIT license

**Wave 3** *(depends on Wave 2)*
- [ ] 06-04: GitHub release workflow, checksums, and artifact verifier

### Phase 7: 5

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 6
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd-plan-phase 7 to break down)

---

## Traceability

| Requirement | Phase | Plan |
|-------------|-------|------|
| PRIV-01 | 1 | 01-02 |
| PRIV-02 | 1 | 01-02 |
| CORE-01 | 2 | 02-05 |
| CORE-02 | 2 | 02-02 |
| CORE-03 | 2 | 02-02 |
| CORE-04 | 2 | 02-03 |
| CORE-05 | 5 | 05-01 |
| CORE-06 | 2 | 02-04 |
| CORE-07 | 2 | 02-04 |
| CORE-08 | 4 | 04-03 |
| CORE-09 | 2 | 02-01 |
| MOD-01 | 1 | 01-02 |
| MOD-02 | 1 | 01-02 |
| PROF-01 | 3 | 03-01 |
| PROF-02 | 3 | 03-01 |
| PROF-03 | 3 | 03-01 |
| GUI-01 | 4 | 04-03 |
| GUI-02 | 4 | 04-02 |
| GUI-03 | 4 | 04-01 |
| TEST-01 | 1 | 01-02 |
| TEST-02 | 1 | 01-03 |
| REL-01 | 6 | 06-03 |
| REL-02 | 6 | 06-02 |
