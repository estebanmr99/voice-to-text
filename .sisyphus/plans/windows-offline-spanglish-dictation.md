# Windows Offline Spanglish Dictation Architecture Plan

## TL;DR
> **Summary**: Build a Windows-first, fully offline technical Spanglish dictation app as a modular Python/PySide6 desktop shell with native Win32 integration, whisper.cpp as the portable CPU shipping backend, and faster-whisper/CTranslate2 as the NVIDIA dev/benchmark backend. This plan starts with GSD tooling recovery and architecture artifacts before any production app code.
> **Deliverables**:
> - Recovered GSD/.planning workflow or documented fallback
> - Decision-complete architecture and privacy/licensing docs
> - Benchmark-driven ASR/VAD defaults
> - MVP offline dictation loop
> - Model profiles, GUI/tray polish, deterministic Spanglish glossary, packaging/release pipeline
> **Effort**: XL
> **Parallel**: YES - 5 waves
> **Critical Path**: Task 1 → Task 2 → Task 3 → Task 4 → Task 8

## Context

### Original Request
User wants a Windows-first, 100% offline desktop voice-to-text app for technical Spanglish dictation. It must run from the system tray, show a small floating topmost status panel, activate via global hotkey, capture microphone audio, detect speech/silence, transcribe offline, post-process technical Spanglish, and paste into the focused app. It must be open source, legal for GitHub, installable/cloneable without cloud services or paid APIs, and must never send audio or text to the internet.

### Interview Summary
- Repository is greenfield and currently only contains `.git/` plus planning drafts.
- `gsd-sdk` is missing from PATH, so `.planning/` artifacts cannot be generated through the requested GSD workflow yet.
- User selected **Hybrid activation**: push-to-talk plus toggle mode.
- User selected **No runtime network**: app must not make runtime network calls, including model downloads.
- User selected **Both paste modes**: immediate paste by default plus confirmation/edit-before-paste profile.

### Metis Review (gaps addressed)
- Added Phase 0 tooling recovery because Prometheus cannot create `.planning/` artifacts and `gsd-sdk` is unavailable.
- Added benchmark phase before locking model defaults because CPU latency on Intel laptops must be measured.
- Added license/SBOM requirements before release.
- Added explicit no-network tests, clipboard/paste QA, missing/corrupt model QA, and audio-device failure QA.
- Added guardrails against cloud fallback, telemetry, auto-update, sync, account systems, local LLM scope creep, and GPL surprises.

## Work Objectives

### Core Objective
Create a local-only Windows dictation pipeline that turns technical Spanglish speech into pasted text in arbitrary focused Windows applications without sending audio/text to any network service.

### Deliverables
- `.planning/` project artifacts after GSD tooling recovery: `PROJECT.md`, `config.json`, `REQUIREMENTS.md`, `ROADMAP.md`, `STATE.md`.
- Architecture documents covering modules, interfaces, dataflow, concurrency, privacy, licensing, and packaging.
- Offline ASR/VAD benchmark results for target hardware profiles.
- MVP app plan: tray/hotkey/audio/VAD/transcription/post-process/paste.
- Model profile plan: CPU portable, CPU high-accuracy, NVIDIA dev, optional OpenVINO future.
- Release plan: local model management, installer, license notices, SBOM, checksums, GitHub release docs.

### Definition of Done (verifiable conditions with commands)
- `where.exe gsd-sdk` succeeds OR recovery notes document exact install command and PATH fix.
- `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/STATE.md`, and `.planning/config.json` exist after GSD recovery execution.
- `pytest tests/privacy/test_no_runtime_network.py` passes once implementation reaches MVP.
- `pytest tests/postprocess/test_spanglish_glossary.py` passes with fixtures including `mergear el PR`, `hacer deploy`, `pushea el hotfix`.
- `pytest tests/models/test_missing_model.py` passes and proves missing local models do not trigger downloads.
- `pytest tests/e2e/test_notepad_paste.py` passes on Windows for immediate paste mode.

