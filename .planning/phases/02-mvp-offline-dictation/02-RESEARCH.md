# Phase 2: MVP Offline Dictation - Research

**Researched:** 2026-05-04
**Status:** Complete — findings validated against PyPI and current package versions

---

## 1. PySide6 System Tray & Global Hotkeys

### System Tray
- **PySide6.QtWidgets.QSystemTrayIcon** provides native Windows system tray integration
- Supports context menu (QMenu), tooltips, and animated icons
- Signals: `activated(reason)`, `messageClicked()`
- Requires `QApplication` with `setQuitOnLastWindowClosed(False)` for tray-only apps
- Icon formats: PNG/ICO recommended; SVG support varies on Windows

### Global Hotkeys
- **PySide6 has NO built-in global hotkey API**
- Options evaluated:
  1. **`keyboard` library** — Simple API but requires admin on Windows for global hooks; violates CORE-09 (no admin)
  2. **`pynput` library** — Cross-platform, can listen without admin for some keys, but global hotkeys may still need elevation depending on key combo
  3. **Win32 API via `ctypes`** — `RegisterHotKey` / `UnregisterHotKey` work without admin for standard modifier+key combos (Ctrl+Alt, Win, etc.)
  4. **Win32 API via `pywin32`** — Same as ctypes but with cleaner Python wrappers
- **Recommendation:** Use `ctypes` calling `user32.RegisterHotKey` directly. No admin required for standard combos. MOD_WIN, MOD_CONTROL, MOD_ALT, MOD_SHIFT flags. Returns WM_HOTKEY message to window message loop.

### Floating Panel
- `QWidget` with `Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool`
- Position with `QScreen.availableGeometry()` to avoid taskbar
- Transparent background: `setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)`

---

## 2. Audio Capture (sounddevice / PortAudio)

### sounddevice 0.5.5
- **License:** MIT
- **Pre-built wheels:** Yes — win_amd64, win32, win_arm64
- **Backend:** PortAudio (bundled in wheels)
- **WASAPI support:** Yes — `sounddevice.RawInputStream` with `hostapi='Windows WASAPI'` or `extra_settings=sounddevice.WasapiSettings(loopback=True)` for loopback
- **Key API:**
  - `sd.query_devices()` — list input/output devices
  - `sd.InputStream(callback=callback, samplerate=16000, channels=1, dtype='int16')`
  - `sd.RawInputStream` for lower-level buffer access
- **Blockers:** None. Works out-of-the-box on Windows.

### Alternative: PySide6 QtMultimedia
- `QAudioInput` / `QAudioSource` available in PySide6.QtMultimedia
- Less mature than sounddevice for low-latency capture
- **Recommendation:** Use sounddevice for Phase 2 MVP. QtMultimedia can be evaluated later.

---

## 3. Voice Activity Detection (VAD)

### WebRTC VAD (webrtcvad 2.0.10)
- **License:** MIT
- **Last release:** 2017 (stable but unmaintained)
- **Pros:** Very fast, no ML dependencies, tiny footprint (~66KB source)
- **Cons:** Only accepts 10ms, 20ms, or 30ms frames at 8kHz, 16kHz, or 32kHz; requires 16-bit mono PCM
- **API:** `webrtcvad.Vad(aggressiveness)` where aggressiveness 0-3
- **Usage pattern:** Feed audio frames continuously, detect speech start/end by counting consecutive speech/non-speech frames

### Silero VAD (silero-vad 6.2.1)
- **License:** MIT
- **Last release:** Feb 2026 (actively maintained)
- **Pros:** State-of-the-art accuracy, supports 8kHz and 16kHz, ONNX runtime option (no torch dependency), handles noise better
- **Cons:** Larger dependency footprint (torch ~2GB or onnxruntime ~100MB), slightly higher latency (~1ms per chunk)
- **API:** `load_silero_vad()` → `get_speech_timestamps(audio, model)`
- **faster-whisper integration:** faster-whisper has built-in Silero VAD filter via `vad_filter=True`

### Recommendation
- **Default profile:** WebRTC VAD — fast, lightweight, no heavy deps, good enough for MVP
- **Accurate profile:** Silero VAD (ONNX) — user-selectable via settings, loaded dynamically only when selected
- **Architecture:** VAD interface with two implementations (WebRTC default, Silero accurate)

