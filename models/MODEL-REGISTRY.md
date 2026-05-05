# Local Model Registry

Status: Models side-loaded for this workstation. Not in git.

## Hardware Profile

| Component | Spec |
|-----------|------|
| CPU | AMD Ryzen 5 3600 (6 cores / 12 threads) |
| RAM | 16 GB DDR4 |
| GPU | NVIDIA RTX 2070 Super (8 GB VRAM) |

## Available Models

### whisper.cpp (CPU Backend)

| Model | File | Size | SHA-256 | Profile | Load Time | RAM | Notes |
|-------|------|------|---------|---------|-----------|-----|-------|
| base | `ggml-base.bin` | 141.1 MB | `60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe` | CPU Portable | Fast | ~300 MB | Recommended default for this CPU. Good speed/accuracy tradeoff. |
| small | `ggml-small.bin` | 465.0 MB | `1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b` | CPU High Accuracy | Moderate | ~1 GB | Better accuracy. Fits comfortably in 16 GB RAM. |

### faster-whisper (NVIDIA Dev Backend)

| Model | Format | Size | Profile | VRAM | Notes |
|-------|--------|------|---------|------|-------|
| large-v3-turbo | CTranslate2 | ~1.6 GB | NVIDIA Dev | ~4-6 GB | **Not yet downloaded.** Best speed/accuracy on RTX 2070 Super. Convert from Whisper or download pre-converted. |

## Download Commands

### whisper.cpp models (DONE)

Downloaded from: `https://huggingface.co/ggerganov/whisper.cpp/tree/main`

```powershell
curl.exe -L -o models/ggml-base.bin "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin"
curl.exe -L -o models/ggml-small.bin "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin"
```

### faster-whisper models (PENDING)

Option A — Download pre-converted CTranslate2 model:
```bash
pip install huggingface-hub
huggingface-cli download Systran/faster-whisper-large-v3-turbo --local-dir models/faster-whisper-large-v3-turbo
```

Option B — Convert from OpenAI Whisper:
```bash
pip install faster-whisper
ct2-transformers-converter --model openai/whisper-large-v3-turbo --output_dir models/faster-whisper-large-v3-turbo --quantization float16
```

## Profile Recommendations for This Workstation

| Profile | Model | Backend | Expected Latency | Use Case |
|---------|-------|---------|------------------|----------|
| **CPU Portable** (Recommended Default) | `ggml-base.bin` | whisper.cpp | Low | Daily dictation, fast response |
| **CPU High Accuracy** | `ggml-small.bin` | whisper.cpp | Medium | When accuracy matters more than speed |
| **NVIDIA Dev** | `large-v3-turbo` | faster-whisper | Very Low | Development, benchmarking, best quality |

## Missing Model Behavior

If a configured model is missing or corrupt:

1. Return local `missing_model` or `corrupt_model` error
2. Surface side-load guidance pointing to this document
3. Make no network request, no download attempt
4. Do not create model files in the working directory

## License Notes

- Whisper model weights: MIT license (OpenAI)
- whisper.cpp: MIT license (ggerganov)
- faster-whisper: MIT license (SYSTRAN)
- Verify exact terms before redistribution in release artifacts

---
*Last updated: 2026-05-05 after model side-load for AMD Ryzen 5 3600 + RTX 2070 Super workstation*
