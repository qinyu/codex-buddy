#!/usr/bin/env bash
# Reinstall Pi / Hermes extensions as vibe_buddy_hub (replaces legacy codex_buddy_hub).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CLI="${ROOT}/.venv/bin/vibe-buddy"
if [[ ! -x "$CLI" ]]; then
  CLI="$(command -v vibe-buddy)"
fi
"$CLI" setup-hooks --agent pi --agent hermes

CFG="${HOME}/.hermes/config.yaml"
if [[ -f "$CFG" ]] && ! grep -q 'vibe_buddy_hub' "$CFG"; then
  echo ">>> Add under plugins.enabled in ${CFG}:"
  echo "    - vibe_buddy_hub"
fi

echo ">>> Done. Restart Pi / Hermes so they load vibe_buddy_hub."
