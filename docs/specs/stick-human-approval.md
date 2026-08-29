# Spec: Stick human-approval UX + PC-side ZH→EN

GitHub tracking: https://github.com/qinyu/codex-buddy/issues/11

Improve Stick **human approval** (permission prompt) presentation and make Chinese prompt text readable by translating on the **PC bridge** before BLE. Firmware shows ASCII-only fonts today; Chinese glyphs appear blank.

Out of scope for this ticket: multi-agent approval routing for Cursor/Pi/Hermes (follow-up).

## Goals

1. Approval panel is hard to miss and matches physical buttons.
2. Chinese (and other non-ASCII) summaries are shown as concise English on Stick.
3. Text fits the tiny screen without fighting A/B semantics.

## Non-goals

- Shipping a CJK font on Stick firmware (Flash / layout cost).
- Using cloud LLM / Codex tokens for translation.
- Using Ollama for the approval hot path (too slow).
- Manual page-turn with B during approval (B = cancel).

---

## Current behavior (baseline)

```text
Codex PermissionRequest
  → hook_entry.py → approval.sock
  → CodexApprovalProxy
  → BLE {"prompt":{"id","tool","hint"},"msg":...}
  → Stick drawApproval()
  → A accept / B cancel → {"cmd":"permission",...}
```

- `promptTool` ≈ 19 chars, `promptHint` ≈ 43 **bytes** device-side.
- Approval strip historically ~78px; easy to miss vs full usage block.
- Default M5GFX font has no CJK → Chinese renders as blank.
- Landscape usage skips approval overlay unless `inPrompt` forces portrait (already `!inPrompt` in landscape candidate).

---

## Spec A — Firmware approval UI

### A1. Panel geometry

- Approval panel **covers the entire usage/provider band**: from `USAGE_PET_BOTTOM` to `H` (same vertical span as provider header + meters).
- Keep two-pane layout: pet/chrome above; approval below.
- Draw a separator line at the top of the approval band.

### A2. Content layout (portrait)

Within the approval band, top → bottom:

1. Status line: `approve? Ns` (red/hot after ≥10s), unchanged meaning.
2. Tool title: `promptTool` (size 2 if ≤10 ASCII chars, else size 1).
3. Hint: wrap at ~21 columns; allow **up to 3 lines** given taller panel.
4. Footer actions (see A3).

### A3. Button affordances

Replace `A: accept` / `B: cancel` text with spatial arrows matching hardware:

| Action | Physical control | On-screen affordance |
|--------|------------------|----------------------|
| Accept | BtnA (below screen) | label `accept` + **down** triangle (↓) |
| Cancel | BtnB (right edge) | label `cancel` + **right** triangle (→) |

Reuse the same triangle idiom as `drawMenuHints` (pixel triangles, not Unicode arrows if font lacks them).

While `responseSent`, show `sent...` instead of affordances.

### A4. Interaction (unchanged semantics)

- Short A → `decision: accept`
- Short B → `decision: cancel`
- Timeout / offline → hook returns empty → Codex local UI (existing ~45–90s path)
- On prompt arrival: wake, beep, `displayMode = DISP_NORMAL`, close menus; landscape candidate already excludes `inPrompt`

### A5. Landscape

- While a prompt is active, stay on portrait approval path (already implied by `!inPrompt` for `usageLandscapeCandidate`).
- Do **not** require a separate landscape approval layout in v1.

---

## Spec B — PC-side text localization (bridge)

### B1. When to transform

Apply to strings that become Stick `prompt.tool` / `prompt.hint` (and optional `msg`) **after** `_prompt_text()` extraction, **before** `short_text` / BLE write.

Trigger: hint (or tool) contains any non-ASCII code point (typical Chinese).

### B2. Pipeline (ordered)

1. **ASCII passthrough** — if string is ASCII-only (commands, paths, `git …`), do **not** call any translator; only fit-to-screen (Spec C).
2. **MyMemory** (primary) — free HTTP API; short timeout (e.g. 400–800ms). Optional `de=<email>` config later for 50k chars/day; anonymous 5k chars/day is enough for personal approval volume.
3. **Argos Translate zh→en** (fallback) — local package (`argostranslate` + `translate-zh_en`); use on MyMemory timeout/error/empty.
4. **Last resort** — spaced phrase-dict / `pypinyin` / fixed placeholder `Chinese text (see PC)`.

