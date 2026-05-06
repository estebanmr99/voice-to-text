# Milestone v1.0 — Manual Verification Guide

Windows Offline Spanglish Dictation — confirm everything works before release.

---

## Your Environment Status

| Component | Status | Action |
|-----------|--------|--------|
| Python 3.12.10 | ✓ Installed | — |
| PySide6 (Qt UI) | ✓ Installed | — |
| sounddevice | ✓ Installed | — |
| numpy | ✓ Installed | — |
| pywhispercpp | ✓ Installed | — |
| **pywin32** | ✗ Missing | `pip install pywin32==306` |
| **webrtcvad** | ✗ Missing | See Step 1 below |
| ggml-base.bin (141MB) | ✓ Available | CPU Portable profile |
| ggml-small.bin (465MB) | ✓ Available | CPU High Accuracy profile |
| faster-whisper (NVIDIA) | ✗ Not downloaded | Optional — see "More Models" section |

---

## Step 1 — Install Missing Dependencies

Open PowerShell as normal user (no admin needed):

```powershell
# Activate your virtual environment (if using one)
.\venv\Scripts\Activate.ps1

# Required for clipboard, hotkeys, Win32 integration
pip install pywin32==306

# Required for speech detection (WebRTC VAD)
# This needs Visual C++ Build Tools first:
# https://visualstudio.microsoft.com/visual-cpp-build-tools/
# Then:
pip install webrtcvad-wheels==2.0.11
```

---

## Step 2 — Run All Automated Tests

```powershell
python -m pytest tests/ -q
```

Expected: **378 passed, 3 skipped**.

---

## Step 3 — Verify Release Artifacts (No Launch Required)

These can be verified from the command line without running the app:

### 3a. Licence bundle check
```powershell
python scripts/generate_license_bundle.py --check
```
Expected: `All required notice tokens present.`

### 3b. Offline smoke test
```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke_offline.ps1
```
Expected: `=== Smoke test PASSED ===`

### 3c. Release docs validation
```powershell
python -m pytest tests/test_release_docs.py -q
```
Expected: 20 passed

### 3d. Blocked artifact policy
```powershell
python -m pytest tests/test_release_packaging.py -q
```
Expected: all passing, no models/CUDA/cuDNN in default zip

---

## Step 4 — Launch the App (Manual UX Testing)

```powershell
python src/main.py
```

### 4a. Tray Icon Appears
- **Expected:** A green microphone icon appears in your system tray (bottom-right, near clock)
- Click the tray icon to open the context menu
- If icon is missing → pywin32 not installed

### 4b. Tray Menu Structure
Right-click the tray icon. Expected menu items:
- **Start Dictation** / **Start Continuous** / Stop Dictation
- **Paste Mode** (Immediate / Confirm)
- **Profile** (CPU Portable / CPU High Accuracy / NVIDIA Dev)
- **Show Status Panel** / **Hide Status Panel**
- **Settings...**
- **Exit**

### 4c. Settings Dialog
Select **Settings...** from tray menu.
- **Expected:** Dialog opens with tabs/sections for Hotkeys, Audio Device, Model Profile, VAD Profile, Paste Mode, Glossary Path
- Change a setting (e.g., paste mode) and close. Reopen — setting should persist.

### 4d. Double-Click Tray Reveal
Double-click the tray icon.
- **Expected:** A floating status panel appears showing current state
- Click the × or click outside to dismiss

---

## Step 5 — Dictation Test (Core Feature)

### Prerequisites
- A microphone plugged in and working (check Windows Sound Settings)
- pywin32 installed (for hotkeys and paste)
- webrtcvad installed (for speech detection)

### 5a. Start Dictation
From tray menu: **Start Dictation**
- **Expected:** Status changes to "Listening..." or similar
- If error about missing model → check that `ggml-base.bin` is in `models/` folder

### 5b. Speak and Transcribe
1. Press the global hotkey (default push-to-talk: **Ctrl+Shift+Space**)
2. Speak a sentence in English or Spanglish (e.g., "I need to merge the PR for the API")
3. Release hotkey

### 5c. Verify Paste
- **Expected (Immediate mode):** Text appears in your active window (Notepad, browser, IDE)
- **Expected (Confirm mode):** A dialog pops up showing transcribed text — edit if needed, click OK to paste