### Must Have
- Windows-first, user-mode app: no admin rights required for normal use.
- Strict runtime offline guarantee: no audio/text/model fetch/telemetry calls at runtime.
- Backend-switchable architecture: ASR, VAD, paste, post-processing, and model management behind interfaces.
- Default shipping ASR backend: `whisper.cpp` with local quantized multilingual Whisper-family models.
- Dev/benchmark ASR backend: `faster-whisper`/CTranslate2 for NVIDIA RTX machine.
- GUI shell: PySide6/Qt by default, with WPF and Tauri documented as fallback decisions.
- Audio capture: `sounddevice`/PortAudio/WASAPI first; PyAudio fallback only.
- VAD: WebRTC VAD default fast path; Silero VAD accurate/noisy-room profile.
- Paste transport: native Win32 clipboard + `SendInput`, preserving/restoring clipboard where feasible.

### Must NOT Have
- No production app code in planning phase.
- No cloud ASR, paid APIs, accounts, sync, telemetry, runtime auto-update, or cloud fallback.
- No in-app runtime model downloads.
- No retained audio/transcript logs by default.
- No GPL-only dependency unless project license is deliberately changed to GPL-compatible.
- No assumption that paste into all apps is trivial; it must have dedicated QA.
- No `.planning/` writes from Prometheus mode; recover GSD tooling first.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed.
- Test decision: tests-after for this plan; TDD may be used during implementation phases once repo scaffolding exists.
- QA policy: Every task has agent-executed scenarios.
- Evidence: `.sisyphus/evidence/task-{N}-{slug}.{ext}`.

## Execution Strategy

### Parallel Execution Waves
Wave 1: Task 1 only — recover/document GSD tooling and create planning source of truth.
Wave 2: Tasks 2-3 — architecture/privacy/licensing and ASR/VAD benchmark design.
Wave 3: Tasks 4-5 — MVP dictation loop and model profiles.
Wave 4: Tasks 6-7 — GUI/tray polish and glossary/post-processing.
Wave 5: Task 8 + final verification — packaging/release and review agents.

### Mapping to User-Requested Roadmap Phases
| User-Requested Phase | Plan Coverage |
|---|---|
| Phase 1: planning and architecture only | Task 1 recovery, Task 2 architecture/privacy/licensing, Task 3 ASR/VAD/model benchmark design and results |
| Phase 2: MVP offline dictation | Task 4 |
| Phase 3: model profiles and switching | Task 5 |
| Phase 4: GUI/tray polish | Task 6 |
| Phase 5: Spanglish technical glossary and post-processing | Task 7 |
| Phase 6: packaging, installer, and GitHub release | Task 8 |

Task 1 is a recovery prerequisite caused by missing `gsd-sdk`; it does not alter product scope.

### Dependency Matrix
| Task | Depends On | Blocks |
|---|---|---|
| 1. Recover GSD tooling and planning artifacts | None | 2, 3, 4, 5, 6, 7, 8 |
| 2. Lock architecture, privacy, licensing decisions | 1 | 4, 5, 6, 7, 8 |
| 3. Benchmark ASR/VAD/model candidates | 1 | 4, 5 |
| 4. Build MVP offline dictation loop | 2, 3 | 5, 6, 7, 8 |
| 5. Add model profiles and local model manager | 3, 4 | 8 |
| 6. Add GUI/tray polish and confirmation mode | 4 | 8 |
| 7. Add deterministic Spanglish glossary | 4 | 8 |
| 8. Package, license, and release | 5, 6, 7 | Final verification |

### Agent Dispatch Summary
| Wave | Task Count | Categories |
|---|---:|---|
| 1 | 1 | quick |
| 2 | 2 | deep, unspecified-high |
| 3 | 2 | deep, unspecified-high |
| 4 | 2 | visual-engineering, unspecified-high |
| 5 | 1 + 4 final reviews | deep, oracle, unspecified-high |

## TODOs
> Implementation + Test = ONE task. Never separate.
> EVERY task MUST have: Agent Profile + Parallelization + QA Scenarios.

