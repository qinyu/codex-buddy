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

With **no** `--agent`, vibe-buddy scans this machine for known tools and only
configures the ones it finds:

```bash
vibe-buddy setup-hooks                 # auto-detect + configure
vibe-buddy setup-hooks --scan          # JSON inventory only
vibe-buddy setup-hooks --dry-run       # show plan, write nothing
vibe-buddy setup-hooks --agent cursor
vibe-buddy setup-hooks --agent all
```

Catalog (detection cues): Cursor, Codex, Claude Code, Pi, Hermes, DSH
(process presence), OpenCodex (quota service), Aider / Kimi / Zed (detect-only notes).

`setup-hooks` writes absolute paths from `which vibe-buddy`, not repo scripts.

## Login autostart (macOS)

```bash
vibe-buddy setup-autostart           # LaunchAgent: start bridge at login
vibe-buddy setup-autostart --status
vibe-buddy setup-autostart --uninstall
```

Installs `~/Library/LaunchAgents/com.vibe-buddy.bridge.plist` with `RunAtLoad`
and `KeepAlive` so the supervisor comes back if it exits.

## OpenCodex (quota meters)

No OpenCodex config changes are required for Agent Hub / hooks.

Vibe Buddy **pulls** provider quotas from a running OpenCodex admin API:

- URL default: `http://127.0.0.1:10100/api/provider-quotas`
- Token default: `~/.opencodex/admin-api-token`
- Bridge config: `"opencodex": true` in `~/.codex/codex-usage-bridge/config.json`

Keep OpenCodex running locally; optional overrides: `opencodex_url`, `opencodex_token_file`, `opencodex_ttl`.

The bridge polls quotas on the PC on its normal interval (and reuses them for
`opencodex_ttl` seconds). Stick provider/agent page turns only flip the cached
index and push over BLE — they do not re-hit OpenCodex on every press.
