---
status: resolved
trigger: "User restarted the PC and now dictation startup repeatedly fails with sounddevice/PortAudio errors: device 1 opens with invalid channel count PaErrorCode -9998, fallback to default then fails querying device -1. Qt focus/layered-window warnings also appear."
created: "2026-05-05"
updated: "2026-05-05"
---

# Debug Session: Dictation Audio Capture Error

## Symptoms

- expected_behavior: Dictation should start audio capture and begin listening normally.
- actual_behavior: Dictation fails to start audio capture after opening the selected input device fails and fallback to default input also fails.
- error_messages: |
    requestActivate() called for QWidgetWindow(...) which has Qt::WindowDoesNotAcceptFocus set.
    Failed to open stream on device 1: Error opening InputStream: Invalid number of channels [PaErrorCode -9998]. Falling back to default.
    Failed to start audio capture: Error querying device -1
    sounddevice.PortAudioError: Error opening InputStream: Invalid number of channels [PaErrorCode -9998]
    sounddevice.PortAudioError: Error querying device -1
    UpdateLayeredWindowIndirect failed ... (El parametro no es correcto.)
- timeline: Started after restarting the PC; dictation worked before restart.
- reproduction: Start dictation in the app.

## Current Focus

- hypothesis: Confirmed. Saved/default PortAudio device can be stale or invalid after reboot, and fallback relied on the same invalid default instead of selecting an explicit input-capable device.
- test: Added mocked sounddevice regressions for stale selected devices, invalid default device `-1`, and failed startup cleanup.
- expecting: AudioCapture should recover by opening an explicit input-capable device and should not leave background capture state running after stream-open failures.
- next_action: complete
- reasoning_checkpoint:
- tdd_checkpoint:

## Evidence

- timestamp: 2026-05-05T18:06:38.2947687-06:00
  observation: `src/audio_capture.py` opened the configured `device_index` first, then retried `sd.InputStream(...)` without a device. When PortAudio's default input maps to `-1`, that retry reproduces `Error querying device -1`.
  source: code inspection, `src/audio_capture.py:79-101`
- timestamp: 2026-05-05T18:06:38.2947687-06:00
  observation: The selected device comes from persisted settings at app startup, so a device index saved before reboot can point at a different/no-longer-input-capable endpoint after enumeration changes.
  source: code inspection, `src/main.py:129-135`
- timestamp: 2026-05-05T18:06:38.2947687-06:00
  observation: Regression coverage now confirms fallback from an invalid default to explicit input device index `0`, fallback from stale selected device `99` to index `0`, and cleanup when no usable input can be opened.
  source: `tests/test_audio_capture.py`

## Eliminated

## Resolution

- root_cause: AudioCapture's fallback retried PortAudio's default input device; after reboot that default resolved to invalid device `-1`, while a stale saved device index could also point at a non-input-capable endpoint.
- fix: AudioCapture now opens streams through a helper that retries with an explicit input-capable device from `sd.query_devices()` and only starts the consumer thread after the stream is created.
- verification: `python -m pytest tests/test_audio_capture.py` passed (17 tests); `python -m pytest` passed (369 passed, 3 skipped).
- files_changed: `src/audio_capture.py`, `tests/test_audio_capture.py`
