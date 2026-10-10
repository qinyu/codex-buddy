<!--
DEMO SAMPLE — not a PR. Spec would publish to issue tracker with ready-for-agent; here filed locally only.
Method: Matt Pocock to-spec
Skill/template: https://github.com/mattpocock/skills/blob/f3fc5632f401156837ee3872f14fe33ccf1024ea/skills/engineering/to-spec/SKILL.md
Repo: qinyu/codex-buddy@da47804f908313906d6a0a71f7665d9b7f9daa5b
Worktree: /workspace/codex-buddy-wt-matt-to-spec branch demo/spec-matt-to-spec-translation
Session: 02-matt-to-spec-session.md
-->

## Problem Statement

When a desktop AI agent finishes (or needs confirmation / fails), StickS3 shows a short message. Those messages are often Chinese or mixed, but the device can only render English/ASCII. Prior offline translation is gone from the tree, so users see unreadable or truncated junk. Categories (done vs need-you vs error) also blur together on a tiny screen, and tones barely differ, so the stick is hard to use at a glance.

## Solution

Normalize every device-bound string to English before it is written over BLE; tag each user-visible message with a category that drives distinct tiny-screen visuals and distinct beep patterns; keep confirm/deny as a one-handed A/B flow for messages that need a decision.

## User Stories

1. As a StickS3 user, I want agent-finished summaries in English on the stick, so that I can read them without CJK fonts.
2. As a StickS3 user, I want Chinese agent text automatically converted to English before display, so that the screen never shows mojibake or blank boxes.
3. As a StickS3 user, I want a clear success presentation when work completes normally, so that I know I can ignore the stick.
4. As a StickS3 user, I want confirmation requests to look different from completions, so that I do not miss approvals.
5. As a StickS3 user, I want error/failure messages to look different from completions, so that I escalate quickly.
6. As a StickS3 user, I want to accept or deny confirmation requests with the front and side buttons, so that I do not need to grab the laptop.
7. As a StickS3 user, I want different beep patterns for complete / confirm / error when sound is on, so that I can classify events without looking.
8. As a StickS3 user, I want sound-off mode to still show category visuals, so that quiet offices remain usable.
9. As a desktop agent operator, I want translation failure to fall back to a short English placeholder, so that the stick never paints Chinese.
10. As a desktop agent operator, I want original Chinese retained in desktop logs, so that I can audit meaning later.
11. As a multi-agent user, I want category cues to work for Codex, Cursor, Pi, Hermes, etc., so that any hub client behaves consistently.
12. As a user with long summaries, I want English text truncated safely to the stick's field budgets, so that layout does not break.
13. As a user, I want non-confirm messages not to trap me on an approval screen, so that browsing usage stays fluid.
14. As a user, I want waiting time on confirm prompts still emphasized, so that stale approvals are obvious.
15. As a maintainer, I want the English-display contract documented as a product rule, so that future hooks do not bypass it.

## Implementation Decisions

- Keep language detection, ZH→EN, and category tagging on the desktop Agent Hub / BLE bridge path (device remains a dumb English renderer).
- Introduce an explicit category signal accompanying display strings (or a strict mapping onto existing attention/complete/dizzy semantics) consumed by firmware for icon and tone.
- Preserve existing A/B permission UX as the confirm seam; extend the same interaction model to confirm-class agent messages.
- Field budgets stay as today's display limits; English strings must fit or truncate with ellipsis behavior already used for short_text.
- Do not add CJK fonts on-device as the solution.
- Translation engine choice is deferred to planning; the decision locked here is "English on device before BLE write."

## Testing Decisions

- Good tests observe external behavior only: bytes/strings written toward the device and on-device presentation outcomes — not private helper names.
- Primary seam (confirmed with user): the bridge/notify boundary that emits the JSON packet for StickS3 (`msg` / prompt / entries / category).
- Cases: Chinese input → English output fields; already-English passthrough; translation failure → English fallback never containing CJK; category complete/confirm/error → distinct visual + tone contracts; confirm accept/deny round-trip.
- Prior art: existing approval packet shaping and `short_text` truncation behavior in the bridge.

## Out of Scope

- Implementing or vendoring a specific MT library in this spec.
- Redesigning pet GIF asset production.
- Changing BLE UUIDs or encryption pairing flow.
- Pushing branches or opening PRs as part of the demo.

## Further Notes

Repo gap: no `translate` / `i18n` module at `da47804`. Upstream clone URL in README points at openelab-commits/codex-buddy; this demo specs against qinyu/codex-buddy.
