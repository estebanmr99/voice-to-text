# Benchmark Fixtures

Status: reproducible fixture definition for Task 3.

## Required Phrases

1. `mergear el PR`
2. `hacer deploy`
3. `abre el branch de staging`
4. `corre los tests`
5. `pushea el hotfix`
6. `rollback en producción`

## Recording Rules

- Record on Windows using the same microphone path intended for MVP validation.
- Keep fixtures local only and outside git unless a later task explicitly approves sanitized sample storage.
- Save phrase ID, speaker tag, device, sample rate, and room-noise notes in a local-only worksheet.
- Do not upload or download anything during capture.

## Recommended Fixture Variants

For each required phrase, record:

1. Normal pace.
2. Fast pace.
3. Quiet room.
4. Mild fan or keyboard noise.
5. Deliberate emphasis on the technical English token.

## Evaluation Focus

- Preserve technical tokens such as `PR`, `deploy`, `branch`, `tests`, and `hotfix`.
- Preserve Spanish framing and command intent.
- Detect whether VAD clips the first or last token.
- Mark whether punctuation or casing post-processing would be sufficient to repair the transcript.
