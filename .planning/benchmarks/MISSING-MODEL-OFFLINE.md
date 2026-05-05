# Missing or Corrupt Model Offline Contract

Status: Task 3 failure-behavior contract.

## Required Failure Outcome

When a benchmark candidate has a missing or corrupt local model or VAD asset, the benchmark path must:

1. fail locally
2. emit a local error category such as `missing_model` or `corrupt_model`
3. provide side-load guidance that points to documentation only
4. make no network attempt
5. make no runtime download attempt
6. make no cloud fallback attempt

## Observable Evidence Required Later

- Invalid local model path produces a local-only error.
- Network-blocked test environment shows no socket or HTTP activity.
- No new model file appears in the repo or working directory after the run.
- Diagnostics remain redacted and contain no raw audio or transcript text.

## Current Task 3 Result

- No local model files were discovered in this repository during Task 3.
- No benchmark candidate was executed.
- No model download or installer step was performed.
- Benchmark rows therefore remain pending local side-load and local execution.
