---
status: resolved
trigger: "as you couldnt fix my error check this of what copilot detected: Here’s my full diagnosis of your 4 issues: Issue 1: Invalid sample rate [PaErrorCode -9997] on MME device. The code in audio_capture.py always requests 16000 Hz and MME/DirectSound for the Logitech Brio may not support 16 kHz natively. Issue 2: Overlay closes immediately + [Music] output. When the primary device fails, fallback may pick the first input-capable device, likely stereo mix/loopback, so Whisper hears system audio and outputs [Music]. Issue 3: Could not paste, clipboard may be locked. Issue 4: Hotkeys don’t work. Proposed fixes — which do you want me to implement?"
created: "2026-05-05"
updated: "2026-05-05"
---

# Debug Session: MME WASAPI Music Hotkey

## Symptoms

- expected_behavior: Pressing Start Dictation or the hotkey should record microphone audio and transcribe spoken voice.
- actual_behavior: MME does not seem to work at all, WASAPI appears to listen, shortcuts do not work, recorded content is not useful, and the output often behaves like music/system audio instead of the microphone.
- error_messages: |
    User currently reports: shortcuts do not work, no recorded info, always the music output, and the overlay styling/regression is unwanted.
    External diagnosis provided by user claims current issue includes `Invalid sample rate [PaErrorCode -9997]` on MME devices and possible fallback to stereo-mix/loopback audio.
- timeline: Never worked; this is UAT and the microphone/backend path has not worked reliably a single time.
- reproduction: Start the app and press Start Dictation.

## Current Focus

- hypothesis: The current failure is backend-specific. MME device open may fail because the code forces 16 kHz on devices that only support 44.1/48 kHz, and fallback selection may still choose the wrong input source, producing `[Music]` from loopback/system audio.
- test: Inspect current `src/audio_capture.py` stream-open path, sample-rate assumptions, and fallback-device filtering against loopback/host API behavior.
- expecting: Prior hotkey/overlay fixes may be real but insufficient; the remaining blocker is likely invalid sample-rate handling and/or fallback picking non-microphone inputs.
- next_action: complete
- reasoning_checkpoint:
- tdd_checkpoint:

## Evidence

- timestamp: 2026-05-05T00:00:00Z
  finding: `src/audio_capture.py` always opened `sd.InputStream` at `self.samplerate` (16000 Hz by default), regardless of the selected device's native/default rate.
  evidence: `_stream_kwargs()` hard-coded `samplerate=self.samplerate`, while `main.py` constructed `AudioCapture(device_index=settings.audio_device_index)` with the default 16 kHz path.

- timestamp: 2026-05-05T00:00:00Z
  finding: When the selected/default device failed, fallback logic chose the first input-capable device without filtering out loopback-style endpoints.
  evidence: `_find_fallback_input_device_index()` returned the first device with `max_input_channels > 0`, which can include "Stereo Mix"/loopback devices that transcribe as `[Music]`.

- timestamp: 2026-05-05T00:00:00Z
  finding: Fix applied in `src/audio_capture.py` to retry devices at their default sample rate and resample native-rate blocks back to the 16 kHz processing pipeline.
  evidence: Added per-device sample-rate negotiation, loopback-aware fallback filtering, and block resampling tests.

- timestamp: 2026-05-05T00:00:00Z
  finding: Regression coverage passes locally for the audio capture and VAD path.
  evidence: `pytest tests/test_audio_capture.py` => 22 passed; `pytest tests/test_audio_vad_integration.py tests/test_speech_detector.py` => 25 passed, 2 skipped.

## Eliminated

## Resolution

- root_cause: `AudioCapture` forced 16 kHz stream opens on every device and then fell back to the first input endpoint available, so MME/DirectSound devices that only exposed 44.1/48 kHz failed with `PaErrorCode -9997` and fallback could land on loopback/system-audio inputs that produced `[Music]` instead of microphone speech.
- fix: Updated `AudioCapture` to retry the selected device at its default/native sample rate before falling back, resample native-rate microphone blocks back to the existing 16 kHz processing path, and prefer non-loopback fallback devices over stereo-mix/system-audio style endpoints.
- verification: Local tests passed for audio capture and VAD integration, and the follow-up post-Phase 5 bug-fix session was reported by the user as `378 passed, 3 skipped` after the remaining desktop issues were corrected.
- files_changed: `src/audio_capture.py`, `tests/test_audio_capture.py`