- [ ] 1. Recover GSD tooling and generate planning artifacts — BLOCKED/PARTIAL

  **Current status**: Recovery attempts are documented in `.planning/TOOLING-RECOVERY.md` and `.sisyphus/evidence/task-1-gsd-recovery.txt`, but canonical `.planning/PROJECT.md`, `.planning/config.json`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, and `.planning/STATE.md` are still absent because `gsd-sdk` remains shell-invisible.

  **What to do**: Diagnose missing `gsd-sdk`, install/recover the minimal GSD tooling, then generate `.planning/` artifacts from the decisions in this plan. First try `where.exe gsd-sdk`. If missing, run the minimal recovery command `npx get-shit-done-cc@latest --global`, restart or refresh PATH, and re-run `where.exe gsd-sdk`. Then execute `/gsd-new-project` or equivalent GSD flow using this plan as the source document. Set config defaults: YOLO mode only if user approves later; coarse granularity; parallel execution; commit planning docs; research/plan-check/verifier enabled; no runtime network as a project invariant.
  **Must NOT do**: Do not create production app code. Do not hand-write `.planning/` while `gsd-sdk` is unavailable unless the user explicitly approves a fallback outside Prometheus.

  **Recommended Agent Profile**:
  - Category: `quick` - Tooling recovery and artifact creation are procedural once command availability is fixed.
  - Skills: [`git-master`] - Only if committing planning artifacts is requested by the workflow.
  - Omitted: [`frontend-ui-ux`] - No UI implementation yet.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: 2,3,4,5,6,7,8 | Blocked By: none

  **References**:
  - Workflow: `C:\Users\esteb\.config\opencode\get-shit-done\workflows\new-project.md:55-113` - setup/init checks and git handling.
  - Workflow: `C:\Users\esteb\.config\opencode\get-shit-done\workflows\new-project.md:346-452` - `PROJECT.md` creation expectations.
  - Workflow: `C:\Users\esteb\.config\opencode\get-shit-done\workflows\new-project.md:648-670` - `config.json` creation/commit expectations.
  - Template: `C:\Users\esteb\.config\opencode\get-shit-done\templates\project.md` - project context structure.
  - Template: `C:\Users\esteb\.config\opencode\get-shit-done\templates\requirements.md` - requirements structure and traceability.

  **Acceptance Criteria**:
  - [ ] `where.exe gsd-sdk` exits `0`, or `.planning/TOOLING-RECOVERY.md` records `npx get-shit-done-cc@latest --global` as required recovery and explains PATH status.
  - [ ] `.planning/PROJECT.md` includes offline Windows Spanglish dictation scope, strict no-runtime-network privacy, target hardware, and out-of-scope cloud/telemetry/account/sync exclusions.
  - [ ] `.planning/config.json` exists and records workflow preferences.
  - [ ] `.planning/REQUIREMENTS.md` and `.planning/ROADMAP.md` exist with no production code created.

  **QA Scenarios**:
  ```
  Scenario: GSD SDK available after recovery
    Tool: Bash
    Steps: Run `where.exe gsd-sdk`; if missing, run `npx get-shit-done-cc@latest --global`, refresh PATH, then run `where.exe gsd-sdk` again.
    Expected: gsd-sdk path is printed, or recovery document exists explaining why PATH is still unresolved.
    Evidence: .sisyphus/evidence/task-1-gsd-recovery.txt

  Scenario: No app code created during planning recovery
    Tool: Bash
    Steps: Run `git status --short` and inspect changed files.
    Expected: Changes are limited to `.planning/`, `.sisyphus/`, and optional `AGENTS.md`; no `src/`, app package, or production code files exist.
    Evidence: .sisyphus/evidence/task-1-no-app-code.txt
  ```

  **Commit**: YES | Message: `docs(planning): initialize offline dictation project` | Files: `.planning/*`, `AGENTS.md` if generated

