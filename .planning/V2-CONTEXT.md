# V2 Enhancement Context
## User Requirements
1. **Persistent settings** — Settings must survive PC restarts (investigate current persistence bugs)
2. **Model management window** — Full custom config: add/remove/edit models (path, language, backend, n_threads, beam_size, custom name)
3. **Custom profiles** — Create/edit/delete profiles with preferred model, fallback order, backend hint
4. **Real-time streaming dictation** — Text appears at cursor position in real-time while speaking (no intermediate panel, Perplexity-style)
5. **True push-to-talk** — Hold to record, release to stop (currently both hotkeys call toggle())
6. **Multiple output modes** — "Paste immediate" / "Stream to cursor" / "Confirmation" — user picks in settings
## Priority Order
Phase 7 (Settings + PTT) → Phase 8 (Models) → Phase 9 (Streaming) → Phase 10 (Stream-to-Cursor)
## Codebase Discoveries
### Settings Persistence
- `SettingsStore` in `src/settings_store.py` persists to `~/.spanglish-dictation/settings.json`
- Atomic save via temp file + `os.replace()`
- Batch mode supported via `begin_batch()`/`end_batch()`
- **Bug risk**: `load()` at line 60 does `self._data.update(loaded)` which merges — new default keys not in the file won't be overwritten but also won't be validated
- Missing settings keys need to be added: `dictation_mode`, `output_mode`
- Settings dialog in `src/settings_dialog.py` needs new sections for these settings
### Hotkey System
- `shell_integration.py` uses `pynput` for global hotkeys
- Two hotkeys registered: toggle (id=1) and push_to_talk (id=2)
- **BUG**: `main.py:188` wires BOTH hotkeys to `dictation_loop.toggle()` — push_to_talk should be hold-to-record
- `pynput` GlobalHotKeys only supports key combos, NOT individual press/release events
- For true PTT, need `pynput.keyboard.Listener` for individual key press/release tracking, OR switch to a different approach
- Alternative: Use `pynput.keyboard.Listener` with key state tracking for PTT mode
### Transcription Pipeline
- `DictationLoop` in `src/dictation_loop.py` is the state machine (IDLE → LISTENING → PROCESSING → READY)
- Audio flows: mic → AudioCapture callback → SpeechDetector VAD → buffer → speech_end → Transcriber.transcribe() → PostProcessor → PasteController
- Transcriber spawns a `multiprocessing.Process` worker that loads whisper.cpp model
- Worker receives audio array + language via Queue, returns result dict via Queue
- **No streaming**: Entire buffer is transcribed at once after speech ends
- For streaming: need to send audio in segments (~2-3s chunks), get interim results, emit partial transcription signal
### Paste Controller
- `paste_controller.py` uses clipboard + Ctrl+V SendInput
- Backup/restore clipboard with retry logic
- **No character-by-character typing** — need new `TypingController` for stream-to-cursor
- Win32 `SendInput` with `KEYBDINPUT` can type individual characters but needs Unicode handling via `VK_PACKET` (0xE7) and `wScan` for Unicode
### Model Management
- `model_manager.py` has hardcoded `_DEFAULT_MODELS` (base, small) and `_DEFAULT_PROFILES` (cpu-portable, cpu-high-accuracy, nvidia-dev)
- Registry file at `models/registry.json`, but no UI to add/edit/customize
- `profile_resolver.py` resolves settings-based profile selection to actual model
- No user-defined models or profiles currently possible
- `ModelInfo` dataclass has: name, path, size_mb, checksum_sha256, language, parameters (dict with n_threads), backend, profile_compatibility, source_url, license_status
- `Profile` dataclass has: canonical_name, display_name, description, preferred_model, fallback_order, backend_hint, shipping_default
### Architecture
- Modular monolith with 10 modules in `src/`
- Qt signal/slot wiring in `src/main.py`
- All modules use dependency injection (no singletons except PrivacyGuard)
- Tests use pytest with manual QApplication fixture (378 tests passing)
- PrivacyGuard blocks ALL network at startup via monkey-patching
- faster-whisper backend referenced but NOT implemented (only pywhispercpp)
## Key Files by Feature
| Feature | Files to Modify/Create |
|---------|----------------------|
| Settings fix | `src/settings_store.py`, `src/settings_dialog.py`, `src/main.py` |
| True PTT | `src/shell_integration.py`, `src/dictation_loop.py`, `src/main.py` |
| Model management | NEW: `src/model_management_dialog.py`; MODIFY: `src/model_manager.py`, `src/profile_resolver.py`, `src/shell_integration.py` |
| Profile management | NEW: `src/profile_management_dialog.py`; MODIFY: `src/model_manager.py`, `src/settings_store.py` |
| Streaming transcription | MODIFY: `src/transcriber.py`, `src/transcriber_worker.py`, `src/dictation_loop.py`; NEW: streaming mode logic |
| Stream-to-cursor | NEW: `src/typing_controller.py`; MODIFY: `src/dictation_loop.py`, `src/main.py`, `src/settings_store.py` |
| Output mode setting | `src/settings_store.py`, `src/settings_dialog.py`, `src/main.py` |

