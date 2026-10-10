<!--
DEMO SAMPLE — not a PR.
Method: OpenSpec delta spec (spec-driven schema)
Template: https://github.com/Fission-AI/OpenSpec/blob/9111a7654d7800391459431fff4eaf66e33a3d2e/schemas/spec-driven/templates/spec.md
Instructions: https://github.com/Fission-AI/OpenSpec/blob/9111a7654d7800391459431fff4eaf66e33a3d2e/schemas/spec-driven/schema.yaml
Repo: qinyu/codex-buddy@da47804f908313906d6a0a71f7665d9b7f9daa5b
Worktree: /workspace/codex-buddy-wt-openspec branch demo/spec-openspec-translation
Session: 07-openspec-session.md
-->

# Spec Delta

## Purpose

Make StickS3 agent lifecycle messages readable and classifiable: English-only display after ZH→EN conversion, distinct category visuals and tones, and convenient on-device confirm/deny — without relying on CJK fonts on the device.

## ADDED Requirements

### Requirement: English-only device-bound text

The system SHALL ensure every user-visible string written for StickS3 display is English (device-font-safe) when the source agent message contains Chinese or other non-renderable script. The system SHALL convert such source text to English before display. On conversion failure the system SHALL show a short English fallback and MUST NOT display Chinese characters on StickS3.

#### Scenario: Chinese completion becomes English on device
- **WHEN** an agent-finished message containing Chinese is delivered to StickS3
- **THEN** the on-device text SHALL be English or an English fallback and SHALL contain no Chinese characters

#### Scenario: Translation failure stays English-safe
- **WHEN** conversion cannot produce a translation
- **THEN** the system SHALL display a short English fallback and MUST NOT render Chinese on StickS3

### Requirement: Category visual distinction

The system SHALL classify user-visible StickS3 messages into at least Complete, Confirm, and Error categories. The system SHALL present each category with a visually distinct icon and/or layout suitable for a tiny screen.

#### Scenario: Glanceable categories
- **WHEN** Complete, Confirm, and Error messages are shown on StickS3
- **THEN** each category SHALL be visually distinguishable without requiring full sentence reading

### Requirement: On-device confirm and deny

When a message requires a user decision, the system SHALL provide convenient Confirm and Deny actions on StickS3. Messages that do not require a decision MUST NOT trap the user in an approval gate.

#### Scenario: Confirm accept
- **WHEN** a Confirm-category message is shown and the user selects accept
- **THEN** the system SHALL record an accept decision for that message

#### Scenario: Confirm deny
- **WHEN** a Confirm-category message is shown and the user selects deny
- **THEN** the system SHALL record a deny/cancel decision for that message

#### Scenario: Non-confirm does not block
- **WHEN** a Complete or Error message that does not require a decision is shown
- **THEN** the system MUST NOT require an approval dismiss to continue normal device browsing

### Requirement: Distinct tones per category

When device sound is enabled, the system SHALL play mutually distinguishable alert/tone patterns for Complete, Confirm, and Error. When sound is disabled, category visuals SHALL still apply.

#### Scenario: Audible distinction
- **WHEN** sound is enabled and Complete, Confirm, and Error messages arrive
- **THEN** each category SHALL use a different tone pattern

#### Scenario: Silent mode
- **WHEN** sound is disabled and categorized messages arrive
- **THEN** the system SHALL omit tones while still showing category visuals

### Requirement: Off-device original retention

When Chinese (or other non-English) source text is converted for device display, the system SHALL retain the original text in an off-device desktop-accessible record.

#### Scenario: Original retained
- **WHEN** a Chinese source message is converted for StickS3
- **THEN** the original text SHALL remain available off-device for operator review