- [x] 2. Lock architecture, privacy, and licensing decisions

  **What to do**: Create architecture docs under `.planning/` that define the modular monolith, interfaces, dataflow, worker-process concurrency, privacy guardrails, and license matrix. Record stack decision: Python + PySide6/Qt shell, native Win32 integration through `pywin32`/`ctypes`, `sounddevice` audio, WebRTC VAD default, Silero VAD accurate profile, whisper.cpp shipping backend, faster-whisper dev/benchmark backend. Include fallback decisions: WPF if native Windows UX overtakes Python ASR convenience; Tauri if web/Rust footprint becomes preferred. Define no-runtime-network enforcement and zero-retention default logging.
  **Must NOT do**: Do not implement modules yet. Do not add GPL-only dependencies without explicit license decision. Do not include local LLM post-processing.

  **Recommended Agent Profile**:
  - Category: `deep` - Requires architecture, privacy, licensing, and distribution tradeoffs.
  - Skills: [] - No special implementation skill required.
  - Omitted: [`frontend-ui-ux`] - Design contract comes later; this is architecture.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 4,5,6,7,8 | Blocked By: 1

  **References**:
  - ASR research: faster-whisper `https://github.com/SYSTRAN/faster-whisper`, whisper.cpp `https://github.com/ggml-org/whisper.cpp`, OpenAI Whisper model card `https://github.com/openai/whisper/blob/main/model-card.md`.
  - Windows APIs: RegisterHotKey `https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-registerhotkey`, SendInput `https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-sendinput`, clipboard APIs `https://learn.microsoft.com/windows/win32/dataxchg/clipboard`.
  - GUI research: Qt tray/topmost support, PySide6 preference over PyQt licensing, WPF/Tauri fallbacks from research summary.
  - Recovery artifact: `.planning/TOOLING-RECOVERY.md` - captured current GSD tooling blocker.

  **Acceptance Criteria**:
  - [ ] `.planning/architecture/ARCHITECTURE.md` defines module boundaries: `ShellIntegration`, `AudioCapture`, `SpeechDetector`, `Transcriber`, `ModelManager`, `PostProcessor`, `PasteController`, `PrivacyGuard`, `SettingsStore`, `Diagnostics`.
  - [ ] `.planning/architecture/PRIVACY.md` states no runtime network, no telemetry, no cloud fallback, no retained audio/transcripts by default, redacted diagnostics only.
  - [ ] `.planning/architecture/LICENSE-MATRIX.md` lists app license, Qt/PySide6, whisper.cpp, model weights, faster-whisper/CTranslate2, CUDA/cuDNN redistribution status, WebRTC VAD, Silero VAD, sounddevice/PortAudio, pywin32, installer tooling, and model release artifacts.
  - [ ] `.planning/architecture/INTERFACES.md` defines replaceable backend interfaces for ASR, VAD, model manager, paste transport, and post-processing.

  **QA Scenarios**:
  ```
  Scenario: Architecture docs cover required modules
    Tool: Bash
    Steps: Run a script/grep that checks ARCHITECTURE.md for all required module names.
    Expected: All module names are present exactly as listed in acceptance criteria.
    Evidence: .sisyphus/evidence/task-2-architecture-coverage.txt

  Scenario: Privacy doc forbids runtime network
    Tool: Bash
    Steps: Search PRIVACY.md for `no runtime network`, `no telemetry`, `no cloud fallback`, and `no retained audio`.
    Expected: All phrases are present with enforcement guidance and test references.
    Evidence: .sisyphus/evidence/task-2-privacy-guardrails.txt
  ```

  **Commit**: YES | Message: `docs(architecture): define offline dictation architecture` | Files: `.planning/architecture/*`