---

## Recommended Skills to Install

### High Priority
```
npx skills add howell5/willhong-skills@graphify -g -y
```
Graphify (336 installs) — Generates visual code graphs showing file relationships, call graphs, and dependency maps. Critical for understanding the dictation pipeline wiring across modules.

```
npx skills add oimiragieo/agent-studio@pyqt6-ui-development-rules -g -y
```
PyQt6 UI Development Rules (544 installs) — Closest to PySide6 (same Qt bindings). Best practices for Qt desktop dialogs, signal/slot patterns, and model/view architecture. Useful for Phases 7-10 UI work.

### Medium Priority
```
npx skills add addyosmani/agent-skills@code-review-and-quality -g -y
```
Code Review and Quality (2.8K installs) — General code review patterns. Useful during execution phases to catch issues.

```
npx skills add ds-codi/project-memory-mcp@pyside6-mvc -g -y
```
PySide6 MVC (95 installs) — Model/view/controller patterns for PySide6. Helpful for Model Management Dialog (Phase 8).

### Optional
```
npx skills add modelcontextprotocol/ext-apps@create-mcp-app -g -y
```
Create MCP App (1.1K installs) — If you want to build an MCP server for external integration (e.g., letting other apps control the dictation engine).

**No MCP server is currently required for development.** All features are local/desktop. If you later want external app integration (e.g., VS Code extension, browser extension controlling dictation), an MCP server could expose the DictationLoop API via stdio/SSE.

---

## Code Quality Issues to Fix (Pre-Phase 7)

### Critical
1. **Thread safety on `_audio_buffer`** (`dictation_loop.py:89`) — Race condition between consumer thread and main Qt thread. Add `threading.Lock` or use `queue.Queue`.
2. **Pre-compile regex patterns** (`post_processor.py:50-55`) — `re.compile()` called inside loop on every `normalize()`. Compile once in `__init__`, cache.
3. **Remove dead Win32 hotkey code** (`shell_integration.py:64-83, 552-578`) — `_parse_hotkey`, `_MODIFIER_MAP`, `_VK_MAP`, `MOD_*` constants all dead since pynput migration.
4. **Fix `glossary.py:28` quadruple-quote bug** — `""""Lowercase..."""` has 4 quotes, silently breaks the `output` field docstring.
5. **Replace `assert` with proper checks** (`transcriber.py:208-209`) — Assertions stripped under `python -O`.
6. **Non-atomic registry write** (`model_manager.py:242-251`) — No crash safety. Adopt temp+rename pattern from `settings_store.py`.

### Moderate
7. **Deduplicate fallback icon** (`main.py:82-111` + `shell_integration.py:592-611`) — Two identical 30-line functions. Extract to shared `icon_utils.py`.
8. **Extract `_log_event` to shared mixin** — Identical 7-line method in 4 classes (`dictation_loop.py`, `paste_controller.py`, `shell_integration.py`, `privacy_guard.py`).
9. **Unify `start()`/`start_continuous()`** (`dictation_loop.py:117-162`) — Replace with `_begin_listening(continuous: bool)`.
10. **Throttle diagnostics rotation** (`diagnostics.py:99`) — `_rotate_if_needed()` does glob+stat on every `event()` call. Throttle to every 100 events or 60 seconds.
11. **Increase SHA-256 read buffer** (`model_manager.py:258`) — 8 KB chunks for 141+ MB files = ~17K syscalls. Use 1 MB chunks.
12. **Initialize dynamic attributes in `__init__`** (`shell_integration.py:270, 322, 403`) — `_action_show_panel`, `_profile_actions`, `_pre_dialog_profile` should be declared in `__init__`.

### Token Reduction (Low Priority)
13. **Compress section separators** — ~45 blocks of `# ------------------------------------------------------------------` (72 chars) across 18 files. Shorten to `# --` or remove where self-evident.
14. **Compress docstrings** — ~80 lines of verbose Sphinx-style docstrings could be halved without losing meaning.
15. **Remove unused import** (`main.py:18` — `from PySide6.QtCore import Qt` unused at top level).
16. **Remove duplicate constant** (`_MIN_AUDIO_SAMPLES = 1600` in both `transcriber.py:27` and `transcriber_worker.py:23`).