# Project Instructions

## Project

Windows Offline Spanglish Dictation — desktop voice-to-text for technical Spanglish. Python + PySide6 tray app with whisper.cpp CPU backend. Fully offline, zero telemetry, zero retention.

## Commands

```bash
# Run the app (from repo root, with .venv activated)
python src/main.py

# Run all tests (394 pass, 3 skip — requires .venv)
python -m pytest tests/ -q

# Run a single test file
python -m pytest tests/test_dictation_loop.py -q

# Run one test by name
python -m pytest tests/test_settings_store.py::TestSettingsStore::test_save_and_load -v

# Install runtime deps (production)
pip install -r requirements.txt

# Install with VAD support (needs Visual C++ Build Tools)
pip install -r requirements.txt && pip install webrtcvad-wheels==2.0.11

# Install dev deps (lint/format/typecheck — NOT currently in .venv)
pip install -e ".[dev]"
```

**Dev tools (ruff, black, mypy) are declared in `[project.optional-dependencies] dev` but NOT installed in the current .venv.** Install with `pip install -e ".[dev]"` before running lint/typecheck.

## Architecture

`src/main.py` is the single entry point — instantiates all modules in order, wires Qt signals, starts event loop.

Module dependency flow (audio → text):
```
AudioCapture → SpeechDetector → DictationLoop → Transcriber → PostProcessor → PasteController
                                                                         ↑
                                                                  ModelManager → models/*.bin
```

Key wiring in `main.py`:
- `shell.hotkey_pressed` → `dictation_loop.toggle()` (currently BOTH hotkeys call toggle — PTT not differentiated)
- `dictation_loop.state_changed` → `shell.show_status_panel(state, msg)`
- `shell.profile_changed` → stops transcriber, resolves profile, restarts
- `dictation_loop.transcription_ready` → `ConfirmationDialog` (only in confirmation paste mode)

**Thread model:** `AudioCapture._consumer_loop` runs on a daemon thread. `DictationLoop._on_audio_block` runs on that thread — uses Qt signals (`_speech_end_signal`, `_transcription_result_signal`) to marshal to the main thread. `Transcriber` uses a separate `multiprocessing.Process`.

**PrivacyGuard** must be enforced as the **first import** in `main.py` — it monkey-patches socket/urllib/ssl to block all network. Code imported before `PrivacyGuard().enforce()` can use network; code imported after **cannot**.

## Testing

- Tests use `unittest.mock.MagicMock` for all hardware deps (audio, transcriber, clipboard). No real mic, model, or paste required.
- `test_transcriber.py` creates a fake `pywhispercpp` module so tests pass without the real package.
- Tests requiring Qt use a manual `QApplication` fixture (not `pytest-qt`):
  ```python
  @pytest.fixture(scope="session")
  def qapp():
      app = QApplication.instance() or QApplication(sys.argv)
      yield app
  ```
- `test_audio_capture.py` and `test_speech_detector.py` may fail on CI without audio hardware — they mock sounddevice.

## Known Bugs / Gaps

- **Push-to-talk not implemented:** both hotkeys (id=1 and id=2) call `dictation_loop.toggle()` in `main.py:188`. True hold-to-record requires `pynput.keyboard.Listener` for press/release, not just `GlobalHotKeys`.
- **`faster-whisper` backend referenced but not implemented:** profile definitions mention it, but all transcription uses `pywhispercpp`.
- **Silero VAD referenced but not implemented:** settings offer "silero" but `SpeechDetector` only has WebRTC and energy-based fallback.
- **`glossary.py:28` quadruple-quote bug:** `""""Lowercase..."""` has 4 quotes, silently corrupts the `output` field docstring.
- **Thread race on `_audio_buffer`:** `DictationLoop._audio_buffer` accessed from AudioCapture consumer thread and main Qt thread with no lock.
- **Non-atomic model registry write:** `ModelManager._save_registry()` writes directly; should use temp+rename like `SettingsStore`.

## Constraints

1. **No runtime network** — `PrivacyGuard` enforces this via monkey-patch
2. **No telemetry** — no analytics, crash uploads, or usage metrics
3. **No retained audio/transcripts** — data-in-motion only
4. **Windows-first, user-mode** — no admin rights required
5. **No model binaries in git** — `models/` is gitignored; users side-load GGML/GGUF files
6. **`webrtcvad-wheels` needs Visual C++ Build Tools** on Windows to compile
7. **`pywin32==306` pinned** — clipboard/SendInput depends on specific COM interfaces

## Source Layout