- [ ] 3. Benchmark ASR, VAD, and model candidates before locking defaults — BLOCKED/PARTIAL

  **Current status**: Benchmark plan, fixture definitions, placeholder matrix, and missing-model offline contract exist under `.planning/benchmarks/`, but real latency/RAM/VRAM/accuracy measurements remain pending local model/VAD side-load and local benchmark execution.

  **What to do**: Design and run reproducible benchmarks using local audio fixtures for technical Spanglish. Compare whisper.cpp CPU quantized models (`tiny`, `base`, `small`, `medium-q5_0`, `large-v3-turbo-q5_0`), faster-whisper/CTranslate2 on RTX dev machine (`large-v3-turbo` float16/int8_float16), OpenAI Whisper reference as baseline, WebRTC VAD, and Silero VAD. Measure speech-end-to-text latency, transcription quality on Spanglish phrases, CPU/RAM/VRAM, model load time, and failure behavior.
  **Must NOT do**: Do not download models at runtime inside the app. Do not benchmark English-only Distil-Whisper as default Spanglish path.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Requires experimental design and reproducibility.
  - Skills: [] - No UI skill needed.
  - Omitted: [`git-master`] - Only commit benchmark docs/artifacts after results are generated.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: 4,5 | Blocked By: 1

  **References**:
  - Model strategy: whisper.cpp model docs `https://github.com/ggml-org/whisper.cpp/blob/master/models/README.md`.
  - CTranslate2 docs: `https://opennmt.net/CTranslate2/installation.html`, `https://opennmt.net/CTranslate2/hardware_support.html`.
  - VAD sources: WebRTC VAD `https://github.com/wiseman/py-webrtcvad`, Silero VAD `https://github.com/snakers4/silero-vad`.

  **Acceptance Criteria**:
  - [ ] `.planning/benchmarks/ASR-VAD-BENCHMARK.md` contains a table with latency, RAM/VRAM, load time, and qualitative Spanglish accuracy for each tested model/backend.
  - [ ] Benchmark fixtures include at least: `mergear el PR`, `hacer deploy`, `abre el branch de staging`, `corre los tests`, `pushea el hotfix`, `rollback en producción`.
  - [ ] Recommended defaults are updated only after benchmark evidence: CPU portable, CPU high-accuracy, NVIDIA dev.
  - [ ] Missing/corrupt model behavior is documented and confirms no network attempt.

  **QA Scenarios**:
  ```
  Scenario: Benchmark matrix complete
    Tool: Bash
    Steps: Run benchmark harness and produce `.planning/benchmarks/results.json`; validate required backend/model rows exist.
    Expected: Results include whisper.cpp CPU quantized rows, faster-whisper GPU row if RTX available, and VAD comparison rows.
    Evidence: .sisyphus/evidence/task-3-benchmark-results.json

  Scenario: Missing model does not download
    Tool: Bash
    Steps: Run missing-model benchmark with network blocked and model path invalid.
    Expected: Error says local model missing; no network socket/file download attempt occurs.
    Evidence: .sisyphus/evidence/task-3-missing-model-offline.txt
  ```

  **Commit**: YES | Message: `docs(benchmarks): record offline asr vad decisions` | Files: `.planning/benchmarks/*`, updated architecture docs

- [ ] 4. Build MVP offline dictation loop — BLOCKED

  **Current status**: Blocked by missing usable Python/test tooling. No production MVP code was created. See `.sisyphus/drafts/task-4-mvp-blocker.md`.

  **What to do**: Implement the smallest app loop after planning/architecture is complete: tray process, global hotkey hybrid activation, microphone capture, WebRTC VAD segmentation, whisper.cpp CPU backend, deterministic minimal post-processing, immediate paste via Win32 clipboard/SendInput, and error states for no microphone/missing model/busy transcription. Use a transcription worker process and bounded queues. Include confirmation-mode scaffolding only if it does not delay immediate-paste MVP.
  **Must NOT do**: Do not add polished settings UI, full glossary, runtime downloads, telemetry, cloud ASR, or installer yet.

  **Recommended Agent Profile**:
  - Category: `deep` - Cross-cuts audio, Windows APIs, worker processes, and privacy tests.
  - Skills: [] - No extra skill required.
  - Omitted: [`frontend-ui-ux`] - MVP UI should be minimal; polish comes later.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: 5,6,7,8 | Blocked By: 2,3

  **References**:
  - Architecture docs from Task 2.
  - Benchmark decisions from Task 3.
  - Windows integration research: native `RegisterHotKey`, `SendInput`, clipboard restore, focus-change caveats.
  - Audio/VAD research: `sounddevice`, WebRTC VAD constraints: 16-bit mono PCM, 10/20/30ms frames at 8/16/32/48kHz.

  **Acceptance Criteria**:
  - [ ] App runs on Windows without admin rights.
  - [ ] Push-to-talk path records one utterance, transcribes offline, and pastes into Notepad.
  - [ ] Toggle path starts/stops recording and does not leave recorder/transcriber stuck busy.
  - [ ] Clipboard previous text is restored after immediate paste where feasible.
  - [ ] `pytest tests/privacy/test_no_runtime_network.py` passes.
  - [ ] `pytest tests/e2e/test_notepad_paste.py` passes with expected final text `mergear el PR`.

  **QA Scenarios**:
  ```
  Scenario: Happy path immediate paste into Notepad
    Tool: Bash + Windows automation
    Steps: Launch Notepad, start app, trigger push-to-talk with fixture audio `mergear_el_pr.wav`, wait for transcription, inspect Notepad text.
    Expected: Notepad contains exactly `mergear el PR` or benchmark-approved normalized equivalent; app logs no transcript text.
    Evidence: .sisyphus/evidence/task-4-notepad-paste.txt

  Scenario: No microphone available
    Tool: Bash
    Steps: Run app with audio device mocked unavailable, trigger dictation.
    Expected: Status panel/tray reports microphone unavailable; app does not crash; no transcription starts.
    Evidence: .sisyphus/evidence/task-4-no-microphone.txt
  ```

  **Commit**: YES | Message: `feat(mvp): add offline dictation loop` | Files: implementation files, tests, docs

