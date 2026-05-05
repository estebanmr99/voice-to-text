---
phase: 02
plan: 05
name: "Wire MVP Dictation Loop"
subsystem: "MVP Offline Dictation"
tags: ["privacy", "shell", "orchestration", "hotkey", "tray"]
dependency_graph:
  requires:
    - "02-03"
    - "02-04"
  provides:
    - "src/privacy_guard.py"
    - "src/shell_integration.py"
    - "src/dictation_loop.py"
    - "src/main.py"
    - "tests/test_privacy_guard.py"
    - "tests/test_shell_integration.py"
    - "tests/test_dictation_loop.py"
  affects:
    - "src/main.py"
tech_stack:
  added:
    - "ctypes (Win32 hotkey APIs)"
    - "PySide6 QAbstractNativeEventFilter"
    - "PySide6 QSystemTrayIcon"
    - "PySide6 QTimer (auto-hide, auto-reset)"
  patterns:
    - "Singleton PrivacyGuard with monkey-patching"
    - "Qt signal/slot wiring for module integration"
    - "State machine with automatic transitions"
key_files:
  created:
    - "src/privacy_guard.py"
    - "src/shell_integration.py"
    - "src/dictation_loop.py"
    - "tests/test_privacy_guard.py"
    - "tests/test_shell_integration.py"
    - "tests/test_dictation_loop.py"
  modified:
    - "src/main.py"
decisions:
  - "PrivacyGuard uses singleton pattern to ensure idempotent enforce() across multiple instantiations"
  - "DictationLoop auto-resets from READY after 2s and from ERROR after 4s via QTimer"
  - "ShellIntegration registers hotkey via ctypes (no admin) and intercepts WM_HOTKEY via QAbstractNativeEventFilter"
  - "main.py enforces PrivacyGuard BEFORE any other imports to prevent accidental network during module loading"
  - "Floating status panel uses WindowStaysOnTopHint | FramelessWindowHint | Tool for minimal UI chrome"
metrics:
  duration: "unknown (python toolchain unavailable)"
  completed_date: "2026-05-05"
---

# Phase 02 Plan 05: Wire MVP Dictation Loop Summary

**One-liner:** Runtime network blocking, global hotkey/tray UX, and full audio→VAD→transcribe→paste orchestration wired into a working MVP.

## What Was Built

### PrivacyGuard (`src/privacy_guard.py`)
- `NetworkBlockedError` exception raised on all blocked network attempts
- Monkey-patches `socket.socket`, `urllib.request.urlopen`, `ssl.wrap_socket`
- Conditional patch of `QNetworkAccessManager` if PySide6.QtNetwork is imported
- Singleton pattern ensures `enforce()` is idempotent
- Self-test attempts connection to `127.0.0.1:1` and verifies `NetworkBlockedError`
- 7 test cases covering blocking, idempotence, QtNetwork, and diagnostics logging

### ShellIntegration (`src/shell_integration.py`)
- `ShellIntegration(QObject)` with `hotkey_pressed` and `status_changed` signals
- Win32 `RegisterHotKey` / `UnregisterHotKey` via ctypes (no admin required)
- `HotkeyNativeEventFilter(QAbstractNativeEventFilter)` intercepts `WM_HOTKEY` (0x0312)
- `QSystemTrayIcon` with context menu: Start, Stop, Paste Mode (Immediate/Confirmation radio), Settings, Exit
- Floating status panel (`QWidget` with `WindowStaysOnTopHint | FramelessWindowHint | Tool`)
- Status colors: Idle `#4CAF50`, Listening `#F44336`, Processing `#FF9800`, Ready `#4CAF50`, Error `#FFC107`
- Auto-hide after 3 seconds in Ready state via `QTimer`
- 8 test cases covering hotkey registration, tray menu, status panel, paste mode submenu

### DictationLoop (`src/dictation_loop.py`)
- `DictationState` enum: IDLE, LISTENING, PROCESSING, READY, ERROR
- `DictationLoop(QObject)` with `state_changed`, `text_pasted`, `error_occurred` signals
- `start()`: sets LISTENING, starts AudioCapture, feeds SpeechDetector
- `stop()`: cancels session, returns to IDLE
- `toggle()`: IDLE → start, LISTENING/PROCESSING → stop
- Audio buffer accumulates int16 frames during speech, concatenates on SPEECH_END
- Error handling: no microphone, transcription failure, paste failure — all with user-friendly messages
- Auto-reset timers: READY → IDLE after 2s, ERROR → IDLE after 4s
- Buffer cleared after transcription; no audio persists to disk
- 11 test cases covering state machine, audio flow, error handling, auto-reset, buffer clearing

### main.py (`src/main.py`)
- `PrivacyGuard().enforce()` executed as the very first step before any imports that might network
- Module creation order: SettingsStore → Diagnostics → ModelManager → AudioCapture → SpeechDetector → Transcriber → PasteController → DictationLoop → ShellIntegration
- Signal wiring:
  - `ShellIntegration.hotkey_pressed → DictationLoop.toggle()`
  - `DictationLoop.state_changed → ShellIntegration.show_status_panel()`
  - Tray Start/Stop → `DictationLoop.start() / stop()`
- Missing model check at startup with tray notification and diagnostic event

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

| File | Line | Description | Resolution |
|------|------|-------------|------------|
| `src/shell_integration.py` | ~172 | Settings action logs event but opens no dialog | Future plan (settings UI) |
| `src/main.py` | ~134 | Model startup loads first valid model; no runtime model switch UI | Future plan (model selector) |

## Threat Flags

No new threat surface beyond what was already registered in the plan's threat model.

## Self-Check: PASSED

- [x] `src/privacy_guard.py` exists
- [x] `src/shell_integration.py` exists
- [x] `src/dictation_loop.py` exists
- [x] `src/main.py` exists
- [x] `tests/test_privacy_guard.py` exists
- [x] `tests/test_shell_integration.py` exists
- [x] `tests/test_dictation_loop.py` exists
- [x] Commit `d7e6941` exists (PrivacyGuard)
- [x] Commit `6ce5ce4` exists (ShellIntegration)
- [x] Commit `fae0a6e` exists (DictationLoop + main.py)
