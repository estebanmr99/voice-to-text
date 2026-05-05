# Model Side-Loading Guide

Spanglish Dictation requires local Whisper-family model files for offline
transcription.  The app **never downloads models at runtime**.  You must
side-load at least one model before first use.

## Directory structure

Place model files in the `models/` directory at the project root (or next to
the portable executable):

```
models/
  ggml-base.bin      # CPU Portable (recommended default)
  ggml-small.bin     # CPU High Accuracy
```

The `models/` directory is excluded from git and the default portable zip.

## Available models

### ggml-base.bin

| Field | Value |
|-------|-------|
| Format | whisper.cpp quantized |
| Size | 141.1 MB |
| SHA-256 | `60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe` |
| Profile | CPU Portable |
| Source | [huggingface.co/ggerganov/whisper.cpp](https://huggingface.co/ggerganov/whisper.cpp/tree/main) |
| Recommended for | Daily dictation — good speed/accuracy tradeoff on most CPUs |

### ggml-small.bin

| Field | Value |
|-------|-------|
| Format | whisper.cpp quantized |
| Size | 465.0 MB |
| SHA-256 | `1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b` |
| Profile | CPU High Accuracy |
| Source | [huggingface.co/ggerganov/whisper.cpp](https://huggingface.co/ggerganov/whisper.cpp/tree/main) |
| Recommended for | When accuracy matters more than speed — fits comfortably in 16 GB RAM |

## Downloading models

Use curl or your browser to download from the Hugging Face repository:

```powershell
curl.exe -L -o models/ggml-base.bin "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin"
curl.exe -L -o models/ggml-small.bin "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin"
```

## Verifying integrity

After downloading, verify the SHA-256 checksum:

```powershell
(Get-FileHash -Algorithm SHA256 models/ggml-base.bin).Hash
```

Compare against the published hash above.  If they do not match, the file
is corrupt or has been tampered with — delete it and download again.

## NVIDIA dev profile (optional)

For RTX GPU users (optional, not in default portable zip):

1. Install: `pip install faster-whisper ctranslate2`
2. Download a pre-converted CTranslate2 model:
   ```bash
   pip install huggingface-hub
   huggingface-cli download Systran/faster-whisper-large-v3-turbo --local-dir models/faster-whisper-large-v3-turbo
   ```
3. Select the "NVIDIA Dev" profile in the tray menu.

## Missing model behaviour

If the configured model file is missing or corrupt:

1. The app returns a local error — it does not attempt to download.
2. System tray shows a notification with the model name.
3. Select a different profile or side-load the required model file.

## Licence

Whisper model weights are released under the MIT licence by OpenAI.
Verify the exact terms before redistribution.  See
[LICENSES/MODEL-NOTICES.md](../LICENSES/MODEL-NOTICES.md).
