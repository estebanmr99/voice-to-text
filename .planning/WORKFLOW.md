# Workflow Cheat Sheet — GSD + OMO + Caveman + RTK

## Quick Reference

| Phase | OMO | Tab Mode | Model | Caveman | Purpose |
|-------|-----|----------|-------|---------|---------|
| Planning | DISABLED | Plan | GPT-5.5 | OFF | Research, architecture, phase plans |
| Execution | ENABLED | Sisyphus/Hephaestus | DeepSeek V4 Pro | ON | Multi-agent implementation |
| Always | — | — | — | — | RTK for CLI compression (60-90%) |
| As needed | — | — | — | — | Graphify for code structure map |

---

## Tab Modes — What You See & When

### Without OMO Plugin (`"plugin": []`)

| Tab Mode | When to Use | What It Does |
|----------|-------------|--------------|
| **Plan** | Research, analysis, architecture | Reads code, creates plans, writes docs |
| **Build** | Write code, fix bugs, implement | Edits files, runs tests, commits changes |

### With OMO Plugin (`"plugin": ["oh-my-openagent@latest"]`)

| Tab Mode | Agent | Role | When to Use |
|----------|-------|------|-------------|
| **Sisyphus — Ultraworker** | sisyphus | Heavy multi-step execution | Complex features, large refactors |
| **Hephaestus — Deep Agent** | hephaestus | Deep code changes | Writing new modules, major rewrites |
| **Prometheus — Plan Builder** | prometheus | Architecture + planning | Design decisions, phase planning with OMO context |
| **Atlas — Plan Executor** | atlas | Infrastructure + config | DevOps, CI/CD, config changes, packaging |

**"Ultrawork" note:** Sisyphus in "ultrawork" variant handles longer, more complex tasks with better context management. Use for phases with many files to change.

---

## Model Strategy — Avoid Quota Drain

### The Problem
Using GPT-5.5 for everything burns through quota fast (happened during planning). Different phases need different model tiers.

### Recommended Model per Phase

| Phase | Model | Why | Cost Tier |
|-------|-------|-----|-----------|
| **Planning** (GSD) | GPT-5.5 | Included in subscription, good reasoning | FREE (sub) |
| **Execution** (OMO) | DeepSeek V4 Pro | Cheap, good code generation | LOW |
| **Quick fixes** | MiniMax M2.5 Free | Free tier, simple changes | FREE |
| **Code review** | GLM-5.1 | Good analysis, cheap | LOW |
| **UI work** | Kimi K2.6 | Good at visual/frontend | LOW |
| **Complex architecture** | GPT-5.4 | Strong reasoning, cheaper than 5.5 | MEDIUM |
| **Debugging** | DeepSeek V4 Flash | Fast, cheap, good for investigation | LOW |

### Models to Avoid (Unless Necessary)
- **GPT-5.5 Pro** — Most expensive, only for critical architecture decisions
- **GPT-5.5** — Expensive, use 5.4 or Codex instead
- **GPT-5.5 Fast** — Still expensive, not worth the speed gain

### How to Switch Models

1. **In OpenCode UI:** Select model from dropdown before starting work
2. **In oh-my-openagent.json:** Edit agent model assignments (see below)
3. **Rule of thumb:** Codex for planning, cheap model for execution

---

## OMO — Enable/Disable & Agent Guide

### How to Enable/Disable OMO

OMO is controlled by the `plugin` array in `~/.config/opencode/opencode.json`:

```json
// DISABLED — use Plan/Build modes with Codex for planning
"plugin": []

// ENABLED — use Sisyphus/Hephaestus/Prometheus/Atlas modes for execution
"plugin": ["oh-my-openagent@latest"]
```

**To toggle:**
```bash
# Enable OMO (for execution phase)
cp ~/.config/opencode/"opencode - copia.json" ~/.config/opencode/opencode.json

# Disable OMO (for planning phase)
# Edit opencode.json: change "plugin": ["oh-my-openagent@latest"] to "plugin": []
```

**Restart OpenCode** after changing the file.

### Updated Agent Models (Cheap Configuration)

Edit `~/.config/opencode/oh-my-openagent.json` to use cheap models:

```json
{
  "agents": {
    "sisyphus": { "model": "opencode-go/deepseek-v4-pro", "variant": "medium" },
    "hephaestus": { "model": "opencode-go/deepseek-v4-pro", "variant": "medium" },
    "prometheus": { "model": "opencode-go/glm-5.1", "variant": "high" },
    "atlas": { "model": "opencode-go/deepseek-v4-pro", "variant": "medium" },
    "oracle": { "model": "opencode-go/kimi-k2.6", "variant": "high" },
    "librarian": { "model": "opencode-go/minimax-m2.5", "variant": "default" },
    "explore": { "model": "opencode-go/deepseek-v4-flash", "variant": "default" },
    "momus": { "model": "opencode-go/glm-5.1", "variant": "high" },
    "metis": { "model": "opencode-go/glm-5.1", "variant": "high" },
    "multimodal-looker": { "model": "opencode-go/kimi-k2.6", "variant": "medium" },
    "sisyphus-junior": { "model": "opencode-go/minimax-m2.5", "variant": "medium" }
  }
}
```

