# Offline Dictation Architecture

Status: candidate architecture lock for Task 2. Verify implementation details during later MVP and benchmark tasks.

## Continuation Note

Task 1 remains partially blocked: `gsd-sdk` remains shell-invisible after the documented recovery attempts. These architecture docs are authored as continuation artifacts under `.planning/architecture/` while `.planning/PROJECT.md`, `.planning/config.json`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, and `.planning/STATE.md` are still pending tooling recovery.

No production app code is introduced by this document set.

## Product Boundary

The app is a Windows-first, user-mode, fully offline desktop dictation tool for technical Spanglish. It listens only after user activation, transcribes with local models, applies deterministic post-processing, and pastes into the previously focused Windows app. It must not send audio, transcript text, model metadata, diagnostics, telemetry, or update checks to the network at runtime.

Out of scope for the architecture lock:

- Cloud ASR, paid APIs, accounts, sync, telemetry, auto-update, and runtime model downloads.
- Local LLM rewriting or generative assistant behavior.
- Production implementation files, packages, installers, bundled models, or binaries.

## Architectural Style

Use a modular monolith desktop process with explicit ports/adapters. The GUI shell, hotkey integration, audio capture, speech detection, post-processing, paste transport, privacy enforcement, settings, and diagnostics live in one deployable desktop application, while CPU/GPU ASR work runs in a separate transcriber worker process behind a narrow interface.

Reasons:

- Keeps the MVP installable and debuggable on Windows without service orchestration.
- Provides clear replacement points for ASR, VAD, model, paste, and post-processing backends.
- Isolates heavy transcription work from the Qt event loop so tray and status UI remain responsive.
- Makes privacy controls enforceable at module boundaries rather than relying on convention.

## Required Modules

| Module | Responsibility | Key Interfaces |
|---|---|---|
| `ShellIntegration` | Owns PySide6/Qt app lifecycle, tray menu, floating status panel, global hotkey registration, focus handoff, and user activation mode routing. | Activation source, status sink, settings observer |
| `AudioCapture` | Captures microphone audio with local device selection, frame sizing, sample-rate normalization, and bounded queues. | Audio source, device inventory |
| `SpeechDetector` | Converts audio frames into speech start/end events using VAD profiles. | VAD backend, segment emitter |
| `Transcriber` | Sends complete speech segments to a worker process and returns offline ASR hypotheses. | ASR backend, worker protocol |
| `ModelManager` | Tracks local model profiles, paths, checksums, hardware compatibility, and missing/corrupt model errors. | Model registry, profile resolver |
| `PostProcessor` | Applies deterministic Spanglish technical glossary, casing, punctuation, and paste-safe text cleanup. | Text normalization pipeline |
| `PasteController` | Pastes final text into the focused app through Win32 clipboard and `SendInput`, preserving clipboard where feasible. | Paste transport |
| `PrivacyGuard` | Enforces no-runtime-network policy, zero-retention defaults, diagnostic redaction, and test hooks for privacy invariants. | Privacy policy, network guard, log scrubber |
| `SettingsStore` | Persists local user preferences for hotkeys, activation mode, paste mode, model profile, device selection, and glossary path. | Settings repository |
| `Diagnostics` | Emits local-only status, counters, error categories, and redacted troubleshooting bundles without raw audio or transcript text. | Event bus subscriber, redacted logger |

## Dataflow

The locked user path is:

1. global hotkey
2. focused window capture
3. audio capture
4. VAD
5. speech segment
6. transcriber worker process
7. post-processing
8. paste controller
9. focused app

Status updates flow independently through an event bus to the tray and floating status panel.

Detailed sequence:

1. `ShellIntegration` registers the global hotkey and receives push-to-talk or toggle activation.
2. `ShellIntegration` captures the currently focused window handle before any panel interaction can steal focus.
3. `PrivacyGuard` checks the current runtime policy and denies activation if privacy invariants are violated.
4. `AudioCapture` opens the selected local microphone through WASAPI-compatible capture and emits fixed-duration PCM frames.
5. `SpeechDetector` receives frames, applies the selected VAD profile, and closes a speech segment on validated silence.
6. `Transcriber` places the speech segment onto a bounded worker-process queue.
7. The transcriber worker loads a local model selected by `ModelManager`, performs offline ASR, and returns text plus redacted timing metadata.
8. `PostProcessor` normalizes approved technical Spanglish terms without translation or meaning changes.
9. `PasteController` restores focus to the captured target where feasible, uses clipboard plus `SendInput`, and restores the prior clipboard when feasible.
10. `Diagnostics` and `ShellIntegration` receive event-bus updates such as Idle, Listening, Processing, Ready, Pasted, and Error.