### 5d. Spanglish Glossary
Test these specific terms by saying them:
| Say this | Should paste as |
|----------|----------------|
| "pr" | PR |
| "api" | API |
| "ci" | CI |
| "cpu" | CPU |
| "commitear" | commitear (preserved) |
| "deployar" | deployar (preserved) |

---

## Step 6 — Privacy Verification

The app enforces zero-network at runtime. Verify:

1. **Disconnect WiFi / Ethernet** (or just trust the automated tests)
2. Launch the app — should start normally without any network error
3. Run transcription — should work fully offline
4. No popups about updates, accounts, or cloud services

The privacy tests (367+ automated) also block `socket`, `urllib`, and Qt network APIs — any code that tries to make a network call fails these tests.

---

## More Models

You currently have **2 of 10** candidate models. Here's what you need for full coverage:

### Already Done ✓
| Model | File | Size | Profile |
|-------|------|------|---------|
| base (CPU) | `ggml-base.bin` | 141 MB | CPU Portable (default) |
| small (CPU) | `ggml-small.bin` | 465 MB | CPU High Accuracy |

### NVIDIA Dev Profile (Optional — for your RTX 2070 Super)
```powershell
# Install faster-whisper backend
pip install faster-whisper ctranslate2

# Download pre-converted model (~1.6 GB)
pip install huggingface-hub
huggingface-cli download Systran/faster-whisper-large-v3-turbo --local-dir models/faster-whisper-large-v3-turbo
```
Then select "NVIDIA Dev" profile from tray menu. This gives the fastest, most accurate transcription using your GPU.

### For Full Benchmark Coverage (Later)
The benchmark plan lists 10 model candidates. You'd also need:
- `ggml-tiny.bin`, `ggml-medium.bin` (whisper.cpp — smaller/larger quantized models)
- `ggml-large-v3.bin` (if you have enough RAM ~4GB)
- Distil-whisper variants, Silero VAD model

These are not needed for daily use — only if you want to run the full ASR benchmark suite.

---

## Your Next Steps as Human

### Immediate (20 minutes)
1. **Install missing deps:** `pip install pywin32==306 webrtcvad-wheels==2.0.11`
2. **Run full test suite:** `python -m pytest tests/ -q`
3. **Launch app:** `python src/main.py`
4. **Test dictation:** Speak something, confirm it pastes correctly
5. **Try both profiles:** Switch between CPU Portable and CPU High Accuracy in tray

### Short-term (1 hour)
6. **Download NVIDIA model** if you want GPU transcription
7. **Test all tray actions:** Start/Stop, Settings, Profile switching, Paste mode toggle
8. **Test glossary:** Say "pr", "api", "mergear", "commitear" — verify normalization
9. **Disconnect internet, repeat tests** — confirm everything works offline

### Before GitHub Release
10. **Run release smoke test:** `powershell -File scripts/smoke_offline.ps1`
11. **Verify licence bundle:** `python scripts/generate_license_bundle.py --check`
12. **Review README** and docs for accuracy
13. **Build portable zip:** `powershell -File scripts/build_portable.ps1 -Version "0.1.0"` (needs `pip install ".[release]"`)
14. **Tag and push:** `git tag v0.1.0 && git push origin v0.1.0` (triggers GitHub Actions release)

---

## Quick Reference

```powershell
# Run all tests
python -m pytest tests/ -q

# Run the app
python src/main.py

# Offline smoke check
powershell -ExecutionPolicy Bypass -File scripts/smoke_offline.ps1

# License verification
python scripts/generate_license_bundle.py --check

# Model hashes (verify integrity)
Get-FileHash -Algorithm SHA256 models/ggml-base.bin
Get-FileHash -Algorithm SHA256 models/ggml-small.bin
# Expected base:    60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe
# Expected small:   1be3a9b2063867b937e64e2ec7483364a79917e157fa98c5d94b5c1fffea987b
```

---

## What Each Phase Built (For Reference)

| Phase | What You're Testing |
|-------|---------------------|
| 2 — MVP Dictation | Push-to-talk, audio capture, VAD, transcription, paste, tray, hotkey |
| 3 — Model Profiles | Profile switching, CPU Portable/High Accuracy/NVIDIA Dev, model registry |
| 4 — GUI Polish | Settings dialog, confirmation mode, tray menu groups, status panel |
| 5 — Spanglish Glossary | "pr"→"PR", "api"→"API", "mergear" preserved — 25 terms default |
| 6 — Packaging | Portable zip build, license bundle, README/docs, GitHub Actions release |