---

## Starting a New Session

### 1. Open OpenCode in Git Bash
```bash
cd /c/Users/esteb/Downloads/voice-to-text
opencode
```

### 2. Set Model (IMPORTANT — before anything else)
- **Planning:** Select `GPT-5.5` from model dropdown
- **Execution:** Select `DeepSeek V4 Pro` (or your cheap model)

### 3. Check Current State
```
rtk gain              # See token savings
graphify query graphify-out/graph.json "DictationLoop"  # Check graph
```

### 4. Set Caveman Mode
```
/caveman off           # Planning phase
/caveman on            # Execution phase
```

### 5. Review Planning State
```
cat .planning/STATE.md
cat .planning/ROADMAP.md
```

---

## Implementing a New Feature / Change

### Step 1: Planning (GSD) — OMO DISABLED, Codex Model

```
# Ensure OMO is disabled (plugin: [])
# Select GPT-5.5 as model
/caveman off

# Describe what you want
"I want to add push-to-talk hold-to-record functionality"

# Let GSD plan the phase
/gsd-plan-phase Phase 7: True Push-to-Talk
```

**What happens:**
1. GSD researches codebase (uses `gsd-*` agents)
2. Creates plan in `.planning/phases/phase-7-*.md`
3. Includes task breakdown, dependencies, success criteria
4. **You review the plan before execution**

### Step 2: Execution (OMO) — OMO ENABLED, Cheap Model

```
# Enable OMO (copy copia file)
# Restart OpenCode
# Select DeepSeek V4 Pro as model
/caveman on

# Execute the plan
/gsd-execute Phase 7
```

**What happens:**
1. OMO spawns agents (sisyphus, hephaestus, etc.)
2. Each agent has isolated context
3. Agents commit changes atomically
4. You see progress, not every detail

### Step 3: Verification

```
/caveman off

# Run tests
rtk pytest tests/ -q

# Code review
/gsd-code-review

# Evaluate goals
/gsd-eval-review
```

---

## GSD vs OMO — How They Coexist

**They are complementary, not competing:**

| Tool | Agents | Tab Modes | Model | Purpose |
|------|--------|-----------|-------|---------|
| **GSD** | `gsd-*` (32 agents) | Plan/Build | GPT-5.5 | Planning, review, verification |
| **OMO** | Greek gods (11 agents) | Sisyphus/Hephaestus/Prometheus/Atlas | DeepSeek V4 Pro | Execution, implementation |

**The workflow:**
```
You: "I want feature X"
  ↓ (Tab: Plan, Model: Codex, OMO: OFF)
GSD (gsd-planner): Creates plan in .planning/phases/
  ↓
You: Review plan
  ↓ (Tab: Sisyphus, Model: DeepSeek V4 Pro, OMO: ON)
GSD (gsd-executor): Spawns OMO agents to execute
  ├── sisyphus: Main implementation
  ├── hephaestus: Writes new code
  └── momus: Reviews the code
  ↓
GSD (gsd-verifier): Checks goals met
  ↓
You: Approve or request changes
```

**Key insight:** GSD *orchestrates*, OMO *executes*. Switch model and OMO state between phases.

---

## GSD vs OMO — Don't Let Them Fight

### Golden Rules

1. **GSD plans (Codex), OMO executes (DeepSeek)** — different models, different phases
2. **One phase at a time** — wait for verification before next
3. **Never run planning during execution** — context pollution
4. **Always verify plan exists** before executing
5. **Disable OMO for planning** — saves tokens, avoids agent confusion

### What NOT to Do

```
# BAD: OMO enabled during planning (burns quota)
/gsd-plan-phase Phase 8    # With OMO ON + GPT-5.5 = quota drain

# BAD: Running OMO without a plan
/gsd-execute Phase 8       # No plan = agents make wrong assumptions

# BAD: Mixing phases
/gsd-plan-phase Phase 8    # Don't plan next phase during execution
```

### What TO Do

```
# GOOD: Sequential workflow with model switching
# Phase 1: Planning
# → Disable OMO, select Codex, Tab: Plan
/gsd-plan-phase Phase 7
# → You review plan

# Phase 2: Execution
# → Enable OMO, select DeepSeek V4 Pro, Tab: Sisyphus
/gsd-execute Phase 7
# → Agents implement

# Phase 3: Verification
# → Disable OMO, select Codex, Tab: Plan
/gsd-eval-review

# Phase 4: Next planning
# → Still Codex, Tab: Plan
/gsd-plan-phase Phase 8
```

---

## Closing Milestones

### 1. Verify All Phases Complete
```
ls .planning/phases/
/gsd-eval-review
```

### 2. Update State
```
cat .planning/STATE.md
```

### 3. Run Full Test Suite
```
rtk pytest tests/ -q
```

