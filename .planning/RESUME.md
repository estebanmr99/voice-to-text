# Session Resume — 2026-05-08

## Current State

| Item | Status |
|------|--------|
| **Milestone** | v1.0 — COMPLETE (100%) |
| **Last Phase** | 06 (Packaging & Release) — DONE |
| **Public Release** | v0.1.0 at github.com/estebanmr99/voice-to-text |
| **Tests** | 394 pass, 3 skip |
| **Next Milestone** | v2.0 — NOT STARTED |

## What's Done (Phases 1-6)

- [x] Phase 1: Architecture, privacy, licensing locked
- [x] Phase 2: MVP dictation loop (audio → VAD → transcribe → paste)
- [x] Phase 3: Model profiles (cpu-portable, cpu-high-accuracy, nvidia-dev)
- [x] Phase 4: GUI/tray polish (settings dialog, confirmation mode, status panel)
- [x] Phase 5: Spanglish glossary (post-processor, import/export)
- [x] Phase 6: Packaging & release (portable zip, SBOM, GitHub release v0.1.0)

## What's Next (V2 Requirements from `.planning/V2-CONTEXT.md`)

### Phase 7: Settings + Push-to-Talk (HIGH PRIORITY)
1. **Fix settings persistence bugs** — merge logic validation, missing keys
2. **True push-to-talk** — hold-to-record, release-to-stop (currently both hotkeys call toggle())
3. **Add new settings keys** — `dictation_mode`, `output_mode`
4. **Update settings dialog** — new sections for output modes

### Phase 8: Model Management Window
1. **Full custom model config** — add/remove/edit models (path, language, backend, n_threads, beam_size, custom name)
2. **Custom profiles** — create/edit/delete profiles with preferred model, fallback order
3. **Model management UI** — NEW `src/model_management_dialog.py`

### Phase 9: Streaming Transcription
1. **Real-time streaming dictation** — text appears while speaking (no intermediate panel)
2. **Segment-based transcription** — send audio in ~2-3s chunks, get interim results
3. **Modify** — `transcriber.py`, `transcriber_worker.py`, `dictation_loop.py`

### Phase 10: Stream-to-Cursor
1. **Character-by-character typing** — Win32 SendInput with VK_PACKET for Unicode
2. **NEW** — `src/typing_controller.py`
3. **Multiple output modes** — "Paste immediate" / "Stream to cursor" / "Confirmation"

## Known Bugs to Fix (Pre-Phase 7)

### Critical
1. Thread race on `_audio_buffer` (`dictation_loop.py:89`) — add `threading.Lock`
2. Pre-compile regex patterns (`post_processor.py:50-55`) — compile once in `__init__`
3. Remove dead Win32 hotkey code (`shell_integration.py:64-83, 552-578`)
4. Fix `glossary.py:28` quadruple-quote bug — `""""Lowercase..."""`
5. Replace `assert` with proper checks (`transcriber.py:208-209`)
6. Non-atomic registry write (`model_manager.py:242-251`) — use temp+rename

### Moderate
7. Deduplicate fallback icon (`main.py:82-111` + `shell_integration.py:592-611`)
8. Extract `_log_event` to shared mixin (4 classes duplicate it)
9. Unify `start()`/`start_continuous()` (`dictation_loop.py:117-162`)
10. Throttle diagnostics rotation (`diagnostics.py:99`)
11. Increase SHA-256 read buffer (`model_manager.py:258`) — 8KB → 1MB
12. Initialize dynamic attributes in `__init__` (`shell_integration.py`)

## Workflow Setup (DONE)

- [x] RTK installed (v0.39.0) — `~/.local/bin/rtk.exe`
- [x] RTK OpenCode plugin — `~/.config/opencode/plugins/rtk.ts`
- [x] AGENTS.md updated with workflow rules
- [x] WORKFLOW.md cheat sheet created
- [x] Graphify index built — `graphify-out/graph.json`

## Model Strategy — Avoid Quota Drain

### The Rule
- **Planning:** GPT-5.5 (included in sub) + OMO DISABLED + Tab: Plan
- **Execution:** DeepSeek V4 Pro (cheap) + OMO ENABLED + Tab: Sisyphus
- **Never use GPT-5.5** unless absolutely necessary (burns quota fast)

### Tab Modes
| OMO State | Tab Modes | When to Use |
|-----------|-----------|-------------|
| DISABLED | Plan, Build | Planning phase (Codex model) |
| ENABLED | Sisyphus (Ultraworker), Hephaestus (Deep Agent), Prometheus (Plan Builder), Atlas (Plan Executor) | Execution phase (DeepSeek V4 Pro) |

### Agent Models (Updated to Cheap)
All OMO agents now use cheap models (DeepSeek V4 Pro, GLM-5.1, Kimi K2.6, MiniMax M2.5) instead of GPT-5.5. Config updated in `~/.config/opencode/oh-my-openagent.json`.