```
src/                       # All app code (src-layout, see pyproject.toml)
  main.py                  # Entry point + signal wiring
  audio_capture.py         # sounddevice/PortAudio mic capture
  speech_detector.py       # WebRTC VAD state machine
  transcriber.py           # Orchestrator (spawns worker process)
  transcriber_worker.py    # Worker: loads pywhispercpp, transcribes
  model_manager.py         # Model registry + validation
  profile_resolver.py      # Hardware → model resolution
  hardware_detector.py     # CPU/GPU detection
  dictation_loop.py        # State machine: IDLE→LISTENING→PROCESSING→READY
  post_processor.py        # Spanglish glossary normalization
  glossary.py              # Glossary loading/merge
  paste_controller.py      # Win32 clipboard + SendInput paste
  shell_integration.py     # Tray icon, pynput hotkeys, status panel
  settings_store.py        # JSON persistence at ~/.spanglish-dictation/settings.json
  settings_dialog.py       # PySide6 settings UI
  confirmation_dialog.py   # Edit-before-paste dialog
  privacy_guard.py         # Runtime network blocker
  diagnostics.py           # Redacted event logger
tests/                     # 394 passing tests, all mocked
data/                      # Default glossary (default_glossary.json)
models/                   # Gitignored; side-load GGML/GGUF here
.planning/                # GSD workflow artifacts (STATE.md, ROADMAP.md, phases/)
```

## Settings

Persisted at `~/.spanglish-dictation/settings.json`. Keys:
- `hotkey_push_to_talk`, `hotkey_toggle`, `audio_device_index`, `vad_profile`, `model_profile`, `paste_mode`, `language`, `glossary_path`
- Atomic save via temp file + `os.replace()`
- Batch mode: `begin_batch()` / `end_batch()` defers saves

Model registry at `models/registry.json`. Three default profiles: `cpu-portable`, `cpu-high-accuracy`, `nvidia-dev`.

## Workflow & Tool Rules

### RTK — Always On
- **Always prefix shell commands with `rtk`** for token compression (60-90% savings)
- `rtk git status`, `rtk ls src/`, `rtk pytest tests/ -q`, `rtk read <file>`
- RTK OpenCode plugin is installed globally — commands are auto-rewritten when possible
- On native Windows (no WSL), use `rtk` prefix explicitly in bash tool calls

### Caveman Mode
- **Planning phase**: Caveman OFF — full detail for research, analysis, architecture
- **Execution phase**: Caveman ON — compressed responses (~75% token savings)
- User toggles via `/caveman` command or "caveman mode"

### Graphify
- Rebuild after: adding new modules, major refactoring, or when agents explore unfamiliar code
- Query existing graph before rebuilding — avoid unnecessary rebuilds
- Run: `graphify build` from repo root

### GSD (Get Shit Done) — Planning
- Use `/gsd-plan-phase` for structured planning before implementation
- Use `/gsd-code-review` before merging changes
- Use `/gsd-eval-review` after implementation to verify goals
- Planning docs live in `.planning/` — consult before starting work

### OMO (Oh My OpenCode) — Execution
- Multiple agents run in parallel via `task` tool
- Each agent has isolated context — no cross-contamination
- Use `gsd-executor` subagent for plan execution with atomic commits
- Use `gsd-debugger` for bug investigation with scientific method

### Agent Conflict Prevention
- GSD agents handle planning; OMO agents handle execution — do not mix
- Never run planning commands during execution phase
- Always verify plan exists in `.planning/phases/` before executing
- One phase at a time — do not start next phase until current is verified

### Model Strategy — Enforce These Rules
- **Planning phase:** Use GPT-5.5 (included in subscription). OMO DISABLED (`"plugin": []`). Tab: Plan/Build.
- **Execution phase:** Use DeepSeek V4 Pro or GLM-5.1 (cheap). OMO ENABLED (`"plugin": ["oh-my-openagent@latest"]`). Tab: Sisyphus/Hephaestus.
- **NEVER use GPT-5.5** unless explicitly requested — it burns quota fast.
- **Free tier models:** MiniMax M2.5 for docs, quick fixes, simple tasks.
- **Quick fixes:** MiniMax M2.5 Free or DeepSeek V4 Flash.
- **Code review:** GLM-5.1 (cheap, good analysis).
- **UI work:** Kimi K2.6 (good at frontend).
- **Debugging:** DeepSeek V4 Flash (fast, cheap).

### Tab Modes
- **Without OMO:** Plan (research/analysis), Build (write code)
- **With OMO:** Sisyphus (ultraworker), Hephaestus (deep agent), Prometheus (plan builder), Atlas (plan executor)
- **Ultrawork mode:** Sisyphus handles longer, complex tasks with better context management

### OMO Toggle
- **Enable:** `cp ~/.config/opencode/"opencode2.json" ~/.config/opencode/opencode.json`
- **Disable:** Edit `~/.config/opencode/opencode.json` → `"plugin": []`
- **Restart OpenCode** after changing