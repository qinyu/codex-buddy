<!--
DEMO SAMPLE — not a PR.
Method: Superpowers (obra/superpowers) brainstorming → written design spec
Skill/template: https://github.com/obra/superpowers/blob/8ca22dba9a94f28898bbce59f2537ff4d87c747d/skills/brainstorming/SKILL.md
Repo explored: qinyu/codex-buddy@da47804f908313906d6a0a71f7665d9b7f9daa5b
Worktree: /workspace/codex-buddy-wt-superpowers branch demo/spec-superpowers-translation
Session: 01-superpowers-session.md
-->

# Agent-finished message English display & category cues — design

- **Date:** 2026-10-10
- **Status:** draft for demo review (Yu constraints incorporated; awaiting formal written-spec approval before writing-plans)
- **Case repo:** [qinyu/codex-buddy@da47804](https://github.com/qinyu/codex-buddy/tree/da47804f908313906d6a0a71f7665d9b7f9daa5b)

## Motivation

Desktop AI agents already push lifecycle events to StickS3 via the Agent Hub BLE bridge. Users often receive Chinese (or mixed) completion / confirmation / error text. The StickS3 firmware renders English/ASCII UI only; Chinese glyphs are not available. Offline translation used previously is **not present** in the current tree at `da47804` — this design treats reliable EN-before-display, category visuals, confirm UX, and distinct tones as the product outcomes to restore and harden.

## Context (explored)

- Notify path: hooks → `tools/agent_hub_notify.py` → `agent-hub.sock` → `tools/codex_usage_ble_bridge.py` → NUS → `src/data.h` / `src/main.cpp`.
- Display budgets: `msg[24]`, transcript `lines[8][92]`, approval `promptTool[20]` / `promptHint[44]` ([data.h](https://github.com/qinyu/codex-buddy/blob/da47804f908313906d6a0a71f7665d9b7f9daa5b/src/data.h#L37-L44)).
- Existing confirm: A accept / B cancel on approval screen ([main.cpp](https://github.com/qinyu/codex-buddy/blob/da47804f908313906d6a0a71f7665d9b7f9daa5b/src/main.cpp#L914-L956)); arrival chirp `beep(1200,80)` ([L1773](https://github.com/qinyu/codex-buddy/blob/da47804f908313906d6a0a71f7665d9b7f9daa5b/src/main.cpp#L1773)).
- Category today ≈ pet states from attention/dizzy event sets, not free-text category chrome.

## Design

### 1. English-only display contract (non-negotiable)

Every string destined for StickS3 fields (`msg`, `entries`/`lines`, `prompt.tool`, `prompt.hint`) MUST be English (ASCII-safe for the default font). If the agent or hook payload contains Chinese (or other non-renderable scripts), a **desktop-side** normalization step MUST produce an English string **before** BLE write. Failure to translate MUST NOT paint Chinese; instead show a short English fallback such as `ZH msg (see desktop)` plus preserve original off-device.

### 2. Message categories with tiny-screen visuals

Classify outbound user-visible messages into at least:

| Category | Meaning | Visual cue (WHAT) |
| --- | --- | --- |
| `complete` | Normal agent-finished / success summary | Distinct success icon or pet/chrome state already associated with completion |
| `confirm` | Needs user approve/deny | Approval-style chrome (existing approve? banner pattern) |
| `error` | Failure / fatal / rate-limit class | Distinct error icon or dizzy/error chrome |

Categories MUST remain recognizable at ~135px width without reading every character.

### 3. Confirm / deny interaction

`confirm` category messages MUST expose accept and cancel (or equivalent) on-device with the same A/B convenience as today's permission prompts. Time-to-decide feedback (e.g. waiting seconds turning hot) remains desirable. Non-confirm categories MUST NOT trap the user in an approval screen.

### 4. Distinct tones

When device sound is enabled, `complete`, `confirm`, and `error` MUST play different beep patterns (frequency and/or length and/or count). Silent mode still shows visuals.

### 5. Where logic lives (architectural shape, still WHAT/WHY)

Prefer keeping language detection + ZH→EN + category tagging on the **desktop bridge / notify path**, because the device lacks CJK fonts and has tiny buffers. The firmware consumes already-English text plus a category signal (explicit field or mapped state) and renders icon + tone.

### 6. Out of scope for this design

- Shipping a CJK font pack on StickS3 as the primary fix.
- Rewriting the pet GIF pipeline.
- Choosing a specific cloud MT vendor as the only allowed engine (engine is a later plan decision; outcome is correct English on screen).

## Success criteria

1. A Chinese agent-finished payload never appears as Chinese glyphs on StickS3; English (or ASCII fallback) does.
2. A user can tell complete vs confirm vs error within one glance on the stick.
3. Confirm messages are decidable with A/B without opening the desktop.
4. With sound on, the three categories sound different in a blind listen test.

## Self-review (Superpowers checklist)

1. Placeholder scan: none left (offline engine absence noted as fact, not TBD).
2. Consistency: EN contract + category + UX + tone align; fallback is English-only.
3. Scope: single subsystem (message presentation path), one plan-sized.
4. Ambiguity: "English" = display language for device fields; original may remain on desktop logs.
