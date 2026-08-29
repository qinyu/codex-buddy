#!/usr/bin/env python3
"""Supervise the Vibe Buddy BLE bridge once per user session."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from vibe_buddy.paths import (
    CONFIG_PATH,
    DEFAULT_CONFIG,
    HOOK_LOG_PATH,
    LOG_PATH,
    PID_PATH,
    ensure_state_dir,
)

SHUTDOWN = False


def load_config() -> dict[str, Any]:
    ensure_state_dir()
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2) + "\n")
        return dict(DEFAULT_CONFIG)
    try:
        loaded = json.loads(CONFIG_PATH.read_text())
    except json.JSONDecodeError:
        loaded = {}
    cfg = dict(DEFAULT_CONFIG)
    if isinstance(loaded, dict):
        cfg.update(loaded)
    return cfg


def process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def running_pid() -> int | None:
    try:
        pid = int(PID_PATH.read_text().strip())
    except (OSError, ValueError):
        return None
    if process_alive(pid):
        return pid
    try:
        PID_PATH.unlink()
    except OSError:
        pass
    return None


def _vibe_buddy_argv() -> list[str]:
    """Prefer installed console script; fall back to `python -m vibe_buddy`."""
    from shutil import which

    exe = which("vibe-buddy")
    if exe:
        return [exe]
    return [sys.executable, "-m", "vibe_buddy"]


def bridge_command(cfg: dict[str, Any]) -> list[str]:
    cmd = [*_vibe_buddy_argv(), "bridge", "--"]
    name = cfg.get("name")
    if name:
        cmd.extend(["--name", str(name)])
    address = cfg.get("address")
    if address:
        cmd.extend(["--address", str(address)])
    if cfg.get("interval") is not None:
        cmd.extend(["--interval", str(cfg["interval"])])
    if cfg.get("scan_timeout") is not None:
        cmd.extend(["--scan-timeout", str(cfg["scan_timeout"])])
    if cfg.get("verbose", True):
        cmd.append("--verbose")
    if cfg.get("no_approval_proxy", True):
        cmd.append("--no-approval-proxy")
    if cfg.get("opencodex", True):
        cmd.append("--opencodex")
        if cfg.get("opencodex_url"):
            cmd.extend(["--opencodex-url", str(cfg["opencodex_url"])])
        if cfg.get("opencodex_token_file"):
            cmd.extend(["--opencodex-token-file", str(cfg["opencodex_token_file"])])
        if cfg.get("opencodex_ttl") is not None:
            cmd.extend(["--opencodex-ttl", str(cfg["opencodex_ttl"])])
        if cfg.get("opencodex_timeout") is not None:
            cmd.extend(["--opencodex-timeout", str(cfg["opencodex_timeout"])])
    hub_sock = cfg.get("agent_hub_sock")
    if hub_sock:
        cmd.extend(["--agent-hub-sock", str(hub_sock)])
    if cfg.get("agent_recent_window") is not None:
        cmd.extend(["--agent-recent-window", str(cfg["agent_recent_window"])])
    prompt_translate = cfg.get("prompt_translate", "auto")
    if prompt_translate:
        cmd.extend(["--prompt-translate", str(prompt_translate)])
    if cfg.get("prompt_translate_timeout_ms") is not None:
        cmd.extend(
            ["--prompt-translate-timeout-ms", str(cfg["prompt_translate_timeout_ms"])]
        )
    mymemory_email = cfg.get("mymemory_email")
    if mymemory_email:
        cmd.extend(["--mymemory-email", str(mymemory_email)])
    return cmd


def supervisor_command() -> list[str]:
    return [*_vibe_buddy_argv(), "start", "--supervise"]


def request_shutdown(_signum: int, _frame: object) -> None:
    global SHUTDOWN
    SHUTDOWN = True


def supervise_bridge() -> int:
    signal.signal(signal.SIGTERM, request_shutdown)
    signal.signal(signal.SIGINT, request_shutdown)

    while not SHUTDOWN:
        cfg = load_config()
        proc = subprocess.Popen(bridge_command(cfg))
        while proc.poll() is None:
            if SHUTDOWN:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                break
            time.sleep(1)
        if not SHUTDOWN:
            delay = float(cfg.get("restart_delay", 5.0) or 5.0)
            time.sleep(max(1.0, delay))
    return 0


def start_bridge(foreground: bool = False) -> int:
    cfg = load_config()

    if foreground:
        return subprocess.call(bridge_command(cfg))

    pid = running_pid()
    if pid is not None:
        return 0

    ensure_state_dir()
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    with LOG_PATH.open("ab") as log:
        proc = subprocess.Popen(
            supervisor_command(),
            stdout=log,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            env=env,
        )
    PID_PATH.write_text(f"{proc.pid}\n")
    return 0


def ensure_running() -> int:
    """Idempotent start for hooks."""
    return start_bridge(foreground=False)


def stop_bridge() -> int:
    pid = running_pid()
    if pid is None:
        return 0
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        PID_PATH.unlink()
    except OSError:
        pass
    return 0


def status() -> int:
    cfg = load_config()
    pid = running_pid()
    state = "running" if pid is not None else "stopped"
    print(
        json.dumps(
            {
                "state": state,
                "pid": pid,
                "config": str(CONFIG_PATH),
                "log": str(LOG_PATH),
                "hook_log": str(HOOK_LOG_PATH),
                "command": supervisor_command(),
                "bridge_command": bridge_command(cfg),
            },
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Start/stop the Vibe Buddy BLE bridge.")
    parser.add_argument("--foreground", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--stop", action="store_true")
    parser.add_argument("--supervise", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.supervise:
        return supervise_bridge()
    if args.status:
        return status()
    if args.stop:
        return stop_bridge()
    return start_bridge(foreground=args.foreground)


if __name__ == "__main__":
    raise SystemExit(main())
