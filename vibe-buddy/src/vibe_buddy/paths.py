"""Shared paths and defaults for Vibe Buddy PC state."""

from __future__ import annotations

from pathlib import Path
from typing import Any

STATE_DIR = Path.home() / ".codex" / "codex-usage-bridge"
CONFIG_PATH = STATE_DIR / "config.json"
PID_PATH = STATE_DIR / "bridge.pid"
LOG_PATH = STATE_DIR / "bridge.log"
HOOK_LOG_PATH = STATE_DIR / "hook.log"
APPROVAL_SOCK_PATH = STATE_DIR / "approval.sock"
AGENT_HUB_SOCK_PATH = STATE_DIR / "agent-hub.sock"

DEFAULT_CONFIG: dict[str, Any] = {
    "name": "Codex-",
    "address": None,
    "interval": 10.0,
    "scan_timeout": 8.0,
    "restart_delay": 5.0,
    "verbose": True,
    "no_approval_proxy": True,
    "opencodex": True,
    "opencodex_ttl": 180.0,
    "agent_hub_sock": str(AGENT_HUB_SOCK_PATH),
    "agent_recent_window": 300.0,
    "prompt_translate": "auto",
    "prompt_translate_timeout_ms": 600,
    "mymemory_email": None,
}


def ensure_state_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
