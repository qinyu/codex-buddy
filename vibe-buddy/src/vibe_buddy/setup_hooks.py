"""Install host-agent hooks that call the installed vibe-buddy CLI.

Default (no --agent): scan the machine for known tools and configure only
those that are present. Explicit --agent overrides detection.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
INTEGRATIONS = REPO_ROOT / "integrations" / "agent-hub"
VIBE_BUDDY_TOKEN = "__VIBE_BUDDY__"

HOME = Path.home()
APPLICATIONS = Path("/Applications")
CURSOR_HOOKS = HOME / ".cursor" / "hooks.json"
CLAUDE_SETTINGS = HOME / ".claude" / "settings.json"
PI_EXT = HOME / ".pi" / "agent" / "extensions" / "codex_buddy_hub"
HERMES_PLUGIN = HOME / ".hermes" / "plugins" / "codex_buddy_hub"
CODEX_PLUGIN_HOOKS = REPO_ROOT / "plugins" / "codex-usage-stick" / "hooks.json"
BRIDGE_CONFIG = HOME / ".codex" / "codex-usage-bridge" / "config.json"
OPENCODEX_TOKEN = HOME / ".opencodex" / "admin-api-token"

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

CLAUDE_EVENTS = (
    "SessionStart",
    "SessionEnd",
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "Stop",
)

LEGACY_MARKERS = (
    "agent_hub_notify.py",
    "vibe-buddy post",
    "vibe_buddy",
    "vibe-buddy hook",
)


def _which(*names: str) -> str | None:
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    return None


def _app(*names: str) -> bool:
    return any((APPLICATIONS / name).exists() for name in names)


def _dir(*paths: Path) -> bool:
    return any(p.is_dir() for p in paths)


def _file(*paths: Path) -> bool:
    return any(p.is_file() for p in paths)


@dataclass(frozen=True)
class AgentSpec:
    id: str
    title: str
    kind: str  # "hooks" | "service" | "note"
    detect: Callable[[], bool]
    install: Callable[[str], None] | None
    notes: str = ""


def resolve_vibe_buddy() -> str:
    """Absolute path to the installed console script."""
    exe = _which("vibe-buddy")
    if not exe:
        print(
            "vibe-buddy not found on PATH.\n"
            "Install first:\n"
            "  cd vibe-buddy && uv tool install -e .\n"
            "Ensure ~/.local/bin (or uv's tool bin dir) is on PATH, then retry.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    return str(Path(exe).resolve())


def render_template(src: Path, dest: Path, vibe_buddy: str) -> None:
    text = src.read_text()
    if VIBE_BUDDY_TOKEN not in text:
        raise SystemExit(f"{src} missing {VIBE_BUDDY_TOKEN} placeholder")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text.replace(VIBE_BUDDY_TOKEN, vibe_buddy))


def _is_our_command(command: str) -> bool:
    return any(marker in command for marker in LEGACY_MARKERS)


def _is_our_hook_item(item: object) -> bool:
    if not isinstance(item, dict):
        return False
    if _is_our_command(str(item.get("command", ""))):
        return True
    nested = item.get("hooks")
    if isinstance(nested, list):
        return any(
            isinstance(h, dict) and _is_our_command(str(h.get("command", "")))
            for h in nested
        )
    return False


def install_cursor(vibe_buddy: str) -> None:
    if CURSOR_HOOKS.exists():
        data: dict[str, Any] = json.loads(CURSOR_HOOKS.read_text())
    else:
        data = {"version": 1, "hooks": {}}
    hooks = data.setdefault("hooks", {})
    cmd = f'"{vibe_buddy}" post --client-kind cursor --client-name Cursor'
    for event in CURSOR_EVENTS:
        entries = hooks.setdefault(event, [])
        if not isinstance(entries, list):
            entries = []
            hooks[event] = entries
        entries[:] = [item for item in entries if not _is_our_hook_item(item)]
        entries.append({"command": cmd, "type": "command"})
    CURSOR_HOOKS.parent.mkdir(parents=True, exist_ok=True)
    CURSOR_HOOKS.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"cursor: {CURSOR_HOOKS}")
    print(f"  → {cmd}")


def install_claude(vibe_buddy: str) -> None:
    """Wire Claude Code (~/.claude/settings.json) Agent Hub presence hooks."""
    if CLAUDE_SETTINGS.exists():
        data = json.loads(CLAUDE_SETTINGS.read_text())
        if not isinstance(data, dict):
            data = {}
    else:
        data = {}
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        hooks = {}
        data["hooks"] = hooks
    cmd = f'"{vibe_buddy}" post --client-kind claude --client-name Claude'
    entry = {
        "matcher": "*",
        "hooks": [{"type": "command", "command": cmd, "timeout": 8}],
    }
    for event in CLAUDE_EVENTS:
        entries = hooks.setdefault(event, [])
        if not isinstance(entries, list):
            entries = []
            hooks[event] = entries
        entries[:] = [item for item in entries if not _is_our_hook_item(item)]
        entries.append(entry)
    CLAUDE_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    CLAUDE_SETTINGS.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"claude: {CLAUDE_SETTINGS}")
    print(f"  → {cmd}")


def install_pi(vibe_buddy: str) -> None:
    src = INTEGRATIONS / "pi" / "index.ts"
    if not src.exists():
        print(f"pi: template missing ({src})", file=sys.stderr)
        return
    render_template(src, PI_EXT / "index.ts", vibe_buddy)
    print(f"pi: {PI_EXT}")


def install_hermes(vibe_buddy: str) -> None:
    src = INTEGRATIONS / "hermes"
    if not (src / "__init__.py").exists():
        print(f"hermes: template missing ({src})", file=sys.stderr)
        return
    HERMES_PLUGIN.mkdir(parents=True, exist_ok=True)
    render_template(src / "__init__.py", HERMES_PLUGIN / "__init__.py", vibe_buddy)
    shutil.copy2(src / "plugin.yaml", HERMES_PLUGIN / "plugin.yaml")
    print(f"hermes: {HERMES_PLUGIN}")


def install_codex(vibe_buddy: str) -> None:
    if CODEX_PLUGIN_HOOKS.exists():
        text = CODEX_PLUGIN_HOOKS.read_text()
        if "vibe-buddy hook" in text:
            print(f"codex: plugin hooks use vibe-buddy ({CODEX_PLUGIN_HOOKS})")
        else:
            print(
                f"codex: update {CODEX_PLUGIN_HOOKS} to call `vibe-buddy hook --event …`",
                file=sys.stderr,
            )
    print(
        "codex: ensure plugin hooks are enabled "
        f"(`codex features enable plugin_hooks`); CLI → {vibe_buddy}"
    )


def install_opencodex(_vibe_buddy: str) -> None:
    """Enable OpenCodex quota pull in bridge config — no OpenCodex-side edits."""
    from vibe_buddy.paths import DEFAULT_CONFIG, ensure_state_dir

    ensure_state_dir()
    cfg: dict[str, Any] = dict(DEFAULT_CONFIG)
    if BRIDGE_CONFIG.exists():
        try:
            loaded = json.loads(BRIDGE_CONFIG.read_text())
            if isinstance(loaded, dict):
                cfg.update(loaded)
        except json.JSONDecodeError:
            pass
    cfg["opencodex"] = True
    cfg.setdefault("opencodex_ttl", 180.0)
    BRIDGE_CONFIG.write_text(json.dumps(cfg, indent=2) + "\n")
    token = "yes" if OPENCODEX_TOKEN.is_file() else "missing"
    print(f"opencodex: bridge config {BRIDGE_CONFIG} (opencodex=true)")
    print(f"  token file: {OPENCODEX_TOKEN} ({token})")
    print("  no OpenCodex app config changes required — keep it running on :10100")


def install_dsh(_vibe_buddy: str) -> None:
    print(
        "dsh: detected, but no stable host hook surface yet — "
        "Hub accepts `vibe-buddy post --client-kind dsh` when wired"
    )


def install_note(name: str, message: str) -> Callable[[str], None]:
    def _install(_vibe_buddy: str) -> None:
        print(f"{name}: {message}")

    return _install


# Catalog seeded from a typical Mac install set (bins + Apps + ~/.dirs).
AGENTS: tuple[AgentSpec, ...] = (
    AgentSpec(
        id="cursor",
        title="Cursor",
        kind="hooks",
        detect=lambda: bool(
            _which("cursor", "Cursor")
            or _app("Cursor.app")
            or _dir(HOME / ".cursor")
        ),
        install=install_cursor,
        notes="~/.cursor/hooks.json",
    ),
    AgentSpec(
        id="codex",
        title="Codex",
        kind="hooks",
        detect=lambda: bool(_which("codex") or _dir(HOME / ".codex")),
        install=install_codex,
        notes="Codex plugin hooks → vibe-buddy hook",
    ),
    AgentSpec(
        id="claude",
        title="Claude Code",
        kind="hooks",
        detect=lambda: bool(
            _which("claude")
            or _app("Claude.app")
            or _file(CLAUDE_SETTINGS)
            or _dir(HOME / ".claude")
        ),
        install=install_claude,
        notes="~/.claude/settings.json hooks",
    ),
    AgentSpec(
        id="pi",
        title="Pi",
        kind="hooks",
        detect=lambda: bool(_which("pi") or _dir(HOME / ".pi")),
        install=install_pi,
        notes="~/.pi/agent/extensions/codex_buddy_hub",
    ),
    AgentSpec(
        id="hermes",
        title="Hermes",
        kind="hooks",
        detect=lambda: bool(_which("hermes") or _dir(HOME / ".hermes")),
        install=install_hermes,
        notes="~/.hermes/plugins/codex_buddy_hub",
    ),
    AgentSpec(
        id="dsh",
        title="DeepSeek Harness",
        kind="note",
        detect=lambda: bool(_which("dsh")),
        install=install_dsh,
        notes="no stable hook API yet",
    ),
    AgentSpec(
        id="opencodex",
        title="OpenCodex",
        kind="service",
        detect=lambda: bool(
            _which("opencodex", "open-codex")
            or _file(OPENCODEX_TOKEN)
            or _dir(HOME / ".opencodex")
        ),
        install=install_opencodex,
        notes="quota source for Stick meters (not Agent Hub)",
    ),
    AgentSpec(
        id="aider",
        title="Aider",
        kind="note",
        detect=lambda: bool(_which("aider") or _dir(HOME / ".aider")),
        install=install_note(
            "aider",
            "detected — no first-class hooks; optional manual "
            "`vibe-buddy post --client-kind aider` wrappers later",
        ),
        notes="detect-only",
    ),
    AgentSpec(
        id="kimi",
        title="Kimi",
        kind="note",
        detect=lambda: bool(_app("Kimi.app") or _which("kimi")),
        install=install_note(
            "kimi",
            "app detected — no public agent-hook surface for Stick Hub yet",
        ),
        notes="detect-only",
    ),
    AgentSpec(
        id="zed",
        title="Zed",
        kind="note",
        detect=lambda: bool(_app("Zed.app") or _which("zed")),
        install=install_note(
            "zed",
            "app detected — not wired (no Stick Agent Hub hooks)",
        ),
        notes="detect-only",
    ),
)

AGENT_BY_ID = {a.id: a for a in AGENTS}
KNOWN_AGENTS = tuple(a.id for a in AGENTS)


def detect_agents() -> list[str]:
    """Return ids of catalog agents that appear installed on this machine."""
    found = [a.id for a in AGENTS if a.detect()]
    return found


def scan_report() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for agent in AGENTS:
        present = False
        try:
            present = bool(agent.detect())
        except Exception as exc:  # pragma: no cover - defensive
            rows.append(
                {
                    "id": agent.id,
                    "title": agent.title,
                    "kind": agent.kind,
                    "installed": False,
                    "error": repr(exc),
                    "notes": agent.notes,
                }
            )
            continue
        rows.append(
            {
                "id": agent.id,
                "title": agent.title,
                "kind": agent.kind,
                "installed": present,
                "wireable": agent.install is not None and agent.kind in {"hooks", "service"},
                "notes": agent.notes,
            }
        )
    return rows


def parse_agents(raw: list[str] | None, *, auto: bool) -> list[str]:
    if not raw:
        if auto:
            found = detect_agents()
            if not found:
                print("no known agents detected on this machine", file=sys.stderr)
            return found
        return ["cursor", "pi", "hermes", "codex"]
    agents: list[str] = []
    for item in raw:
        for part in item.split(","):
            name = part.strip().lower()
            if not name:
                continue
            if name in {"all", "*"}:
                return list(KNOWN_AGENTS)
            if name in {"auto", "detect", "scan"}:
                return detect_agents()
            if name not in AGENT_BY_ID:
                raise SystemExit(
                    f"unknown agent {name!r}; choose from: {', '.join(KNOWN_AGENTS)}, all, auto"
                )
            if name not in agents:
                agents.append(name)
    return agents


def setup_hooks(
    agents: list[str] | None = None,
    *,
    vibe_buddy: str | None = None,
    dry_run: bool = False,
    scan_only: bool = False,
) -> int:
    if scan_only:
        rows = scan_report()
        print(json.dumps({"agents": rows}, indent=2))
        return 0

    exe = vibe_buddy or resolve_vibe_buddy()
    selected = parse_agents(agents, auto=agents is None)
    print(f"using CLI: {exe}")
    if agents is None:
        print(f"auto-detected: {', '.join(selected) or '(none)'}")
    for name in selected:
        spec = AGENT_BY_ID[name]
        if dry_run:
            print(f"would configure {name} ({spec.kind}): {spec.notes}")
            continue
        if spec.install is None:
            print(f"{name}: no installer")
            continue
        spec.install(exe)
    print("done" if not dry_run else "dry-run done")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Wire host agents to the installed vibe-buddy CLI. "
            "With no --agent, scan the machine and configure installed tools."
        ),
    )
    parser.add_argument(
        "--agent",
        action="append",
        dest="agents",
        metavar="NAME",
        help=(
            "Agent(s) to configure (repeatable / comma-separated): "
            f"{', '.join(KNOWN_AGENTS)}, all, auto. "
            "Default: auto-detect installed tools"
        ),
    )
    parser.add_argument(
        "--vibe-buddy",
        default=None,
        help="Absolute path to vibe-buddy (default: resolve from PATH)",
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Only print detection JSON for the catalog; do not write hooks",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be configured without writing files",
    )
    args = parser.parse_args(argv)
    return setup_hooks(
        args.agents,
        vibe_buddy=args.vibe_buddy,
        dry_run=args.dry_run,
        scan_only=args.scan,
    )


if __name__ == "__main__":
    raise SystemExit(main())
