# Windows Offline Spanglish Dictation

Turn technical Spanglish speech into pasted text — fully offline.

## What it does

Spanglish Dictation captures microphone audio, detects speech segments with
VAD, transcribes locally using quantized Whisper models via whisper.cpp, and
pastes the result into your active Windows application.  It runs entirely on
your machine with **no runtime network access**.

Key features:

- Push-to-talk dictation with global hotkey
- Toggle mode for hands-free continuous dictation
- Editable confirmation-before-paste mode (optional)
- System tray with model profile switching, settings, and status panel
- Deterministic Spanglish technical glossary normalization (PR → PR, API → API)

## Privacy guarantees

- **fully offline** — no cloud ASR, no API calls, no account needed
- **No telemetry** — no analytics, no crash uploads, no usage metrics
- **No runtime model downloads** — you side-load your own models; the app never fetches them
- **No retained audio** — raw microphone data is held only while transcribing
- **No retained transcripts by default** — text passes through to paste, not storage
- **Redacted local diagnostics only** — event categories and timings, never audio or text content

## Install from portable zip

1. Download the portable zip from [GitHub Releases](https://github.com/estebanmr99/voice-to-text/releases).
2. Extract to any folder (no admin rights required).
3. Side-load at least one Whisper model (see [Model side-loading](docs/MODEL-SIDELOADING.md)).
4. Run `spanglish-dictation.exe`.

The canonical notes for the first public ship are in [docs/releases/v0.1.0.md](docs/releases/v0.1.0.md).

Need the full first-run walkthrough? See the [Install guide](docs/INSTALL.md).

The portable zip includes the app executable, data assets, release
documentation, licence notices, and an SBOM.  Model binaries and
CUDA/cuDNN DLLs are **not** included.

## Model side-loading

Models must be side-loaded before first use.  See the
[model side-loading guide](docs/MODEL-SIDELOADING.md) for
download URLs, checksums, and hardware profile recommendations.

The app ships with a model registry that drives model selection and
fallback.  You choose which profiles to support by placing the
corresponding model files in the `models/` directory.

## Docs

- [Install guide](docs/INSTALL.md)
- [Release guide](docs/RELEASE.md)
- [Privacy policy](docs/PRIVACY.md)
- [Model side-loading](docs/MODEL-SIDELOADING.md)

## Development

```powershell
# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install runtime + dev dependencies
pip install -e ".[dev]"
# Optional: VAD backend (requires Visual C++ Build Tools)
pip install ".[vad]"

# Run tests
python -m pytest tests -q

# Run the app
python src/main.py
```

### Release tooling (optional)

```powershell
pip install ".[release]"
```

## Release artifacts

Every release includes:

| Artifact | Description |
|----------|-------------|
| `spanglish-dictation-portable-*.zip` | Portable application bundle |
| `sbom.cdx.json` | CycloneDX software bill of materials |
| `LICENSES/` | Third-party and model licence notices |
| `SHA256SUMS` | Checksum file for all release assets |

See [Release guide](docs/RELEASE.md) for the full checklist and [GitHub Releases](https://github.com/estebanmr99/voice-to-text/releases) for published portable builds.

## Licence

This project is licensed under the MIT License — see [LICENSE](LICENSE).

Third-party dependency notices are in [LICENSES/THIRD-PARTY-NOTICES.md](LICENSES/THIRD-PARTY-NOTICES.md).
Model asset notices are in [LICENSES/MODEL-NOTICES.md](LICENSES/MODEL-NOTICES.md).
