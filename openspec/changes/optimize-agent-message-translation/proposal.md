# Change: Optimize agent message translation/display on StickS3

## Why

Chinese agent-finished messages hit an English-only StickS3 display; prior offline translation is missing from the tree; categories, confirm UX, and tones need hardening.

## What Changes

- ADDED capability `agent-message-display`: EN-before-display, categories, confirm/deny, tones, off-device original retention.

## Capabilities

- `agent-message-display` (new)

## Impact

- Desktop notify/bridge outbound packets and StickS3 presentation of `msg`/prompt/category cues.
