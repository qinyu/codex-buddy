<!--
DEMO SAMPLE — not a PR.
Method: BMAD bmad-spec
Template: https://github.com/bmad-code-org/BMAD-METHOD/blob/bda3c5929f672019b90f39a3ea27259d35d00974/skills/bmad-spec/assets/spec-template.md
Skill: https://github.com/bmad-code-org/BMAD-METHOD/blob/bda3c5929f672019b90f39a3ea27259d35d00974/skills/bmad-spec/SKILL.md
Repo: qinyu/codex-buddy@da47804f908313906d6a0a71f7665d9b7f9daa5b
Worktree: /workspace/codex-buddy-wt-bmad branch demo/spec-bmad-translation
Session: 06-bmad-session.md
-->

---
id: SPEC-agent-message-translation
companions: []
sources:
  - https://github.com/qinyu/codex-buddy/tree/da47804f908313906d6a0a71f7665d9b7f9daa5b
  - ../codex-buddy-translation-demo-brief.md
  - user-steering: EN-only display; ZH→EN; category visuals; confirm UX; distinct tones
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Agent message English display on StickS3

## Why

**Pain to solve:** Desktop agents push finished/confirm/error text to StickS3, but Chinese (and mixed) copy hits an English-only tiny display. Prior offline translation is absent from the current tree, so the companion becomes unreadable and categories blur. Operators need glanceable category cues, convenient on-device confirm/deny, and distinct tones so the stick works at arm's length.

## Capabilities

- **CAP-1**
  - **intent:** User receives agent-to-device messages as English text on StickS3 even when the agent emitted Chinese.
  - **success:** For Chinese inputs in a fixed test corpus, on-device strings contain zero Chinese characters; meaning-preserving English or documented English fallback appears instead.

- **CAP-2**
  - **intent:** User can distinguish normal completion, confirmation-needed, and error messages by visual presentation on the tiny screen.
  - **success:** Blind glance test yields correct category identification without reading full sentences.

- **CAP-3**
  - **intent:** User can accept or deny confirmation-needed messages on the device with simple button actions.
  - **success:** Accept and deny each complete a decision round-trip without using the desktop UI; non-confirm messages do not force an approval gate.

- **CAP-4**
  - **intent:** User hears different alert patterns for completion, confirmation, and error when sound is enabled.
  - **success:** Forced-choice listen test separates the three patterns; silent mode still shows category visuals.

- **CAP-5**
  - **intent:** Operator can still inspect original non-English text off-device after conversion.
  - **success:** Desktop-side record retains original text whenever conversion or fallback ran.

## Constraints

- StickS3 display path remains English/ASCII-font oriented; adding CJK fonts is not an acceptable primary solution.
- Display payloads must respect existing small field budgets conceptually (short summaries).
- Sound patterns apply only when device sound setting is enabled.
- Load-bearing claim preserved: no offline translation module exists at commit `da47804` in qinyu/codex-buddy — capability must be (re)introduced on the desktop path.

## Non-goals

- Choosing a single mandatory cloud translation vendor.
- Redesigning pet GIF asset production pipelines.
- Changing BLE pairing/encryption mechanics.
- Opening GitHub PRs as part of this demo documentation effort.

## Success signal

A Chinese agent-finished message becomes readable English on StickS3 with the correct category chrome and tone, while confirmations stay one-handed on-device — demonstrated end-to-end on real hardware or a faithful display/tone harness.

## Assumptions

- Assumed desktop bridge/notify remains the choke point for outbound device JSON (matches current architecture).
- Assumed minimum category set {complete, confirm, error} satisfies Yu's "varied content forms" for this slice.

## Open Questions

- Should "warning" be a fourth category now, or folded into error for v1? (Default assumed: fold into error unless product expands.)
