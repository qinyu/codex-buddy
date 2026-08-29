#!/usr/bin/env python3
"""Codex hook entry for Vibe Buddy (PermissionRequest + Agent Hub presence)."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import select
import socket
import sys
import time
from typing import Any

from vibe_buddy.paths import (
    AGENT_HUB_SOCK_PATH,
    APPROVAL_SOCK_PATH,
    HOOK_LOG_PATH,
    STATE_DIR,
    ensure_state_dir,
)
from vibe_buddy.supervisor import ensure_running

APPROVAL_WAIT_SEC = 45.0
APPROVAL_CONNECT_SEC = 4.0


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def read_stdin_text() -> str:
    """Read hook stdin only when data is already available."""
    try:
        if sys.stdin is None or sys.stdin.closed or sys.stdin.isatty():
            return ""
        ready, _, _ = select.select([sys.stdin], [], [], 0)
        if not ready:
            return ""
        return sys.stdin.read(65536)
    except Exception as exc:  # pragma: no cover - diagnostic best effort
        return f"<stdin unavailable: {exc}>"


def append_log(record: dict[str, Any]) -> None:
    try:
        ensure_state_dir()
        with HOOK_LOG_PATH.open("a", encoding="utf-8") as log:
            log.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    except OSError:
        pass


def env_snapshot() -> dict[str, str | None]:
    keys = [
        "PLUGIN_ROOT",
        "PLUGIN_DATA",
        "CLAUDE_PLUGIN_ROOT",
        "CLAUDE_PLUGIN_DATA",
        "CODEX_HOME",
        "PWD",
    ]
    return {key: os.environ.get(key) for key in keys}


def permission_output(behavior: str, message: str) -> dict[str, Any]:
    return {
        "continue": True,
        "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": {
                "behavior": behavior,
                "message": message,
            },
        },
    }


def request_hardware_permission(hook_payload: dict[str, Any]) -> dict[str, Any] | None:
    request = {
        "type": "permission_request",
        "hook": hook_payload,
        "timeout": APPROVAL_WAIT_SEC,
    }
    encoded = (json.dumps(request, separators=(",", ":"), ensure_ascii=False) + "\n").encode(
        "utf-8"
    )
    connect_deadline = time.monotonic() + APPROVAL_CONNECT_SEC
    last_error = ""

    while True:
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(max(0.2, min(1.0, connect_deadline - time.monotonic())))
                sock.connect(str(APPROVAL_SOCK_PATH))
                sock.sendall(encoded)
                sock.settimeout(APPROVAL_WAIT_SEC + 2.0)
                raw = sock.makefile("rb").readline(4096)
            if not raw:
                append_log(
                    {
                        "time": now_iso(),
                        "event": "PermissionRequest",
                        "phase": "approval_ipc_empty",
                    }
                )
                return None
            response = json.loads(raw.decode("utf-8", errors="replace"))
            append_log(
                {
                    "time": now_iso(),
                    "event": "PermissionRequest",
                    "phase": "approval_ipc_response",
                    "response": response,
                }
            )
            if not response.get("ok"):
                return None
            decision = response.get("decision")
            if decision == "allow":
                return permission_output("allow", "Approved from StickS3")
            if decision == "deny":
                return permission_output("deny", "Denied from StickS3")
            return None
        except (FileNotFoundError, ConnectionRefusedError, socket.timeout, OSError) as exc:
            last_error = repr(exc)
            if time.monotonic() >= connect_deadline:
                append_log(
                    {
                        "time": now_iso(),
                        "event": "PermissionRequest",
                        "phase": "approval_ipc_unavailable",
                        "socket": str(APPROVAL_SOCK_PATH),
                        "error": last_error,
                    }
                )
                return None
            time.sleep(0.2)
        except Exception as exc:  # pragma: no cover - keep hook fail-open
            append_log(
                {
                    "time": now_iso(),
                    "event": "PermissionRequest",
                    "phase": "approval_ipc_error",
                    "error": repr(exc),
                }
            )
            return None


def notify_agent_hub(event: str, stdin_text: str) -> None:
    """Best-effort dual-send of Codex hooks into the Stick Agent Hub socket."""
    try:
        hook = json.loads(stdin_text) if stdin_text else {}
        if not isinstance(hook, dict):
            hook = {}
    except json.JSONDecodeError:
        hook = {}
    envelope = {
        "source": "codex",
        "client_kind": "codex",
        "client_name": "CODEX",
        "hook_event_name": hook.get("hook_event_name") or event,
    }
    envelope.update(hook)
    encoded = (json.dumps(envelope, separators=(",", ":"), ensure_ascii=False) + "\n").encode(
        "utf-8"
    )
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.8)
            sock.connect(str(AGENT_HUB_SOCK_PATH))
            sock.sendall(encoded)
            sock.makefile("rb").readline(4096)
        append_log({"time": now_iso(), "event": event, "phase": "agent_hub_ok"})
    except (FileNotFoundError, ConnectionRefusedError, socket.timeout, OSError) as exc:
        append_log(
            {
                "time": now_iso(),
                "event": event,
                "phase": "agent_hub_skip",
                "socket": str(AGENT_HUB_SOCK_PATH),
                "error": repr(exc),
            }
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Vibe Buddy Codex hook entry point.")
    parser.add_argument("--event", default="unknown", help="Hook event name")
    args = parser.parse_args(argv)

    stdin_text = read_stdin_text()
    append_log(
        {
            "time": now_iso(),
            "event": args.event,
            "phase": "received",
            "argv": sys.argv,
            "cwd": os.getcwd(),
            "state_dir": str(STATE_DIR),
            "env": env_snapshot(),
            "stdin_preview": stdin_text[:4096],
        }
    )

    try:
        rc = ensure_running()
        append_log(
            {
                "time": now_iso(),
                "event": args.event,
                "phase": "ensure_running",
                "returncode": rc,
            }
        )
    except Exception as exc:  # pragma: no cover - hook must stay non-fatal
        append_log(
            {
                "time": now_iso(),
                "event": args.event,
                "phase": "error",
                "error": repr(exc),
            }
        )

    notify_agent_hub(args.event, stdin_text)

    if args.event == "PermissionRequest":
        try:
            hook_payload = json.loads(stdin_text) if stdin_text else {}
        except json.JSONDecodeError as exc:
            append_log(
                {
                    "time": now_iso(),
                    "event": args.event,
                    "phase": "permission_json_error",
                    "error": repr(exc),
                }
            )
            return 0

        decision = request_hardware_permission(hook_payload)
        if decision:
            sys.stdout.write(json.dumps(decision, separators=(",", ":"), ensure_ascii=False))
            sys.stdout.write("\n")
            sys.stdout.flush()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
