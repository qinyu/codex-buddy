#!/usr/bin/env python3
"""Tee Ping Island-shaped hook stdin to Island bridge + Stick Agent Hub.

Usage (as a hook command replacement):

  … | tools/agent_hub_hook_tee.py -- \\
        ~/.ping-island/bin/ping-island-bridge --source codex

Identity flags after `--` are copied into the Agent Hub envelope.
The same stdin JSON is forwarded unchanged to the Island bridge process.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any


DEFAULT_HUB_SOCK = Path.home() / ".codex" / "codex-usage-bridge" / "agent-hub.sock"


def parse_identity(argv: list[str]) -> dict[str, Any]:
    identity: dict[str, Any] = {}
    mapping = {
        "--source": "source",
        "--client-kind": "client_kind",
        "--client-name": "client_name",
        "--client-origin": "client_origin",
        "--client-originator": "client_originator",
        "--thread-source": "thread_source",
        "--client-bundle-id": "client_bundle_id",
    }
    i = 0
    while i < len(argv):
        key = argv[i]
        if key in mapping and i + 1 < len(argv):
            identity[mapping[key]] = argv[i + 1]
            i += 2
            continue
        i += 1
    return identity


def send_hub(sock_path: Path, envelope: dict[str, Any]) -> None:
    if not sock_path.exists():
        return
    payload = (json.dumps(envelope, separators=(",", ":")) + "\n").encode("utf-8")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(1.5)
        sock.connect(str(sock_path))
        sock.sendall(payload)
        with sock.makefile("rb") as reader:
            reader.readline()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--agent-hub-sock",
        type=Path,
        default=Path(os.environ.get("CODEX_AGENT_HUB_SOCK", DEFAULT_HUB_SOCK)),
    )
    parser.add_argument(
        "--island-only",
        action="store_true",
        help="Skip Agent Hub delivery (debug)",
    )
    parser.add_argument(
        "--hub-only",
        action="store_true",
        help="Skip Island bridge delivery (debug)",
    )
    parser.add_argument("bridge_argv", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    bridge_argv = list(args.bridge_argv)
    if bridge_argv and bridge_argv[0] == "--":
        bridge_argv = bridge_argv[1:]
    if not bridge_argv and not args.hub_only:
        print("agent_hub_hook_tee: missing Island bridge command after --", file=sys.stderr)
        return 2

    raw = sys.stdin.buffer.read()
    try:
        hook = json.loads(raw.decode("utf-8"))
        if not isinstance(hook, dict):
            hook = {"raw": True}
    except Exception:
        hook = {"raw": True}

    identity = parse_identity(bridge_argv)
    envelope = dict(identity)
    envelope.update(hook)
    envelope.setdefault("source", identity.get("source") or "codex")

    hub_error: str | None = None
    if not args.island_only:
        try:
            send_hub(args.agent_hub_sock.expanduser(), envelope)
        except Exception as exc:
            hub_error = repr(exc)

    island_rc = 0
    if not args.hub_only:
        proc = subprocess.run(bridge_argv, input=raw, check=False)
        island_rc = int(proc.returncode)

    if hub_error and os.environ.get("AGENT_HUB_TEE_VERBOSE"):
        print(f"[agent-hub-tee] hub delivery failed: {hub_error}", file=sys.stderr)

    # Prefer Island exit code so existing hook graphs stay green when Stick is offline.
    return island_rc


if __name__ == "__main__":
    raise SystemExit(main())