## OMO Agents — Enable/Disable & Guide

### Toggle OMO

| State | opencode.json `plugin` field | Effect |
|-------|------------------------------|--------|
| **DISABLED** (current) | `"plugin": []` | Plan/Build modes, use Codex for planning |
| **ENABLED** | `"plugin": ["oh-my-openagent@latest"]` | Sisyphus/Hephaestus/Prometheus/Atlas modes |

**Quick toggle:**
```bash
# Enable (for execution phase)
cp ~/.config/opencode/"opencode - copia.json" ~/.config/opencode/opencode.json

# Disable (for planning phase)
# Edit opencode.json: change "plugin": ["oh-my-openagent@latest"] to "plugin": []
```
**Restart OpenCode** after changing.

### OMO Agent Roles (Cheap Models)

| Agent | Model | Role | Use For |
|-------|-------|------|---------|
| `sisyphus` | DeepSeek V4 Pro | Ultraworker | Complex features, large refactors |
| `hephaestus` | DeepSeek V4 Pro | Deep Agent | Writing new modules, major rewrites |
| `prometheus` | GLM-5.1 | Plan Builder | Architecture decisions |
| `atlas` | DeepSeek V4 Pro | Plan Executor | DevOps, config, packaging |
| `oracle` | Kimi K2.6 | Researcher | Deep exploration |
| `momus` | GLM-5.1 | Critic | Code review |
| `metis` | GLM-5.1 | Strategist | Complex problems |
| `explore` | DeepSeek V4 Flash | Explorer | Finding patterns (fast) |
| `librarian` | MiniMax M2.5 | Doc manager | Documentation (free) |
| `multimodal-looker` | Kimi K2.6 | Visual | UI/screenshots |
| `sisyphus-junior` | MiniMax M2.5 | Light executor | Quick fixes (free) |

### GSD + OMO Coexistence

**They work together, not against each other:**
- **GSD** = planner/reviewer (uses `gsd-*` agents)
- **OMO** = executor/builder (uses Greek god agents)
- **GSD spawns OMO** during `/gsd-execute`
- **Never run both simultaneously** — sequential only

### New Projects

Both tools are project-agnostic. For a new project:
1. Run `/gsd-new-project` → creates roadmap
2. Run `graphify build` → index codebase
3. Run `/gsd-plan-phase 1` → plan first phase
4. Run `/gsd-execute 1` → OMO agents implement

No per-project setup needed beyond `AGENTS.md` and `.planning/`.

## How to Start Working

### Option A: Fix bugs first (recommended)
```
# OMO DISABLED, Codex model, Tab: Plan, Caveman OFF
# Review bugs, pick one to fix

# Then switch to execution:
# OMO ENABLED, DeepSeek V4 Pro, Tab: Sisyphus, Caveman ON
# Fix bug, commit, test

# Then verify:
# OMO DISABLED, Codex model, Tab: Plan, Caveman OFF
# rtk pytest tests/ -q
```

### Option B: Start Phase 7 (Settings + PTT)
```
# Step 1: Planning
# OMO DISABLED, Codex model, Tab: Plan, Caveman OFF
/gsd-plan-phase Phase 7: Settings + Push-to-Talk
# Review plan

# Step 2: Execution
# OMO ENABLED, DeepSeek V4 Pro, Tab: Sisyphus, Caveman ON
/gsd-execute Phase 7

# Step 3: Verification
# OMO DISABLED, Codex model, Tab: Plan, Caveman OFF
/gsd-eval-review
```

### Option C: Start new milestone v2.0
```
# OMO DISABLED, Codex model, Tab: Plan, Caveman OFF
/gsd-new-milestone "v2.0: Settings + PTT + Models + Streaming"
# Creates roadmap for Phases 7-10
```

## Quick Commands

```bash
# Check token savings
rtk gain

# Run tests
rtk pytest tests/ -q

# Check graph status
graphify query graphify-out/graph.json "DictationLoop"

# Start app
python src/main.py
```

## Files to Know

| File | Purpose |
|------|---------|
| `.planning/STATE.md` | Current project state |
| `.planning/ROADMAP.md` | Phase roadmap |
| `.planning/V2-CONTEXT.md` | V2 requirements |
| `.planning/WORKFLOW.md` | Workflow cheat sheet |
| `AGENTS.md` | Project instructions + workflow rules |
| `src/main.py` | Entry point |
| `src/dictation_loop.py` | State machine (needs thread fix) |
| `src/shell_integration.py` | Hotkeys (needs PTT fix) |

## Next Session Checklist

1. [ ] Decide: fix bugs first OR start Phase 7
2. [ ] Select model: Codex (planning) or DeepSeek V4 Pro (execution)
3. [ ] Enable/disable OMO based on phase
4. [ ] Set caveman mode based on phase
5. [ ] Run `rtk gain` to check savings
6. [ ] Verify graph is current if exploring code
7. [ ] One phase at a time — verify before moving on