- [ ] 5. Add local model manager and hardware profiles — BLOCKED

  **Current status**: Blocked by missing Task 4 MVP scaffold, missing Python/test tooling, and missing local model assets. No model manager code or model registry implementation was created. See `.sisyphus/drafts/task-5-model-profiles-blocker.md`.

  **What to do**: Implement local-only model registry, profile selection, hardware detection, model import, checksum verification, and backend switching. Profiles: CPU Portable (`whisper.cpp` + benchmark-selected quantized multilingual model), CPU High Accuracy (`whisper.cpp` + `large-v3-turbo-q5_0` if benchmark approves), NVIDIA Dev (`faster-whisper` + `large-v3-turbo` float16/int8_float16), Reference Baseline (OpenAI Whisper, dev/test only). Model files must be local user-managed assets with source URL, license, checksum, size, and expected RAM/VRAM.
  **Must NOT do**: Do not implement runtime model download. Do not bundle models into git history. Do not assume CUDA/cuDNN redistribution is allowed without license matrix approval.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Requires filesystem, hardware detection, profile logic, and licensing guardrails.
  - Skills: [] - No special skill needed.
  - Omitted: [`frontend-ui-ux`] - Settings UI comes in Task 6.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: 8 | Blocked By: 3,4

  **References**:
  - Task 3 benchmark matrix.
  - Task 2 license matrix.
  - ASR research defaults: whisper.cpp shipping, faster-whisper dev/benchmark, OpenAI Whisper baseline only.

  **Acceptance Criteria**:
  - [ ] `pytest tests/models/test_profile_selection.py` maps target hardware to expected profile.
  - [ ] `pytest tests/models/test_missing_model.py` reports missing local model and performs zero network calls.
  - [ ] `pytest tests/models/test_checksum_validation.py` rejects corrupted model files.
  - [ ] Model registry includes source URL, license, checksum, size, backend compatibility, and recommended hardware for every profile.

  **QA Scenarios**:
  ```
  Scenario: CPU-only laptop chooses portable profile
    Tool: Bash
    Steps: Run profile selection test with mocked Intel CPU-only hardware and no GPU.
    Expected: CPU Portable profile selected; no CUDA/faster-whisper dependency required.
    Evidence: .sisyphus/evidence/task-5-cpu-profile.txt

  Scenario: Corrupt model rejected offline
    Tool: Bash
    Steps: Place invalid model file with expected name and run checksum validation.
    Expected: App reports checksum mismatch and never attempts network repair/download.
    Evidence: .sisyphus/evidence/task-5-corrupt-model.txt
  ```

  **Commit**: YES | Message: `feat(models): add local model profiles` | Files: model manager files, tests, docs

