# Backend Interfaces

Status: candidate interface contract for Task 2. These are architectural ports, not production code.

## Continuation Note

`gsd-sdk` remains shell-invisible, so these interface contracts are continuation artifacts under `.planning/architecture/` while the canonical generated GSD files remain pending tooling recovery.

## Interface Principles

- Each backend is replaceable without changing the user-facing dictation loop.
- Interfaces exchange local data only: local model paths, PCM frames, segment metadata, redacted diagnostics, settings values, and final text.
- Interfaces must not accept URLs for runtime model resolution.
- Interface implementations must be testable with network calls blocked.
- Raw audio and raw transcripts are data-in-motion only unless the user explicitly enables a future debug capture mode outside the default privacy contract.

## ASR / Transcriber Backend

Purpose: convert a complete speech segment into candidate text using a local model.

Required operations:

- `load_model(local_model_ref, runtime_options)` validates local path, checksum status, backend compatibility, and hardware profile.
- `transcribe(segment_ref, language_hints, glossary_hints)` returns text, confidence/timing metadata where available, and redacted performance counters.
- `unload()` releases model resources.
- `health()` returns readiness without contacting a network.

Candidate adapters:

- `WhisperCppTranscriber` for the shipping CPU backend.
- `FasterWhisperTranscriber` for dev/benchmark NVIDIA profiles.
- `ReferenceWhisperTranscriber` for local development baselines only, not a shipping default.

Contract constraints:

- No cloud fallback.
- No runtime model download.
- No raw transcript logging by default.
- Worker process failures return categorized errors to the shell instead of crashing the UI.

## VAD / Speech Detector Backend

Purpose: classify audio frames and emit speech segment boundaries.

Required operations:

- `configure(profile)` selects aggressiveness, sample rate, frame duration, and silence thresholds.
- `accept_frame(pcm_frame)` returns speech/non-speech decision metadata.
- `flush()` closes any active segment on stop/toggle release.
- `reset()` clears internal state between activations.

Candidate adapters:

- `WebRtcVadDetector` as the default low-latency profile.
- `SileroVadDetector` as accurate/noisy-room profile after benchmark validation.

Contract constraints:

- Input frames are normalized PCM from `AudioCapture`.
- Segment metadata may include timings, but not persisted raw audio by default.

## Model Manager Interface

Purpose: resolve local models and hardware profiles without runtime downloads.

Required operations:

- `list_profiles()` returns CPU Portable, CPU High Accuracy, NVIDIA Dev, and Reference Baseline candidates when configured.
- `resolve_profile(settings, hardware_info)` returns an explicit local model requirement.
- `validate_model(local_model_ref)` verifies existence, checksum, size, license metadata, and backend compatibility.
- `describe_missing_model(local_model_ref)` returns local side-load instructions without opening a network path.

Contract constraints:

- Model registry entries include source URL for documentation, but source URLs are not runtime fetch targets.
- Missing or corrupt models fail closed.
- CUDA/cuDNN-dependent profiles remain optional and blocked for redistribution until license approval.

## Paste Transport Interface

Purpose: insert text into the previously focused app.

Required operations:

- `capture_target()` records focused window identity before activation UI changes focus.
- `paste_text(target_ref, text, mode)` executes immediate paste or confirmation-accepted paste.
- `restore_clipboard(previous_clipboard_ref)` restores prior clipboard contents where feasible.
- `report_capability(target_ref)` returns best-effort app/window metadata for diagnostics.

Candidate adapter:

- `Win32ClipboardSendInputPasteTransport` using clipboard APIs and `SendInput`.

Contract constraints:

- Do not persist pasted text in diagnostics.
- Confirmation/edit-before-paste mode must require user acceptance before paste.
- Immediate paste remains the default mode.

## Post-Processing Interface

Purpose: deterministically normalize technical Spanglish without changing meaning.

Required operations:

- `normalize(transcript, profile, glossary)` returns final text and applied rule IDs.
- `validate_glossary(glossary_ref)` checks local glossary schema and casing rules.
- `preview(transcript, glossary)` supports confirmation mode review.

Contract constraints:

- No cloud or local LLM rewriting.
- No translation of Spanglish into English-only or Spanish-only text.
- Logs may include rule IDs, but not raw before/after transcript text by default.

## Audio Capture Interface

Purpose: enumerate local capture devices and emit normalized frames.

Required operations:

- `list_devices()` returns local microphone devices and default selection metadata.
- `open(device_id, format)` starts local capture.
- `read_frame()` returns bounded PCM frames compatible with VAD.
- `close()` releases the device.

Candidate adapter:

- `SoundDeviceWasapiCapture` over `sounddevice`/PortAudio/WASAPI.

Contract constraints:

- Capture starts only after activation.
- Captured frames are not retained after segment processing by default.
- Device errors are categorized without raw audio dumps.

## Privacy Guard Interface

Purpose: centralize enforcement of offline and retention policy.

Required operations:

- `assert_runtime_offline()` verifies runtime networking is disabled or blocked by test hooks.
- `authorize_activation(context)` gates recording on privacy policy state.
- `scrub_diagnostic(event)` redacts audio, transcript, clipboard, path, and window-title sensitive content.
- `register_network_test_hooks()` supports tests that fail on introduced socket, HTTP, telemetry, or download calls.

Contract constraints:

- Fail closed on policy uncertainty.
- No telemetry, no cloud fallback, no retained audio, and no retained transcripts by default.

## Settings Store Interface

Purpose: persist local settings without accounts or sync.

Required operations:

- `load()` reads local settings with safe defaults.
- `save(settings)` writes local settings atomically.
- `watch(callback)` notifies shell modules of local preference changes.
- `reset_to_defaults()` restores privacy-preserving defaults.

Settings domains:

- Hotkeys and hybrid activation mode.
- Immediate paste or confirmation/edit-before-paste mode.
- Local model profile and model path references.
- Audio device selection.
- VAD profile.
- Local glossary path.
- Diagnostics verbosity with redaction always on.

Contract constraints:

- No account identity, sync endpoint, cloud backup, or telemetry preference exists.
- Defaults preserve no-runtime-network and zero-retention behavior.
