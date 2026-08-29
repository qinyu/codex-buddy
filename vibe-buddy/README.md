# Vibe Buddy (PC)

Mac/PC companion for StickS3: BLE usage bridge, Codex approval hooks, and Agent Hub.

## Install

```bash
cd vibe-buddy
uv tool install -e .
# optional ZH→EN fallbacks:
uv tool install -e ".[translate]"
```

Confirm the console script is on PATH (uv usually uses `~/.local/bin`):

```bash
which vibe-buddy
vibe-buddy --help
```

## Commands

```bash
vibe-buddy start          # ensure bridge supervisor is running
vibe-buddy stop
vibe-buddy status
vibe-buddy hook --event PermissionRequest   # Codex hook (stdin = JSON)
vibe-buddy post --client-kind cursor        # Agent Hub notify (stdin = JSON)
vibe-buddy bridge -- --help                 # foreground BLE bridge flags
```

State/config: `~/.codex/codex-usage-bridge/` (unchanged).

## Wire host hooks

After install, point Cursor / Pi / Hermes / Codex at the **installed** binary:

```bash
vibe-buddy setup-hooks
vibe-buddy setup-hooks --agent cursor
vibe-buddy setup-hooks --agent cursor,pi --agent hermes
vibe-buddy setup-hooks --agent all
```

`setup-hooks` writes absolute paths (`which vibe-buddy`), not repo-relative scripts.

## OpenCodex (quota meters)

No OpenCodex config changes are required for Agent Hub / hooks.

Vibe Buddy **pulls** provider quotas from a running OpenCodex admin API:

- URL default: `http://127.0.0.1:10100/api/provider-quotas`
- Token default: `~/.opencodex/admin-api-token`
- Bridge config: `"opencodex": true` in `~/.codex/codex-usage-bridge/config.json`

Keep OpenCodex running locally; optional overrides: `opencodex_url`, `opencodex_token_file`, `opencodex_ttl`.
