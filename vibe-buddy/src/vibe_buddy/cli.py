"""Console entry: vibe-buddy start|stop|status|hook|post|bridge|tee."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(
        prog="vibe-buddy",
        description="Vibe Buddy PC companion for StickS3 (BLE bridge + hooks).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_start = sub.add_parser("start", help="Start or reuse the bridge supervisor")
    p_start.add_argument("--foreground", action="store_true", help="Run bridge in foreground")
    p_start.add_argument(
        "--supervise",
        action="store_true",
        help=argparse.SUPPRESS,
    )

    sub.add_parser("stop", help="Stop the bridge supervisor")
    sub.add_parser("status", help="Print bridge status JSON")

    p_hook = sub.add_parser("hook", help="Codex plugin hook entry (stdin = hook JSON)")
    p_hook.add_argument("--event", default="unknown", help="Hook event name")

    p_post = sub.add_parser("post", help="Post a hook event to Agent Hub (stdin = JSON)")
    p_post.add_argument("--client-kind", required=True)
    p_post.add_argument("--client-name", default="")
    p_post.add_argument("--source", default="")
    p_post.add_argument("--event", default="")
    p_post.add_argument("--agent-hub-sock", default=None)

    p_bridge = sub.add_parser("bridge", help="Run the BLE bridge in this process")
    p_bridge.add_argument(
        "bridge_args",
        nargs=argparse.REMAINDER,
        help="Forwarded to the bridge (prefix with --)",
    )

    p_tee = sub.add_parser("tee", help="Tee stdin to Ping Island + Agent Hub")
    p_tee.add_argument("tee_args", nargs=argparse.REMAINDER)

    p_setup = sub.add_parser(
        "setup-hooks",
        help="Scan installed agents and wire hooks to this vibe-buddy (or --agent …)",
    )
    p_setup.add_argument(
        "--agent",
        action="append",
        dest="agents",
        metavar="NAME",
        help="Agent(s): cursor,codex,claude,pi,hermes,dsh,opencodex,… / all / auto (default: auto-detect)",
    )
    p_setup.add_argument(
        "--vibe-buddy",
        default=None,
        help="Absolute path to vibe-buddy binary (default: PATH)",
    )
    p_setup.add_argument(
        "--scan",
        action="store_true",
        help="Print installed-tool detection JSON only",
    )
    p_setup.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be configured without writing",
    )

    args = parser.parse_args(argv)

    if args.cmd == "start":
        from vibe_buddy.supervisor import start_bridge, supervise_bridge

        if args.supervise:
            return supervise_bridge()
        return start_bridge(foreground=bool(args.foreground))
    if args.cmd == "stop":
        from vibe_buddy.supervisor import stop_bridge

        return stop_bridge()
    if args.cmd == "status":
        from vibe_buddy.supervisor import status

        return status()
    if args.cmd == "hook":
        from vibe_buddy.hook import main as hook_main

        return hook_main(["--event", args.event])
    if args.cmd == "post":
        from vibe_buddy.notify import main as notify_main

        notify_argv = ["--client-kind", args.client_kind]
        if args.client_name:
            notify_argv.extend(["--client-name", args.client_name])
        if args.source:
            notify_argv.extend(["--source", args.source])
        if args.event:
            notify_argv.extend(["--event", args.event])
        if args.agent_hub_sock:
            notify_argv.extend(["--agent-hub-sock", args.agent_hub_sock])
        return notify_main(notify_argv)
    if args.cmd == "bridge":
        from vibe_buddy.bridge import main as bridge_main

        rest = list(args.bridge_args or [])
        if rest and rest[0] == "--":
            rest = rest[1:]
        return bridge_main(rest)
    if args.cmd == "tee":
        from vibe_buddy.tee import main as tee_main

        rest = list(args.tee_args or [])
        if rest and rest[0] == "--":
            rest = rest[1:]
        return tee_main(rest)
    if args.cmd == "setup-hooks":
        from vibe_buddy.setup_hooks import setup_hooks

        return setup_hooks(
            args.agents,
            vibe_buddy=args.vibe_buddy,
            dry_run=bool(args.dry_run),
            scan_only=bool(args.scan),
        )

    parser.error(f"unknown command: {args.cmd}")
    return 2
