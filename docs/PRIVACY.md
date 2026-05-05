# Privacy Statement

Spanglish Dictation is designed to keep your voice data on your machine.
This document states the privacy guarantees the application makes at runtime.

## Runtime guarantees

These guarantees are enforced by the `PrivacyGuard` module at application
startup and are verified by automated tests before every release:

- **no runtime network** — The application never opens network sockets for
  ASR, post-processing, model downloads, telemetry, updates, or any other
  purpose.  All transcription runs on local CPU or GPU.
- **no telemetry** — No analytics, no crash uploads, no usage metrics.
  No third-party telemetry SDKs are linked or loaded.
- **no cloud fallback** — Transcription failure returns a local error.
  There is no fallback path that sends audio to a remote service.
- **no retained audio** — Raw microphone frames and speech segments are
  held only in memory while a dictation segment is active.  They are
  released immediately after transcription succeeds or fails.
- **no retained transcripts by default** — Raw ASR output and final
  post-processed text pass through the application pipeline to the paste
  operation and are not written to disk or logged by default.
- **redacted local diagnostics only** — Diagnostics store event categories,
  backend/profile names, error codes, and timing.  They never store audio
  data, transcript text, pasted text, or clipboard contents.
- **tests fail if network calls are introduced** — Privacy regression tests
  monkeypatch `socket`, `urllib`, and Qt network APIs.  Any code change that
  introduces network activity causes those tests to fail.

## Data handling

| Data | Default handling |
|------|-----------------|
| Raw audio (microphone PCM frames) | Data-in-motion only — released after segment transcription |
| Raw transcript (ASR hypothesis) | Data-in-motion only — not retained by default |
| Final text (post-processed output) | Passed to paste transport only — not logged by default |
| Clipboard contents | Temporary paste operation state — restored where feasible |
| Window context | Minimal handle metadata — titles redacted in diagnostics unless safe |
| Model metadata | Local paths and checksums — stored in local settings only |
| Settings | Hotkeys, device index, model profile — local storage, no sync or accounts |

## Model side-loading

Model files are user-managed.  The app never downloads model files at
runtime.  See [Model side-loading guide](MODEL-SIDELOADING.md) for
download URLs, checksums, and hardware profile recommendations.

## Repository

Source code, documentation, and release artifacts are published on GitHub.
No model binaries, GPU DLLs, or user data are committed to the repository.

## Changes to this statement

If the privacy guarantees change in a future release (e.g., an opt-in
debug capture mode), those changes require:

1. A separate, explicit design review.
2. The feature must be opt-in only — defaults remain no-retention.
3. The privacy statement is updated before the release is published.
4. Automated tests enforce the new constraints.

The non-negotiable runtime policy (no network, no telemetry, no cloud
fallback) does not change without a major architecture review.
