"""Install host-agent hooks that call the installed vibe-buddy CLI."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
INTEGRATIONS = REPO_ROOT / "integrations" / "agent-hub"
VIBE_BUDDY_TOKEN = "__VIBE_BUDDY__"

CURSOR_HOOKS = Path.home() / ".cursor" / "hooks.json"
PI_EXT = Path.home() / ".pi" / "agent" / "extensions" / "codex_buddy_hub"
HERMES_PLUGIN = Path.home() / ".hermes" / "plugins" / "codex_buddy_hub"
CODEX_PLUGIN_HOOKS = REPO_ROOT / "plugins" / "codex-usage-stick" / "hooks.json"

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

KNOWN_AGENTS = ("cursor", "pi", "hermes", "codex", "dsh")

LEGACY_MARKERS = (
    "agent_hub_notify.py",
    "vibe-buddy post",
    "vibe_buddy",
    "vibe-buddy hook",
)


def resolve_vibe_buddy() -> str:
    """Absolute path to the installed console script."""
    exe = shutil.which("vibe-buddy")
    if not exe:
        # Editable checkout / same interpreter that is running us.
        try:
            from vibe_buddy import __file__ as pkg_file

            # Prefer `python -m vibe_buddy` only as last resort for messaging.
            _ = pkg_file
        except Exception:
            pass
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


def _is_our_hook(item: object) -> bool:
    if not isinstance(item, dict):
        return False
    cmd = str(item.get("command", ""))
    return any(marker in cmd for marker in LEGACY_MARKERS)


def install_cursor(vibe_buddy: str) -> None:
    if not CURSOR_HOOKS.exists():
        data: dict = {"version": 1, "hooks": {}}
    else:
        data = json.loads(CURSOR_HOOKS.read_text())
    hooks = data.setdefault("hooks", {})
    cmd = f'"{vibe_buddy}" post --client-kind cursor --client-name Cursor'
    for event in CURSOR_EVENTS:
        entries = hooks.setdefault(event, [])
        entries[:] = [item for item in entries if not _is_our_hook(item)]
        entries.append({"command": cmd, "type": "command"})
    CURSOR_HOOKS.parent.mkdir(parents=True, exist_ok=True)
    CURSOR_HOOKS.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"cursor: {CURSOR_HOOKS}")
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
    """Codex plugin hooks already call `vibe-buddy hook`; verify + print enable hints."""
    if CODEX_PLUGIN_HOOKS.exists():
        text = CODEX_PLUGIN_HOOKS.read_text()
        if "vibe-buddy hook" in text:
            print(f"codex: plugin hooks already use vibe-buddy ({CODEX_PLUGIN_HOOKS})")
        else:
            print(
                f"codex: update {CODEX_PLUGIN_HOOKS} to call `vibe-buddy hook --event …`",
                file=sys.stderr,
            )
    print(
        "codex: enable plugin hooks if needed:\n"
        "  codex features enable plugin_hooks\n"
        f"  ensure `vibe-buddy` resolves to {vibe_buddy}"
    )


def install_dsh(_vibe_buddy: str) -> None:
    print(
        "dsh: no stable host hook surface yet — "
        "Hub accepts `vibe-buddy post --client-kind dsh` when you wire it"
    )


INSTALLERS = {
    "cursor": install_cursor,
    "pi": install_pi,
    "hermes": install_hermes,
    "codex": install_codex,
    "dsh": install_dsh,
}


def parse_agents(raw: list[str] | None) -> list[str]:
    if not raw:
        return ["cursor", "pi", "hermes", "codex"]
    agents: list[str] = []
    for item in raw:
        for part in item.split(","):
            name = part.strip().lower()
            if not name:
                continue
            if name in {"all", "*"}:
                return list(KNOWN_AGENTS)
            if name not in KNOWN_AGENTS:
                raise SystemExit(
                    f"unknown agent {name!r}; choose from: {', '.join(KNOWN_AGENTS)}, all"
                )
            if name not in agents:
                agents.append(name)
    return agents


def setup_hooks(agents: list[str] | None = None, *, vibe_buddy: str | None = None) -> int:
    exe = vibe_buddy or resolve_vibe_buddy()
    selected = parse_agents(agents)
    print(f"using CLI: {exe}")
    for name in selected:
        INSTALLERS[name](exe)
    print("done")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Wire host agents to the installed vibe-buddy CLI.",
    )
    parser.add_argument(
        "--agent",
        action="append",
        dest="agents",
        metavar="NAME",
        help=(
            "Agent to configure (repeatable or comma-separated): "
            f"{', '.join(KNOWN_AGENTS)}, all. Default: cursor,pi,hermes,codex"
        ),
    )
    parser.add_argument(
        "--vibe-buddy",
        default=None,
        help="Absolute path to vibe-buddy (default: resolve from PATH)",
    )
    args = parser.parse_args(argv)
    return setup_hooks(args.agents, vibe_buddy=args.vibe_buddy)


if __name__ == "__main__":
    raise SystemExit(main())
