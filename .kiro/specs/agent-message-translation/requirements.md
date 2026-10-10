<!--
DEMO SAMPLE — not a PR.
Method: Kiro Feature Specs (requirements.md EARS style)
Docs (prompts not public): https://kiro.dev/docs/specs/feature-specs/ (page updated Aug 4, 2026)
EARS: https://doi.org/10.1109/RE.2009.9 — https://alistairmavin.com/ears/
Repo: qinyu/codex-buddy@da47804f908313906d6a0a71f7665d9b7f9daa5b
Worktree: /workspace/codex-buddy-wt-kiro branch demo/spec-kiro-translation
Session: 04-kiro-session.md
NOTE: Kiro product prompts are closed-source; this sample mirrors documented requirements.md structure from public docs + public example layout in kirodotdev/Kiro issue-tracker specs.
-->

# Requirements Document

## Introduction

Optimize StickS3 (Codex Buddy) presentation of desktop agent lifecycle messages so Chinese text never appears on the English-only device display, message categories are visually distinct on a tiny screen, confirm/deny remains convenient, and categories use distinct tones.

## Glossary

- **StickS3_Device**: The M5Stack StickS3 running Codex Buddy firmware.
- **Agent_Message**: A user-visible notification derived from desktop agent hooks (completion, confirmation, error, etc.).
- **Display_English**: Text restricted to characters renderable by the device's English/ASCII font path.
- **Message_Category**: One of Complete, Confirm, Error (minimum set).

## Requirements

### Requirement 1: English-only device display

**User Story:** As a StickS3 user, I want agent messages on the device in English, so that I can read them without Chinese fonts.

#### Acceptance Criteria

1. WHEN an Agent_Message contains Chinese characters, THE System SHALL convert the display text to Display_English before it is shown on StickS3_Device.
2. WHEN translation or conversion fails, THE System SHALL show a short Display_English fallback and SHALL NOT render Chinese glyphs on StickS3_Device.
3. WHEN an Agent_Message is already Display_English, THE System SHALL display it without introducing Chinese characters.

### Requirement 2: Category visuals on tiny screen

**User Story:** As a StickS3 user, I want completions, confirmations, and errors to look different, so that I can classify them at a glance.

#### Acceptance Criteria

1. WHEN an Agent_Message is classified as Complete, THE StickS3_Device SHALL present a visual treatment distinct from Confirm and Error.
2. WHEN an Agent_Message is classified as Confirm, THE StickS3_Device SHALL present a visual treatment distinct from Complete and Error.
3. WHEN an Agent_Message is classified as Error, THE StickS3_Device SHALL present a visual treatment distinct from Complete and Confirm.
4. WHEN screen width is in the StickS3 tiny-display class, THE visual treatments SHALL remain distinguishable without requiring full sentence reading.

### Requirement 3: Confirm and deny convenience

**User Story:** As a StickS3 user, I want to accept or deny confirmation messages on the device, so that I can unblock the agent without using the desktop.

#### Acceptance Criteria

1. WHEN an Agent_Message requires a user decision, THE StickS3_Device SHALL offer Confirm and Deny actions operable with the device buttons.
2. WHEN the user selects Confirm, THE System SHALL record an accept decision for that message.
3. WHEN the user selects Deny, THE System SHALL record a deny/cancel decision for that message.
4. WHEN an Agent_Message does not require a decision, THE StickS3_Device SHALL NOT require the user to dismiss an approval gate to continue normal browsing.

### Requirement 4: Distinct tones per category

**User Story:** As a StickS3 user, I want different sounds for different message types, so that I can react without looking.

#### Acceptance Criteria

1. WHEN sound is enabled AND a Complete message arrives, THE StickS3_Device SHALL play the Complete tone pattern.
2. WHEN sound is enabled AND a Confirm message arrives, THE StickS3_Device SHALL play the Confirm tone pattern.
3. WHEN sound is enabled AND an Error message arrives, THE StickS3_Device SHALL play the Error tone pattern.
4. WHEN sound is disabled, THE StickS3_Device SHALL still apply category visuals without playing tones.
5. THE Complete, Confirm, and Error tone patterns SHALL be audibly distinguishable from each other.

### Requirement 5: Preserve off-device original text

**User Story:** As an agent operator, I want the original Chinese text kept off-device, so that I can verify translation quality.

#### Acceptance Criteria

1. WHEN Chinese text is converted for display, THE System SHALL retain the original text in an off-device log or record accessible on the desktop side.