---

## 4. Offline Transcription (whisper.cpp)

### pywhispercpp 1.4.1
- **License:** MIT (same as whisper.cpp)
- **Pre-built wheels:** Yes — cp39-cp313, win_amd64/win32, musllinux, manylinux, macOS
- **Default build:** CPU-only (no CUDA, no OpenBLAS)
- **Optional builds:** `GGML_CUDA=1`, `GGML_BLAS=1`, `WHISPER_COREML=1`, `GGML_VULKAN=1`
- **API:**
  ```python
  from pywhispercpp.model import Model
  model = Model('path/to/ggml-model.bin', n_threads=4)
  segments = model.transcribe('audio.wav')
  ```
- **Streaming support:** `new_segment_callback` for real-time partial results
- **Model formats:** GGML/GGUF quantized models (q5_0, q5_1, q8_0, etc.)
- **Assistant example:** Built-in `pywhispercpp.examples.assistant` shows VAD + transcription loop pattern

### faster-whisper 1.2.1 (NVIDIA dev backend)
- **License:** MIT
- **Backend:** CTranslate2 (C++ inference engine)
- **GPU requirements:** cuBLAS for CUDA 12, cuDNN 9 for CUDA 12
- **CPU support:** Yes, with int8 quantization
- **Pros:** Up to 4x faster than openai-whisper, batch inference, built-in Silero VAD
- **Cons:** GPU path requires NVIDIA runtime libraries (not redistributable without approval — blocked per Phase 1 license matrix)
- **CPU-only usage:** `WhisperModel(model_size, device="cpu", compute_type="int8")`

### Recommendation
- **Shipping backend:** whisper.cpp via pywhispercpp — CPU-only, no runtime deps, models side-loaded
- **Dev backend:** faster-whisper CPU (int8) for benchmarking; GPU path blocked pending license approval
- **Worker isolation:** Run transcription in `multiprocessing.Process` to isolate model memory and keep UI responsive (per MOD-02)

---

## 5. Win32 Clipboard + SendInput (PasteController)

### Clipboard Access
- **pywin32** (`win32clipboard` module) — `OpenClipboard()`, `EmptyClipboard()`, `SetClipboardData(CF_UNICODETEXT, text)`, `CloseClipboard()`
- **Alternative:** `ctypes` calling `user32.OpenClipboard`, `kernel32.GlobalAlloc`, `user32.SetClipboardData`
- **Clipboard restore:** Save previous format/data before paste, restore after paste
- **Challenges:** Some apps (terminal emulators, remote desktop) may not handle clipboard paste well; SendInput is more reliable for universal pasting

### SendInput
- **pywin32:** `win32api.SendInput()` or `win32ui` — complex API
- **ctypes approach:** Define `INPUT`, `KEYBDINPUT` structures, call `user32.SendInput`
- **Paste sequence:** Simulate Ctrl+V (key down Ctrl, key down V, key up V, key up Ctrl)
- **Advantage:** Works in any focused window regardless of clipboard support
- **Limitation:** Requires active window focus; may not work if window loses focus during transcription

### Recommendation
- **Primary paste:** SendInput with Ctrl+V simulation (universal)
- **Fallback:** Direct clipboard set + manual user paste (for apps that block SendInput)
- **Clipboard restore:** Always attempt to restore previous clipboard content after paste (CORE-07)

---

## 6. Offline Packaging for Windows

### PyInstaller 6.20.0
- **License:** GPLv2 with special exception (allows bundling proprietary apps)
- **Python support:** 3.8–3.14
- **PySide6 support:** Built-in hooks, tested, bundles Qt DLLs automatically
- **Output:** Single executable or single folder
- **MSVC DLLs:** Bundled automatically on Windows
- **One-file mode:** `--onefile` creates single .exe; slower startup but easier distribution
- **One-folder mode:** `--onedir` faster startup; better for large apps with model files

### Nuitka
- **License:** Apache 2.0
- **Approach:** Python-to-C++ compilation
- **Pros:** Smaller executables, faster startup, harder to reverse-engineer
- **Cons:** Longer build times, some Python features not fully supported, less mature with PySide6

