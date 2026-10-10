<!--
DEMO SAMPLE — not a PR.
Method: Tessl spec-driven-development tile (spec-writer)
Format: https://github.com/tesslio/spec-driven-development-tile/blob/b8fdff700a5df98386d82d29f1ef3dc783092daf/docs/spec-format.md
Skill: https://github.com/tesslio/spec-driven-development-tile/blob/b8fdff700a5df98386d82d29f1ef3dc783092daf/skills/spec-writer/SKILL.md
Validate: scripts/validate-specs.sh @ b8fdff70
Repo: qinyu/codex-buddy@da47804f908313906d6a0a71f7665d9b7f9daa5b
Worktree: /workspace/codex-buddy-wt-tessl branch demo/spec-tessl-translation
Session: 05-tessl-session.md
-->

---
name: AgentMessageDisplay
description: English-only StickS3 presentation of agent lifecycle messages with category visuals, confirm UX, and distinct tones
targets:
  - ../tools/codex_usage_ble_bridge.py
  - ../tools/agent_hub_notify.py
  - ../src/data.h
  - ../src/main.cpp
---

# AgentMessageDisplay

Desktop-side normalization produces English device payloads; firmware renders category visuals and tones. StickS3 MUST never display Chinese glyphs.

```python
from enum import Enum
from typing import Optional, Protocol

class MessageCategory(str, Enum):
    COMPLETE = "complete"
    CONFIRM = "confirm"
    ERROR = "error"

class DeviceMessage(Protocol):
    category: MessageCategory
    english_text: str
    requires_decision: bool
    original_text: Optional[str]

def normalize_for_device(raw_text: str, hint_category: Optional[str] = None) -> DeviceMessage:
    """Detect non-English/CJK, produce Display_English + category. Never return CJK in english_text."""
    ...

def render_tone(category: MessageCategory, sound_enabled: bool) -> None:
    """Play category-distinct pattern when sound_enabled; no-op otherwise."""
    ...
```

`[@test] ../tests/agent_message_display/test_normalize_for_device.py`

## English-only display

- `normalize_for_device` MUST set `english_text` with no Chinese characters even when `raw_text` is Chinese.
  `[@test] ../tests/agent_message_display/test_zh_to_en.py`
- On translation failure, `english_text` MUST be a short English fallback and MUST NOT contain CJK.
  `[@test] ../tests/agent_message_display/test_fallback_no_cjk.py`
- Firmware display paths consuming `msg` / prompt fields MUST receive only `english_text` (or equivalent English fields).

## Categories and visuals

- Every user-visible device message MUST carry `MessageCategory` in {complete, confirm, error}.
- StickS3 MUST show a visually distinct treatment per category on the tiny screen (icon and/or layout).
  `[@test] ../tests/agent_message_display/test_category_visual_contract.py`

## Confirm / deny

- When `requires_decision` is true, device MUST expose accept and deny actions (A/B-equivalent).
  `[@test] ../tests/agent_message_display/test_confirm_deny.py`
- When `requires_decision` is false, device MUST NOT block in an approval gate.

## Tones

- With sound enabled, complete / confirm / error MUST use mutually distinguishable beep patterns.
  `[@test] ../tests/agent_message_display/test_tone_patterns.py`
- With sound disabled, visuals still apply; tones do not play.

## Non-goals

- Shipping CJK fonts on StickS3 as the primary fix.
- Selecting a specific MT vendor API in this tile (signature above is the seam; engine is swappable).
