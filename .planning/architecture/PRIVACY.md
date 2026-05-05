# Privacy Architecture

Status: candidate privacy lock for Task 2. Implementation tests must enforce this document before MVP release.

## Continuation Note

Task 1 did not produce canonical GSD project artifacts because `gsd-sdk` remains shell-invisible. This privacy document is therefore a continuation artifact under `.planning/architecture/` until tooling recovery can generate `.planning/PROJECT.md` and related files.

## Non-Negotiable Runtime Policy

The application has a strict no runtime network policy.

Explicit guarantees:

- no runtime network
- no telemetry
- no cloud fallback
- no retained audio
- no retained transcripts by default
- redacted diagnostics only
- tests that fail if network calls are introduced

These phrases are policy requirements, not marketing copy.

## Data Classification

| Data | Examples | Default handling |
|---|---|---|
| Raw audio | Microphone PCM frames, speech segments | Data-in-motion only; no retained audio. |
| Raw transcript | ASR hypothesis before normalization | Data-in-motion only; no retained transcripts by default. |
| Final text | Post-processed text to paste | Passed to paste transport only; not logged by default. |
| Clipboard contents | Previous clipboard and paste text | Temporary paste operation state; restore where feasible; never diagnostic payload. |
| Window context | Focused app/window handle/title | Use minimal handle metadata; redact titles in diagnostics unless explicitly safe. |
| Model metadata | Local paths, checksums, model profile | Local-only settings and diagnostics may include redacted paths/checksums. |
| Settings | Hotkeys, paste mode, device, local model paths | Stored locally; no accounts or sync. |
| Diagnostics | Error categories, timings, counters | Redacted, local-only, no audio or transcript content. |

## Runtime Network Ban

The app must not perform runtime network activity for:

- ASR or post-processing.
- Model downloads, repairs, or metadata refreshes.
- Telemetry, analytics, crash uploads, or usage metrics.
- Account login, sync, license checks, or feature flags.
- Auto-update checks or installer update checks.
- Cloud fallback when local transcription fails.

Documentation may include source URLs for user-managed side-loading and license verification. Those URLs are release/documentation metadata, not runtime fetch targets.

## Retention Defaults

- Raw microphone frames are held only long enough to detect speech and submit the active segment to the worker process.
- Speech segments are released after transcription succeeds or fails.
- Raw ASR text is passed to `PostProcessor` and not logged by default.
- Final text is passed to `PasteController` and not logged by default.
- Diagnostics store event categories, redacted timing, backend/profile names, and error codes only.
- Future opt-in debug capture, if ever added, requires a separate explicit design and must not change the default no-retention posture.

## PrivacyGuard Responsibilities

`PrivacyGuard` owns enforcement hooks for:

- Startup policy validation.
- Activation authorization.
- Network API blocking in privacy tests.
- Diagnostic redaction.
- No-runtime-download checks in model and backend paths.
- Fail-closed behavior when privacy policy state is unknown.

Every module remains responsible for local correctness, but privacy enforcement is centralized so tests can target one policy surface.

## Diagnostics Redaction Rules

Allowed by default:

- Error category such as `missing_model`, `microphone_unavailable`, `worker_busy`, or `paste_failed`.
- Backend name such as `whisper.cpp` or `faster-whisper`.
- Model profile name and checksum status.
- Latency, queue depth, memory estimates, and boolean capability flags.

Forbidden by default:

- Raw audio bytes or derived replayable audio.
- Raw transcript text.
- Final pasted text.
- Clipboard contents.
- Full local file paths when a redacted basename or hash is enough.
- Full focused window titles if they may contain document names or user data.

## Required Tests

Privacy tests must fail if network calls are introduced. Later implementation should include tests that:

- Monkeypatch or block `socket`, HTTP clients, package download helpers, telemetry SDKs, and update-check clients during runtime flows.
- Exercise missing model and corrupt model paths and prove they return local errors without opening network sockets.
- Run transcription and paste flows with diagnostics enabled and assert no raw audio, transcript, pasted text, or clipboard contents appear in logs.
- Verify no cloud fallback path exists when the local backend fails.
- Verify settings contain no account, sync, telemetry, auto-update, or runtime download toggles.

## User Controls

- Hybrid activation is allowed: push-to-talk and toggle mode.
- Immediate paste is the default paste mode.
- Confirmation/edit-before-paste mode is supported as a user-selectable profile.
- Local model side-loading is user-managed and documented.
- Privacy-protecting defaults must not require user configuration.

## Release Privacy Constraints

- GitHub releases may publish source, docs, checksums, SBOM, and approved release assets.
- Installers and portable zips must run without runtime network access.
- Model bundles are allowed only if license review approves redistribution and checksums are published.
- No bundled dependency may silently add telemetry, update checks, or cloud fallback.
