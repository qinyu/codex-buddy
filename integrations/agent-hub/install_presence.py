#!/usr/bin/env python3
"""Install Stick Agent Hub presence hooks (no Ping Island dependency)."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
NOTIFY = REPO / "tools" / "agent_hub_notify.py"
NOTIFY_TOKEN = "__CODEX_BUDDY_NOTIFY__"
CURSOR_HOOKS = Path.home() / ".cursor" / "hooks.json"
PI_EXT = Path.home() / ".pi" / "agent" / "extensions" / "codex_buddy_hub"
HERMES_PLUGIN = Path.home() / ".hermes" / "plugins" / "codex_buddy_hub"

CURSOR_EVENTS = (
    "sessionStart",
    "sessionEnd",
    "beforeSubmitPrompt",
    "preToolUse",
    "postToolUse",
    "preCompact",
    "stop",
    "subagentStop",
)


def render_notify(src: Path, dest: Path) -> None:
    """Copy template and inject this checkout's notify script path."""
    text = src.read_text()
    if NOTIFY_TOKEN not in text:
        raise SystemExit(f"{src} missing {NOTIFY_TOKEN} placeholder")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text.replace(NOTIFY_TOKEN, str(NOTIFY)))


def cursor_command() -> str:
    return f'/usr/bin/env python3 "{NOTIFY}" --client-kind cursor --client-name Cursor'


def install_cursor() -> None:
    if not CURSOR_HOOKS.exists():
        data = {"version": 1, "hooks": {}}
    else:
        data = json.loads(CURSOR_HOOKS.read_text())
    hooks = data.setdefault("hooks", {})
    cmd = cursor_command()
    marker = "agent_hub_notify.py"
    for event in CURSOR_EVENTS:
        entries = hooks.setdefault(event, [])
        # Refresh any prior install that pointed at an old checkout path.
        entries[:] = [
            item
            for item in entries
            if not (isinstance(item, dict) and marker in str(item.get("command", "")))
        ]
        entries.append({"command": cmd, "type": "command"})
    CURSOR_HOOKS.parent.mkdir(parents=True, exist_ok=True)
    CURSOR_HOOKS.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"cursor hooks updated: {CURSOR_HOOKS}")


def install_pi() -> None:
    src = REPO / "integrations" / "agent-hub" / "pi" / "index.ts"
    render_notify(src, PI_EXT / "index.ts")
    print(f"pi extension installed: {PI_EXT}")


def install_hermes() -> None:
    src = REPO / "integrations" / "agent-hub" / "hermes"
    HERMES_PLUGIN.mkdir(parents=True, exist_ok=True)
    render_notify(src / "__init__.py", HERMES_PLUGIN / "__init__.py")
    shutil.copy2(src / "plugin.yaml", HERMES_PLUGIN / "plugin.yaml")
    print(f"hermes plugin installed: {HERMES_PLUGIN}")


def main() -> int:
    if not NOTIFY.exists():
        print(f"missing {NOTIFY}", file=sys.stderr)
        return 1
    install_cursor()
    install_pi()
    install_hermes()
    print("dsh: no stable hook surface yet — Hub accepts client_kind=dsh when wired")
    print("done (Stick-only; Ping Island not required)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
