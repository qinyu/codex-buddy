<!--
DEMO SAMPLE — not a PR.
Method: GitHub Spec Kit (/speckit.specify)
Command/template: https://github.com/github/spec-kit/blob/62b6fcf49933525162981c5b1ddf075a2b781ded/templates/commands/specify.md
Spec template: https://github.com/github/spec-kit/blob/62b6fcf49933525162981c5b1ddf075a2b781ded/templates/spec-template.md
Repo: qinyu/codex-buddy@da47804f908313906d6a0a71f7665d9b7f9daa5b
Worktree: /workspace/codex-buddy-wt-spec-kit branch demo/spec-spec-kit-translation
Session: 03-spec-kit-session.md
-->

# Feature Specification: Agent message English display on StickS3

**Feature Branch**: `demo/spec-spec-kit-translation`

**Created**: 2026-10-10

**Status**: Draft

**Input**: User description: "电脑上的 AI Agent 工作结束后会发消息给客户端；目前翻译功能很弱，之前用的是离线翻译，后续要优化。设备屏仅英文、中文须先转英文；类别要在小屏可辨；确认/拒绝要方便；不同类型不同提示音。"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Readable English completion on stick (Priority: P1)

A user whose agent finishes with a Chinese summary sees an English summary on StickS3 and never sees Chinese glyphs.

**Why this priority**: Without readable text the device fails its core companion job.

**Independent Test**: Feed a Chinese completion payload through the notify→bridge path; assert device-bound fields are English-only and visible on stick UI.

**Acceptance Scenarios**:

1. **Given** an agent-finished message containing Chinese, **When** it is delivered to StickS3, **Then** the on-device text is English (or an English fallback) with no Chinese characters.
2. **Given** an already-English completion message, **When** it is delivered, **Then** meaning is preserved without unnecessary rewriting that changes intent.

---

### User Story 2 - Confirm vs complete at a glance (Priority: P1)

A user can tell a confirmation request from a normal completion using icon/layout on the tiny screen and can accept or deny with device buttons.

**Why this priority**: Missed approvals block agents; false urgency wastes attention.

**Independent Test**: Deliver one `complete` and one `confirm` message back-to-back; observer distinguishes them without reading full text; confirm accepts/denies via A/B.

**Acceptance Scenarios**:

1. **Given** a confirmation-needed message, **When** it appears on StickS3, **Then** visual presentation differs from normal completion and offers accept and deny actions.
2. **Given** a normal completion, **When** it appears, **Then** the user is not trapped in an approval screen.

---

### User Story 3 - Error looks and sounds different (Priority: P2)

Failures use a distinct visual category and a distinct tone from completions and confirms.

**Why this priority**: Errors need interruptibility without being confused with success chirps.

**Independent Test**: Blind listen + glance test across complete/confirm/error with sound enabled.

**Acceptance Scenarios**:

1. **Given** sound enabled, **When** complete, confirm, and error messages arrive, **Then** each category plays a different tone pattern.
2. **Given** sound disabled, **When** those messages arrive, **Then** category visuals still differ.

---

### Edge Cases

- What happens when translation fails? System MUST show a short English fallback and MUST NOT display Chinese.
- How does system handle mixed Chinese+English input? Non-English segments MUST be converted or replaced so the displayed string is English-safe.
- What if the English result exceeds the small display budget? System MUST truncate safely while keeping category cue intact.
- What if offline/engine unavailable? Same as translation failure: English fallback, never Chinese on device.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST convert any Chinese (or other non-renderable script) in agent-to-device messages into English before StickS3 display.
- **FR-002**: System MUST ensure StickS3 displayed strings for these messages are English/ASCII-safe for the device font.
- **FR-003**: System MUST classify user-visible device messages into at least three categories: normal completion, confirmation-needed, and error/failure.
- **FR-004**: System MUST present each category with a visually distinct icon and/or layout suitable for a ~135px-class screen.
- **FR-005**: Users MUST be able to confirm or deny confirmation-needed messages on-device with convenient button actions.
- **FR-006**: System MUST play distinct alert/tone patterns per category when sound is enabled.
- **FR-007**: System MUST NOT use on-device CJK fonts as the primary way to show Chinese agent text.
- **FR-008**: System MUST keep original non-English text available off-device (e.g. desktop log) when translation or fallback occurs.

### Key Entities

- **DeviceMessage**: category, english_text, optional original_text_ref, requires_decision flag
- **Category**: complete | confirm | error
- **TonePattern**: per-category audible pattern identity (not a specific frequency table in this spec)

## Success Criteria *(mandatory)*

- **SC-001**: In a sample of Chinese agent-finished messages, 100% of StickS3 on-screen strings contain no Chinese characters.
- **SC-002**: Untrained observers distinguish complete vs confirm vs error with ≥90% accuracy from visuals alone on the stick.
- **SC-003**: Confirmation decisions can be completed on-device without using the desktop UI.
- **SC-004**: With sound on, listeners identify category from tone alone with ≥80% accuracy in a three-way forced choice.
- **SC-005**: Users report the stick remains usable in quiet mode via visuals alone.

## Assumptions

- StickS3 firmware continues to use English-oriented bitmap/ASCII fonts (as in current UI strings).
- Desktop bridge remains the insertion point for outbound device packets.
- Prior "offline translation" is absent from tree `da47804` and must be reintroduced or replaced as a capability, not assumed present.

## Codebase anchors (informational; not implementation)

- Notify: [https://github.com/qinyu/codex-buddy/blob/da47804f908313906d6a0a71f7665d9b7f9daa5b/tools/agent_hub_notify.py](https://github.com/qinyu/codex-buddy/blob/da47804f908313906d6a0a71f7665d9b7f9daa5b/tools/agent_hub_notify.py)
- Display fields: [https://github.com/qinyu/codex-buddy/blob/da47804f908313906d6a0a71f7665d9b7f9daa5b/src/data.h#L37-L44](https://github.com/qinyu/codex-buddy/blob/da47804f908313906d6a0a71f7665d9b7f9daa5b/src/data.h#L37-L44)
- Approval UX: [https://github.com/qinyu/codex-buddy/blob/da47804f908313906d6a0a71f7665d9b7f9daa5b/src/main.cpp#L914-L956](https://github.com/qinyu/codex-buddy/blob/da47804f908313906d6a0a71f7665d9b7f9daa5b/src/main.cpp#L914-L956)