### Recommendation
- **Phase 2:** PyInstaller `--onedir` for development and testing
- **Phase 6:** Evaluate Nuitka vs PyInstaller for final release packaging
- **Model distribution:** Models NOT bundled (legal constraint); side-load instructions provided

---

## 7. Privacy & Security Enforcement

### No Runtime Network (PRIV-01)
- **Strategy:** Monkey-patch `socket.socket`, `urllib.request`, `http.client` at app startup to raise exceptions
- **PySide6 risk:** QtNetwork module — avoid importing. If needed for local IPC, restrict to QLocalSocket only
- **Model download risk:** pywhispercpp and faster-whisper may attempt HuggingFace Hub downloads if model path not found — MUST intercept and redirect to local error

### No Telemetry (PRIV-02)
- PyInstaller: No built-in telemetry
- pywhispercpp: No telemetry
- sounddevice: No telemetry
- webrtcvad: No telemetry
- **Risk:** PySide6/Qt may load platform plugins that phone home (update checks) — disable via `qt.conf` or environment variables

### Zero Retention (PRIV-02)
- Audio buffers: Keep in memory only, clear after transcription
- Transcripts: Clear after paste, no logging of content
- Temporary files: Use `tempfile` with `delete=True`, or memory buffers only
- **Exception:** Diagnostics module may log redacted event names (no content)

---

## 8. Worker Process Architecture (MOD-02)

### Options
1. **QThread** — Simple but shares memory space; model memory bloats main process
2. **multiprocessing.Process** — True isolation, separate memory, can be terminated cleanly
3. **subprocess.run** — Maximum isolation but high latency for repeated calls

### Recommendation
- **Transcriber:** `multiprocessing.Process` with `Queue` for audio data in / text out
- **Model loading:** Load model once in worker, keep process alive during app lifetime
- **Termination:** `Process.terminate()` + `Process.join(timeout=5)` for graceful shutdown
- **IPC:** `multiprocessing.Queue` for audio chunks and transcription results; `Event` for cancellation

---

## 9. Dependency Summary

| Package | Version | License | Size | Wheel | Network | Notes |
|---------|---------|---------|------|-------|---------|-------|
| PySide6 | 6.x | LGPL/Commercial | ~150MB | Yes | No | Qt6 platform plugins may phone home — disable |
| sounddevice | 0.5.5 | MIT | ~365KB | Yes | No | PortAudio bundled |
| pywhispercpp | 1.4.1 | MIT | ~1.2MB | Yes | No | whisper.cpp static-linked; models side-loaded |
| webrtcvad | 2.0.10 | MIT | ~66KB | Source only | No | Requires C compiler on install; consider pre-built wheel |
| silero-vad | 6.2.1 | MIT | ~9MB | Yes | No | ONNX option avoids torch dependency |
| faster-whisper | 1.2.1 | MIT | ~1.1MB | Yes | No | CTranslate2 backend; CPU mode works without CUDA |
| pywin32 | 306+ | PSF | ~8MB | Yes | No | Required for clipboard/SendInput |
| pyinstaller | 6.20.0 | GPL+exception | ~3MB | Yes | No | Build-time only |

### Build Concerns
- **webrtcvad:** No pre-built Windows wheel on PyPI. May require MSVC build tools. Alternative: `webrtcvad-wheels` (community fork with wheels) or vendor the C code.
- **silero-vad ONNX:** `onnxruntime` (~100MB) or `torch` (~2GB). For MVP, use WebRTC VAD default; Silero as optional plugin.

---

## 10. Open Questions / Risks

1. **webrtcvad compilation on Windows** — No PyPI wheel; may need `webrtcvad-wheels` or vendor C code
2. **PySide6 one-file PyInstaller** — Qt platform plugins may fail to load; one-folder mode safer
3. **SendInput reliability** — Some UWP apps and elevated processes may ignore SendInput
4. **WASAPI exclusive mode** — May block other apps from microphone; shared mode preferred
5. **Model memory usage** — whisper.cpp base model ~500MB RAM, small ~1GB; ensure worker process isolation
6. **Global hotkey without admin** — RegisterHotKey works for most combos but may conflict with other apps

---

## RESEARCH COMPLETE

**Phase 2 research validated:** All core dependencies have viable Windows paths. No blockers identified for MVP scope.