### 4. Code Review
```
/gsd-code-review
```

### 5. Mark Milestone Complete
```
# Update ROADMAP.md
# Commit changes
```

---

## Starting a New Milestone

### 1. Create Milestone Structure
```
# OMO DISABLED, Codex model, Tab: Plan
/gsd-new-milestone "v2.0: Settings + PTT + Models + Streaming"
```

### 2. Research Phase
```
# GSD researches domain, existing patterns
# Produces files in .planning/research/
```

### 3. Create Roadmap
```
# GSD creates roadmap with phase breakdown
```

### 4. Execute Phases Sequentially
```
# For each phase:
# 1. Disable OMO, Codex, Tab: Plan → /gsd-plan-phase
# 2. Enable OMO, DeepSeek, Tab: Sisyphus → /gsd-execute
# 3. Disable OMO, Codex, Tab: Plan → /gsd-eval-review
```

---

## Caveman Mode — When to Toggle

| Situation | Caveman | Why |
|-----------|---------|-----|
| Describing new feature | OFF | Need full context |
| GSD planning | OFF | Detailed research matters |
| Reviewing architecture | OFF | Nuance is important |
| OMO execution | ON | Save tokens on implementation |
| Running tests | ON | Output is compressed anyway |
| Debugging | ON | Debugger is concise by nature |
| Code review | OFF | Need full detail |
| Quick fixes | ON | Straightforward changes |

**Toggle commands:**
```
/caveman on            # Enable compressed mode
/caveman off           # Disable compressed mode
/caveman               # Toggle current state
```

---

## Graphify — When to Rebuild

### Rebuild After:
- Adding new modules (`src/new_module.py`)
- Major refactoring (renaming, moving files)
- Changing module dependencies
- Agents report unfamiliar code

### Don't Rebuild For:
- Small bug fixes
- Comment/docstring changes
- Test additions
- Config changes

### Commands:
```
graphify build         # Rebuild the AST index
graphify query graphify-out/graph.json <name>  # Query existing graph
```

**Pro tip:** Always query before rebuilding — the graph persists across sessions.

---

## RTK — Always On

### How It Works
RTK intercepts bash commands and compresses output before it reaches the LLM:

```
Without RTK:  git status → ~2000 tokens
With RTK:     git status → ~200 tokens (90% savings)
```

### Common Commands
```
rtk git status         # Compact status
rtk git diff           # Condensed diff
rtk ls src/            # Directory tree
rtk pytest tests/ -q   # Test results
rtk read file.py       # Smart file reading
rtk grep "pattern" .   # Grouped search
```

### Check Savings
```
rtk gain               # Summary stats
rtk gain --graph       # ASCII graph
rtk gain --history     # Command history
```

---

## Session Management

### End of Session
```
rtk gain               # Check token savings
rtk git status         # Ensure all changes committed
# Note current state for next session
```

### Resume Session
```
# Open OpenCode in Git Bash
cd /c/Users/esteb/Downloads/voice-to-text
opencode

# Select model based on phase (Codex for planning, DeepSeek for execution)
# Enable/disable OMO based on phase
cat .planning/STATE.md
/caveman off           # If planning
/caveman on            # If executing
```

---

## Common Pitfalls

### 1. Using GPT-5.5 for Everything
**Symptom:** Quota drains fast during planning
**Fix:** Use Codex for planning, cheap models (DeepSeek V4 Pro, GLM-5.1) for execution

### 2. OMO Enabled During Planning
**Symptom:** Agent confusion, wasted tokens
**Fix:** Disable OMO (`"plugin": []`) during planning phases

### 3. Running OMO Without a Plan
**Symptom:** Agents make wrong assumptions, produce incorrect code
**Fix:** Always run `/gsd-plan-phase` first

### 4. Forgetting Caveman Toggle
**Symptom:** Wasting tokens during execution
**Fix:** Toggle `/caveman on` before execution, `/caveman off` before review

### 5. Not Rebuilding Graphify
**Symptom:** Agents explore slowly, miss relationships
**Fix:** Rebuild after major changes

### 6. Skipping Verification
**Symptom:** Phase appears complete but goals not met
**Fix:** Always run `/gsd-eval-review` after execution

---

## Quick Command Reference

### Planning (OMO OFF, Codex, Tab: Plan)
```
/gsd-plan-phase <name>
/gsd-code-review
/gsd-eval-review
/gsd-new-milestone <name>
```

### Execution (OMO ON, DeepSeek, Tab: Sisyphus)
```
/gsd-execute <phase>
/caveman on
```

### Always Available
```
rtk git status
rtk pytest tests/ -q
rtk ls src/
graphify query graphify-out/graph.json <name>
rtk gain
```

### Session
```
/caveman on/off
cat .planning/STATE.md
cat .planning/ROADMAP.md
```

### Toggle OMO
```bash
# Enable
cp ~/.config/opencode/"opencode - copia.json" ~/.config/opencode/opencode.json

# Disable
# Edit opencode.json: "plugin": []
```
