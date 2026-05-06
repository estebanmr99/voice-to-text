# Install Guide

Install and run Spanglish Dictation on Windows without admin rights or runtime network access.

## Windows prerequisites

- Windows 10 or Windows 11 (64-bit)
- A microphone that works in normal Windows apps
- A local Whisper model already side-loaded into `models/`
- Optional: NVIDIA GPU only if you are intentionally testing the dev-only faster-whisper path

No account, cloud service, admin install, or runtime download is required.

## 1. Download the portable zip

1. Open the project's [GitHub Releases](https://github.com/estebanmr99/voice-to-text/releases) page.
2. Download `spanglish-dictation-portable-<version>.zip`.
3. Optionally download `SHA256SUMS.txt` and `sbom.cdx.json` from the same release for verification.

## 2. Extract the portable zip

1. Right-click the portable zip.
2. Choose **Extract All...**.
3. Extract it to any user-writable folder such as `C:\Users\<you>\Apps\SpanglishDictation`.

The portable zip is designed for user-mode execution. Do not place it under `C:\Program Files` unless you intentionally want elevated write restrictions.

## 3. Side-load a model into `models/`

1. Follow [Model side-loading](MODEL-SIDELOADING.md).
2. Place at least one supported model file in the extracted app's `models/` directory.
3. Keep model filenames exactly as documented, for example `ggml-base.bin`.

The app never downloads models at runtime. If `models/` is empty, transcription cannot start.

## 4. First launch

1. Run `spanglish-dictation.exe` from the extracted folder.
2. Allow the tray icon and status panel to appear.
3. Open **Settings** from the tray if you need to confirm microphone, model profile, or paste behavior.
4. Verify the selected model profile matches the file you placed in `models/`.

## 5. Start dictation

- Use the configured global **hotkey** for push-to-talk dictation.
- If enabled, **toggle mode** starts and stops continuous dictation without holding the key.
- If enabled, confirmation mode lets you edit text before paste.

The expected first-run flow is: launch app → confirm model/profile → focus a text field in another Windows app → press the hotkey → speak → release hotkey or stop toggle mode → review pasted text.

## 6. Settings, logs, and local data

- **Settings live** in local app data for the current Windows user.
- **Logs live** locally on disk and contain redacted diagnostics only.
- Audio and transcripts are not retained by default beyond active dictation flow.

See [Privacy](PRIVACY.md) for the full offline and no-telemetry guarantees.

## Troubleshooting

- No transcription result: confirm a model file exists in `models/` and the selected profile matches it.
- Hotkey does nothing: check whether another application is already consuming that shortcut, then rebind it in Settings.
- No tray icon: relaunch the app from a normal user shell and verify Windows did not hide the tray icon.
- Packaging or publish questions: see [Release Guide](RELEASE.md).