## Stack Decisions

| Area | Decision | Rationale | Status |
|---|---|---|---|
| App language and shell | Python + PySide6/Qt shell | Best balance for Windows desktop UX, tray/topmost panel support, Python ASR ecosystem, and LGPL-friendly Qt binding option. | candidate |
| Native Windows integration | `pywin32`/`ctypes` | Direct access to `RegisterHotKey`, focus/window APIs, clipboard APIs, and `SendInput` without requiring admin privileges. | candidate |
| Audio capture | `sounddevice`/PortAudio/WASAPI | Cross-platform Python API with access to Windows WASAPI via PortAudio and simpler deployment than lower-level custom capture. | candidate |
| Default VAD | WebRTC VAD default | Fast, small, deterministic default for short dictation segments. | candidate |
| Accurate/noisy-room VAD | Silero VAD accurate/noisy-room profile | More tolerant model-based VAD for difficult rooms, gated behind profile choice and benchmark evidence. | candidate |
| Shipping ASR backend | whisper.cpp shipping backend | Portable CPU-first local inference with quantized multilingual Whisper-family models and no Python GPU stack requirement for users. | candidate |
| Dev/benchmark ASR backend | faster-whisper/CTranslate2 dev/benchmark backend | Useful for NVIDIA RTX development and benchmark comparison without becoming required for CPU-only users. | candidate |
| Worker isolation | Separate transcriber worker process | Keeps PySide6 event loop responsive and isolates model memory/lifetime from shell interactions. | candidate |
| Eventing | In-process event bus plus worker messages | Decouples status reporting from pipeline work and keeps tray/panel updates independent of ASR latency. | candidate |

## Fallback Stack Decisions

| Alternative | When to reconsider | Current decision |
|---|---|---|
| WPF/.NET shell | If native Windows UX and installer integration become more important than Python ASR convenience, or if PySide6 deployment proves unacceptable. | Documented fallback only. |
| Tauri shell | If a web/Rust footprint becomes preferred and native Windows integration remains reliable without cloud/update scope creep. | Documented fallback only. |
| PyAudio | If `sounddevice`/PortAudio cannot reliably capture target WASAPI devices. | Fallback only. |
| OpenVINO | If benchmarks show a strong CPU laptop advantage and licensing/release checks pass. | Future option only. |

## Concurrency and Boundaries

- The Qt main thread owns UI rendering, tray menu interaction, hotkey dispatch, and event-bus subscription.
- Audio capture runs outside the UI hot path and writes bounded PCM frame queues.
- VAD consumes audio frames and emits complete segments, never raw retained recordings.
- Transcription runs in a worker process with bounded input/output messages.
- The worker process receives local model paths only; it must not resolve URLs or download assets.
- `PasteController` executes on a controlled shell-side path because it depends on captured focus and clipboard state.
- `PrivacyGuard` is invoked before activation, before model access, before diagnostics emission, and in test fixtures that monkeypatch or block network-capable APIs.

## Error States

| Error | Owner | User-visible behavior | Privacy behavior |
|---|---|---|---|
| Missing microphone | `AudioCapture` | Status panel reports microphone unavailable. | No audio buffer exists. |
| Missing model | `ModelManager` | Prompt user to side-load documented local model. | No runtime download attempt. |
| Corrupt model | `ModelManager` | Report checksum mismatch. | No runtime repair/download attempt. |
| Busy worker | `Transcriber` | Show Processing or Busy and reject overlapping segment if queue is full. | Do not log segment contents. |
| Paste failure | `PasteController` | Show paste error with target app category if available. | Do not log pasted text. |
| Privacy violation | `PrivacyGuard` | Disable dictation path and surface policy error. | Fail closed. |

## Release Constraints

- The GitHub repository can contain source, docs, tests, license notices, manifests, and checksums.
- Model binaries must not enter git history.
- Release assets may include model bundles only after license and redistribution verification.
- CUDA/cuDNN redistribution is blocked until license review explicitly permits the exact packaging path.
- No installer or runtime path may perform network access for telemetry, update checks, model downloads, or cloud fallback.