Never call cloud LLMs or Ollama on this path.

### B3. Caching

- Process-local cache: source string → English result (MyMemory or Argos).
- Avoid repeat network calls for identical hints in one bridge session.

### B4. Dependencies / config

- Document optional deps: `deep-translator` (or direct MyMemory HTTP), `argostranslate` + installed `zh→en` model.
- Config knobs under `~/.codex/codex-usage-bridge/config.json`, e.g.:
  - `prompt_translate`: `auto` | `off`
  - `prompt_translate_timeout_ms`
  - `mymemory_email` (optional)
- Fail open: translation errors must not block showing an approval (fallback string OK).

### B5. Quotas (MyMemory)

- Anonymous ~**5 000 chars/day**; with email ~**50 000**.
- Stick approvals are short (~20–40 chars) and infrequent → personal use is fine.
- On quota failure → Argos/placeholder.

---

## Spec C — Fit text to Stick (truncate / scroll)

Screen budget after A1: roughly **2–3 hint lines × ~21 columns** ≈ **42–63 characters** of English.

### C1. Truncation (required)

After translation (or passthrough):

- Truncate by **Unicode characters** (not bytes).
- Prefer keeping the **start** of the sentence; append `...` when clipped.
- Sync device buffers: either widen `promptHint` enough for 3×21 ASCII, or keep bridge output ≤ device capacity **in characters** after UTF-8 encoding fits `strncpy` limits. Prefer bridge emits final display string that fits `promptHint` safely.

### C2. Auto-scroll (optional v1 stretch)

If translated text still exceeds 3 lines of meaning we care about:

- Firmware may auto-scroll hint lines every ~1.5–2s while prompt is active.
- **Do not** bind scroll to B (cancel).

### C3. Manual paging

**Out of scope for v1** (conflicts with cancel).

---

## Spec D — Dual copies / packaging

- Keep `plugins/codex-usage-stick/scripts/codex_usage_ble_bridge.py` and `tools/codex_usage_ble_bridge.py` in sync (or document single source of truth).
- Same for any new helper module (e.g. `prompt_localize.py`).

---

## Acceptance criteria

- [x] Approval panel covers full provider/usage band; pet/chrome remain above.
- [x] Footer shows ↓ accept / → cancel (not `A:` / `B:` labels).
- [x] Simulated Chinese hint arrives on Stick as readable **English** (MyMemory or Argos), not blank glyphs.
- [x] Pure ASCII hints (e.g. `ls -la /tmp`, `git push …`) are unchanged by translators.
- [x] Overlong English is character-truncated with `...` and does not corrupt UTF-8 mid-codepoint.
- [x] MyMemory failure still shows an approval (Argos or placeholder); bridge does not hang.
- [x] A/B still accept/cancel; timeout still falls back to Codex UI.
- [ ] Firmware flashed and bridge restarted for a manual check on hardware.

## Test plan

1. Portrait LIVE usage → inject safe Chinese permission via `approval.sock` → panel covers meters; English hint visible; ↓/→ footer.
2. Inject ASCII `Bash` + `ls -la /tmp` → no bogus translation (Argos must not rewrite English).
3. Disconnect MyMemory (firewall / bad URL) → still get Argos or placeholder; approval usable.
4. Very long Chinese → truncated English with `...`; optional scroll if implemented.
5. During prompt, tilt to landscape → remains usable portrait approval (no stuck landscape without panel).

## Implementation notes

- Partial firmware work for taller panel + arrow footer may already exist uncommitted/unflashed on the working tree — verify before redoing.
- Argos model path on Mac: `~/.local/share/argos-translate` (~80MB); cold start can be seconds, warm ~30–100ms.
- MyMemory is outbound HTTP; keep timeout tight.

## Follow-ups (not this ticket)

- Multi-agent approval ingress (Cursor/Pi/Hermes → same `approval.sock` / queue).
- Stick CJK fonts if product later requires native Chinese glyphs.
