# Eval Dataset

Reference transcription dataset for benchmarking Whisper model accuracy (WER).

## Directory layout

```
data/eval/
  README.md              — This file
  transcripts.jsonl      — 10 ground-truth phrases (English, Spanish, Spanglish, tech)
  01.wav .. 10.wav       — Recorded audio clips (not committed, see below)
```

## Recording eval clips

Use `scripts/record_eval_clips.py` to populate the WAV files on your machine:

```bash
python scripts/record_eval_clips.py
```

This reads each entry from `transcripts.jsonl`, displays the phrase, waits
for Enter, records 3 seconds of audio, and saves `data/eval/{id}.wav`.

To list available input devices and pick a specific one:

```bash
python scripts/record_eval_clips.py --device <index>
```

## Graceful test skipping

The WER benchmark (`scripts/eval_transcription.py`) and all eval-dependent
tests skip gracefully when WAV files are missing.  They check for the
presence of `data/eval/*.wav` before attempting to run — no failure, no
error, just a clean skip message.

## Reference phrases

| ID | Phrase | Language | Category |
|----|--------|----------|----------|
| 01 | Hello, how are you? | en | english, greeting |
| 02 | Buenos días, ¿cómo estás? | es | spanish, greeting |
| 03 | I need to merge the PR to the main branch | en | spanglish, tech |
| 04 | The API endpoint returns a JSON response | en | english, tech |
| 05 | Vamos a hacer el deploy del nuevo feature | es | spanglish, tech |
| 06 | Por favor revísame el PR cuando tengas tiempo | es | spanglish, tech |
| 07 | Create a new repository on GitHub | en | english, tech |
| 08 | El servidor está caído hay que reiniciarlo | es | spanish, tech |
| 09 | Check the CI pipeline for any failing tests | en | english, tech |
| 10 | Necesito instalar las dependencias con pip | es | spanglish, tech |

## Integrity notes

- WAV files are **not** committed to git (listed in `.gitignore`).
- Only `transcripts.jsonl` and `README.md` live in version control.
- The 10 phrases cover English, Spanish, Spanglish code-switching, and
  common technical terms — enough for a representative WER baseline.