- [ ] 6. Add GUI/tray polish, floating panel, and confirmation mode — BLOCKED

  **Current status**: Blocked by missing Task 4 MVP scaffold and unavailable GUI/Python tooling. No PySide6 GUI/tray code was created. See `.sisyphus/drafts/task-6-gui-blocker.md`.

  **What to do**: Build PySide6/Qt tray UX, topmost floating status panel, settings panel for hotkeys/model/profile/paste mode, confirmation/edit-before-paste mode, status states, and non-blocking worker event updates. Confirm panel must not steal focus unexpectedly; immediate paste remains default. Add WPF/Tauri decision notes as documented fallback only, not parallel implementation.
  **Must NOT do**: Do not rewrite the stack to Electron/Tauri/WPF unless a decision document explicitly supersedes PySide6. Do not add heavy visual redesign beyond functional Windows-native polish.

  **Recommended Agent Profile**:
  - Category: `visual-engineering` - UI/tray/status polish and interaction quality matter.
  - Skills: [`frontend-ui-ux`] - Use for topmost panel usability and Windows-native polish.
  - Omitted: [`git-master`] - Only needed at commit time.

  **Parallelization**: Can Parallel: YES | Wave 4 | Blocks: 8 | Blocked By: 4

  **References**:
  - GUI research: PySide6/Qt default, Qt `QSystemTrayIcon`, `WindowStaysOnTopHint`; WPF/Tauri fallback notes.
  - User decision: both paste modes, immediate default plus confirmation/edit mode.
  - Task 4 MVP status/error states.

  **Acceptance Criteria**:
  - [ ] Tray icon exposes Start/Stop, Settings, Profile, Paste Mode, Exit.
  - [ ] Floating panel shows Idle, Listening, Processing, Ready, Error states without blocking transcription.
  - [ ] Confirmation mode allows edit/accept/cancel and pastes only after accept.
  - [ ] Immediate paste remains default and works without opening confirmation panel.
  - [ ] UI event loop remains responsive while transcriber worker is processing.

  **QA Scenarios**:
  ```
  Scenario: Confirmation mode edit then paste
    Tool: Playwright or Windows GUI automation
    Steps: Enable confirmation mode, transcribe fixture `mergear_el_pr.wav`, edit panel text to `mergear el PR revisado`, accept, inspect Notepad.
    Expected: Notepad contains edited text; original focus behavior is documented; clipboard restored.
    Evidence: .sisyphus/evidence/task-6-confirmation-mode.png

  Scenario: Worker busy does not freeze UI
    Tool: Bash + GUI automation
    Steps: Run a long transcription fixture while toggling tray menu and moving panel.
    Expected: UI remains responsive; status panel shows Processing; no main-thread hang.
    Evidence: .sisyphus/evidence/task-6-ui-responsive.txt
  ```

  **Commit**: YES | Message: `feat(ui): add tray panel and confirmation mode` | Files: UI files, tests, docs

- [ ] 7. Add deterministic technical Spanglish glossary and post-processing — BLOCKED

  **Current status**: Blocked by missing Python/test tooling and missing Task 4 scaffold. No glossary implementation or tests were created. See `.sisyphus/drafts/task-7-glossary-blocker.md`.

  **What to do**: Implement user-editable deterministic glossary and normalization rules for technical Spanglish. MVP rules must preserve code-switching and casing for terms like `PR`, `deploy`, `branch`, `staging`, `tests`, `hotfix`, `endpoint`, `commit`, `repo`, `rollback`, `producción`, `CI/CD`, `GitHub`. Add import/export for user glossary. Keep post-processing deterministic; local LLM rewriting remains explicitly out of scope.
  **Must NOT do**: Do not change user meaning. Do not auto-translate Spanglish into English or Spanish. Do not use cloud or local LLM for MVP glossary.

  **Recommended Agent Profile**:
  - Category: `unspecified-high` - Requires careful text normalization and fixture-driven tests.
  - Skills: [] - No UI skill unless glossary editor UI is included in Task 6.
  - Omitted: [`frontend-ui-ux`] - Glossary logic can be built independently of UI polish.

  **Parallelization**: Can Parallel: YES | Wave 4 | Blocks: 8 | Blocked By: 4

  **References**:
  - User examples in original request.
  - Oracle recommendation: start with deterministic glossary/casing/punctuation rules before local AI.
  - Metis warning: avoid scope creep into AI writing assistant.

  **Acceptance Criteria**:
  - [ ] `pytest tests/postprocess/test_spanglish_glossary.py` passes all user-provided fixture phrases.
  - [ ] User glossary import/export round-trips without losing casing or accents.
  - [ ] Rules preserve Spanglish phrasing and only normalize approved technical terms/casing.
  - [ ] Logs do not store raw transcript before/after post-processing by default.

  **QA Scenarios**:
  ```
  Scenario: User-provided Spanglish fixtures normalize correctly
    Tool: Bash
    Steps: Run `pytest tests/postprocess/test_spanglish_glossary.py`.
    Expected: `mergear el pr` -> `mergear el PR`; `pushea el hotfix` remains `pushea el hotfix`; accents are preserved.
    Evidence: .sisyphus/evidence/task-7-glossary-tests.txt

  Scenario: Glossary does not translate meaning
    Tool: Bash
    Steps: Run negative fixtures where English/Spanish code-switching should remain mixed.
    Expected: No fixture is fully translated or rewritten beyond approved glossary/casing rules.
    Evidence: .sisyphus/evidence/task-7-no-translation.txt
  ```

  **Commit**: YES | Message: `feat(postprocess): add technical spanglish glossary` | Files: post-processing files, tests, docs

