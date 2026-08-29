#!/usr/bin/env python3
"""Notify Stick Agent Hub from any agent hook.

Independent of Ping Island: only talks to the BLE bridge unix socket.
Fails open (exit 0) when the bridge is offline so host agents stay green.

Usage (stdin = hook JSON):

  vibe-buddy post --client-kind cursor --client-name Cursor
  vibe-buddy post --client-kind pi --event UserPromptSubmit
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from pathlib import Path
from typing import Any

from vibe_buddy.paths import AGENT_HUB_SOCK_PATH


def read_stdin() -> dict[str, Any]:
    try:
        raw = sys.stdin.buffer.read()
        if not raw:
            return {}
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def send_hub(sock_path: Path, envelope: dict[str, Any]) -> None:
    if not sock_path.exists():
        return
    payload = (json.dumps(envelope, separators=(",", ":"), ensure_ascii=False) + "\n").encode(
        "utf-8"
    )
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.8)
        sock.connect(str(sock_path))
        sock.sendall(payload)
        with sock.makefile("rb") as reader:
            reader.readline(4096)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client-kind", required=True, help="Agent id: cursor|pi|hermes|dsh|codex")
    parser.add_argument("--client-name", default="", help="Display title override")
    parser.add_argument("--source", default="", help="Optional source tag (defaults to client-kind)")
    parser.add_argument("--event", default="", help="Override hook_event_name when stdin lacks one")
    parser.add_argument(
        "--agent-hub-sock",
        type=Path,
        default=Path(os.environ.get("CODEX_AGENT_HUB_SOCK", AGENT_HUB_SOCK_PATH)),
    )
    args = parser.parse_args(argv)

    kind = str(args.client_kind).strip().lower()
    hook = read_stdin()
    envelope: dict[str, Any] = dict(hook)
    envelope["client_kind"] = kind
    envelope["source"] = (args.source or kind).strip() or kind
    if args.client_name.strip():
        envelope["client_name"] = args.client_name.strip()
    elif "client_name" not in envelope:
        envelope["client_name"] = kind.upper()
    if args.event.strip():
        envelope["hook_event_name"] = args.event.strip()
    elif not envelope.get("hook_event_name"):
        for key in ("event", "event_name", "type"):
            value = envelope.get(key)
            if isinstance(value, str) and value.strip():
                envelope["hook_event_name"] = value.strip()
                break

    try:
        send_hub(args.agent_hub_sock.expanduser(), envelope)
    except (FileNotFoundError, ConnectionRefusedError, socket.timeout, OSError, TimeoutError):
        pass
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
