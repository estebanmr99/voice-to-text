# ASR and VAD Benchmark Plan

Status: Task 3 benchmark design and placeholder evidence for offline Windows technical Spanglish dictation.

## Goal

Choose evidence-backed defaults for offline ASR and VAD without creating production app code and without any runtime downloads.

This benchmark plan is aligned with the locked architecture:

- `whisper.cpp` is the shipping CPU backend candidate.
- `faster-whisper`/CTranslate2 is the NVIDIA dev and benchmark backend candidate.
- OpenAI Whisper is a local reference baseline only.
- WebRTC VAD is the default fast-path VAD candidate.
- Silero VAD is the accurate and noisy-room VAD candidate.

Current repo state: no local model artifacts were found during this task, so every candidate row remains pending local benchmark execution.

## Hard Constraints

- Windows-first execution.
- Technical Spanglish dictation focus.
- no runtime network
- no telemetry
- no cloud fallback
- no retained audio
- no retained transcripts by default
- no runtime model download
- local missing or corrupt model paths must return local errors only

## Fixture Set

Required phrase fixtures:

1. `mergear el PR`
2. `hacer deploy`
3. `abre el branch de staging`
4. `corre los tests`
5. `pushea el hotfix`
6. `rollback en producción`

Recommended fixture expansion for local runs:

- Short command phrase, normal pace.
- Short command phrase, fast pace.
- Phrase with background fan noise.
- Phrase with keyboard noise.
- Phrase with a pause before the technical English token.
- Phrase with code-switch emphasis on `PR`, `branch`, `tests`, and `hotfix`.

See `.planning/benchmarks/FIXTURES.md` for the reproducible fixture recording template.

## Benchmark Columns

Every ASR row must capture:

- backend
- model
- hardware profile
- backend status
- speech-end-to-text latency
- RAM/VRAM
- model load time
- qualitative Spanglish accuracy
- failure behavior

Every VAD row must capture:

- backend
- profile
- hardware profile
- backend status
- speech-end detection latency
- RAM
- model load time
- qualitative segment quality on Spanglish fixtures
- failure behavior

Until a local asset exists, each metric stays `pending local benchmark` and status stays `not yet runnable - local model missing` or `not yet runnable - local VAD asset missing`.

## Candidate Matrix

| Type | Backend | Model or Profile | Hardware Profile | Status | Speech-End-to-Text or Detection Latency | RAM/VRAM | Model Load Time | Qualitative Spanglish Accuracy | Failure Behavior |
|---|---|---|---|---|---|---|---|---|---|
| ASR | whisper.cpp | `tiny` quantized CPU | CPU portable | not yet runnable - local model missing | pending local benchmark | pending local benchmark | pending local benchmark | pending local benchmark | local error only, no network attempt |
| ASR | whisper.cpp | `base` quantized CPU | CPU portable | not yet runnable - local model missing | pending local benchmark | pending local benchmark | pending local benchmark | pending local benchmark | local error only, no network attempt |
| ASR | whisper.cpp | `small` quantized CPU | CPU portable | not yet runnable - local model missing | pending local benchmark | pending local benchmark | pending local benchmark | pending local benchmark | local error only, no network attempt |
| ASR | whisper.cpp | `medium-q5_0` CPU | CPU high accuracy | not yet runnable - local model missing | pending local benchmark | pending local benchmark | pending local benchmark | pending local benchmark | local error only, no network attempt |
| ASR | whisper.cpp | `large-v3-turbo-q5_0` CPU | CPU high accuracy | not yet runnable - local model missing | pending local benchmark | pending local benchmark | pending local benchmark | pending local benchmark | local error only, no network attempt |
| ASR | faster-whisper/CTranslate2 | `large-v3-turbo` `float16` | NVIDIA RTX dev | not yet runnable - local model missing | pending local benchmark | pending local benchmark | pending local benchmark | pending local benchmark | local error only, no network attempt |
| ASR | faster-whisper/CTranslate2 | `large-v3-turbo` `int8_float16` | NVIDIA RTX dev | not yet runnable - local model missing | pending local benchmark | pending local benchmark | pending local benchmark | pending local benchmark | local error only, no network attempt |
| ASR | OpenAI Whisper reference baseline | local reference baseline | Reference baseline | not yet runnable - local model missing | pending local benchmark | pending local benchmark | pending local benchmark | pending local benchmark | local error only, no network attempt |
| VAD | WebRTC VAD | default fast-path profile | CPU default | not yet runnable - local VAD asset missing | pending local benchmark | pending local benchmark | pending local benchmark | pending local benchmark | local error only, no network attempt |
| VAD | Silero VAD | accurate or noisy-room profile | CPU accurate | not yet runnable - local VAD asset missing | pending local benchmark | pending local benchmark | pending local benchmark | pending local benchmark | local error only, no network attempt |

## Reproducible Local Run Plan

1. Side-load candidate model files into a user-managed local model directory outside git.
2. Record exact local path, checksum, size, and backend compatibility in a local-only run sheet.
3. Record audio fixtures on the target microphone and target Windows hardware profile.
4. Run each ASR candidate on the exact same fixture set.
5. Run each VAD candidate on the exact same fixture set and note segment-boundary quality.
6. Capture at least three runs per row and report median latency.
7. Record missing-model and corrupt-model behavior before any valid-model run.

## Suggested Measurement Method

- Latency start: last speech frame accepted by VAD.
- Latency end: final offline transcript emitted to the shell boundary.
- Load time: backend process start or explicit model load call until ready.
- RAM/VRAM: peak process memory for the backend under the active run.
- Accuracy: qualitative pass or fail for technical token preservation and code-switch correctness.

Suggested qualitative rubric:

- Pass: preserves technical English token and Spanish framing with no meaning change.
- Soft fail: understandable but drops casing or article words.
- Hard fail: mistranscribes technical token, merges languages incorrectly, or drops the command intent.

## Default Selection Gates

Do not lock defaults until local evidence exists.

Provisional target buckets after local benchmark execution:

- CPU portable default: fastest acceptable whisper.cpp candidate that passes all required fixtures.
- CPU high-accuracy profile: highest-accuracy whisper.cpp candidate whose latency is still usable for dictation.
- NVIDIA dev profile: faster-whisper/CTranslate2 row with best balance of latency and Spanglish accuracy on RTX hardware.
- Default VAD: WebRTC if latency and segmentation quality are acceptable.
- Accurate VAD: Silero if it materially improves noisy-room segmentation enough to justify footprint.

## Missing and Corrupt Model Behavior

Required behavior for every candidate:

- Return a local `missing_model` or `corrupt_model` style error.
- Surface side-load guidance pointing to documentation, not runtime fetch logic.
- Make no network request, no socket attempt, no downloader invocation, and no cloud fallback attempt.
- Leave the working directory and git history free of downloaded model files.

See `.planning/benchmarks/MISSING-MODEL-OFFLINE.md` for the explicit offline failure contract.

## Intentional Exclusions

- English-only Distil-Whisper is intentionally excluded from the default Spanglish path.
- No production benchmark harness code is created in this task.
- No app implementation, package manifest, model bundle, installer, or runtime dependency is created in this task.