- [ ] 8. Package, license, and publish GitHub release artifacts — BLOCKED

  **Current status**: Blocked by incomplete Tasks 4-7. No package pipeline, installer, SBOM generator, model bundle, or release artifact was created. See `.sisyphus/drafts/task-8-packaging-blocker.md`.

  **What to do**: Create Windows packaging and release pipeline after MVP/profile/UI/glossary are stable. Preferred sequence: portable zip first, installer second. Include local model side-load instructions, optional release assets for model bundles if legally approved, checksums, SBOM, license notices, privacy statement, hardware profile table, and offline install/use docs. Installer must be per-user and not require admin for normal use. Code signing is optional initially but documented for future corporate friendliness.
  **Must NOT do**: Do not bundle models or CUDA/cuDNN DLLs unless license matrix explicitly allows it. Do not enable auto-update or runtime network checks.

  **Recommended Agent Profile**:
  - Category: `deep` - Packaging, licensing, and privacy guarantees need careful validation.
  - Skills: [] - No special UI skill required.
  - Omitted: [`frontend-ui-ux`] - UI polish already handled.

  **Parallelization**: Can Parallel: NO | Wave 5 | Blocks: Final verification | Blocked By: 5,6,7

  **References**:
  - Task 2 license matrix.
  - Task 5 model registry.
  - User constraint: open source, legal to publish on GitHub, cloneable/installable, no cloud services or paid APIs.

  **Acceptance Criteria**:
  - [ ] Release artifact installs/runs on Windows user account without admin for normal use.
  - [ ] `LICENSES/` or equivalent notice bundle covers every runtime dependency and model asset.
  - [ ] SBOM is generated and committed/published with release.
  - [ ] Offline smoke test passes with network disabled.
  - [ ] GitHub release docs explain model side-loading, checksums, privacy guarantee, and supported hardware profiles.

  **QA Scenarios**:
  ```
  Scenario: Offline portable release smoke test
    Tool: Bash + Windows automation
    Steps: Disable network, unpack release zip, place local model in documented folder, launch app, run Notepad paste fixture.
    Expected: App runs, transcribes, pastes, and makes zero network calls.
    Evidence: .sisyphus/evidence/task-8-offline-release-smoke.txt

  Scenario: License bundle complete
    Tool: Bash
    Steps: Run license/SBOM validation script against dependency manifest and model registry.
    Expected: Every dependency/model has license, source URL, checksum where applicable, and redistribution status.
    Evidence: .sisyphus/evidence/task-8-license-sbom.txt
  ```

  **Commit**: YES | Message: `chore(release): add windows packaging pipeline` | Files: packaging files, release docs, license notices, tests

## Final Verification Wave (MANDATORY — after ALL implementation tasks)
> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.
> **Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.**
> **Never mark F1-F4 as checked before getting user's okay.** Rejection or user feedback -> fix -> re-run -> present again -> wait for okay.
- [ ] F1. Plan Compliance Audit — oracle
- [ ] F2. Code Quality Review — unspecified-high
- [ ] F3. Real Manual QA — unspecified-high (+ playwright/Windows automation for UI)
- [ ] F4. Scope Fidelity Check — deep

## Commit Strategy
- Commit planning/tooling artifacts first so context survives interruptions.
- Commit architecture/privacy/licensing docs independently before implementation.
- Commit benchmark results before MVP implementation so model defaults are evidence-based.
- Commit each implementation task atomically with tests and docs.
- Do not commit models into git history; use release assets or documented local side-load paths.
- Do not push remote or create GitHub releases unless explicitly requested.

## Success Criteria
- The project has a recoverable `.planning/` source of truth after GSD SDK recovery.
- Architecture decisions are explicit and backend-switchable.
- Runtime network is impossible or test-failing if introduced.
- CPU-only Windows laptop profile works offline with local quantized model.
- RTX dev path can benchmark higher-accuracy/faster profiles without becoming required for users.
- Dictation can paste into Notepad and representative Windows apps while preserving clipboard where feasible.
- Technical Spanglish examples are preserved/normalized deterministically.
- GitHub release is legally publishable with model/dependency licenses documented.
