"""Install a macOS LaunchAgent so the BLE bridge starts at login."""

from __future__ import annotations

import argparse
import plistlib
import subprocess
import sys
from pathlib import Path

from vibe_buddy.paths import LOG_PATH, STATE_DIR, ensure_state_dir
from vibe_buddy.setup_hooks import resolve_vibe_buddy
from vibe_buddy.supervisor import stop_bridge

LABEL = "com.vibe-buddy.bridge"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def _launchctl(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["launchctl", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def build_plist(vibe_buddy: str) -> dict:
    ensure_state_dir()
    log = str(LOG_PATH)
    return {
        "Label": LABEL,
        "ProgramArguments": [vibe_buddy, "start", "--supervise"],
        "RunAtLoad": True,
        "KeepAlive": True,
        "ThrottleInterval": 5,
        "WorkingDirectory": str(STATE_DIR),
        "StandardOutPath": log,
        "StandardErrorPath": log,
        "EnvironmentVariables": {
            "PATH": "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:"
            + str(Path(vibe_buddy).parent),
        },
    }


def install_autostart(*, vibe_buddy: str | None = None) -> int:
    if sys.platform != "darwin":
        print("setup-autostart is currently macOS-only (LaunchAgent)", file=sys.stderr)
        return 2
    exe = vibe_buddy or resolve_vibe_buddy()
    # Prefer a single owner: stop the ad-hoc background supervisor first.
    stop_bridge()
    plist = build_plist(exe)
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with PLIST_PATH.open("wb") as fh:
        plistlib.dump(plist, fh)

    # Reload if already present.
    uid = Path.home().stat().st_uid
    domain = f"gui/{uid}"
    _launchctl("bootout", domain, str(PLIST_PATH))
    loaded = _launchctl("bootstrap", domain, str(PLIST_PATH))
    if loaded.returncode != 0:
        # Older macOS / already loaded: try load -w
        loaded = _launchctl("load", "-w", str(PLIST_PATH))
    kicked = _launchctl("kickstart", "-k", f"{domain}/{LABEL}")
    if kicked.returncode != 0:
        _launchctl("start", LABEL)

    print(f"autostart: {PLIST_PATH}")
    print(f"  → {exe} start --supervise (RunAtLoad + KeepAlive)")
    print("  starts at login; launchd restarts if the supervisor exits")
    return 0


def uninstall_autostart() -> int:
    if sys.platform != "darwin":
        print("setup-autostart is currently macOS-only (LaunchAgent)", file=sys.stderr)
        return 2
    uid = Path.home().stat().st_uid
    domain = f"gui/{uid}"
    _launchctl("bootout", domain, str(PLIST_PATH))
    _launchctl("unload", "-w", str(PLIST_PATH))
    if PLIST_PATH.exists():
        PLIST_PATH.unlink()
        print(f"removed {PLIST_PATH}")
    else:
        print("no LaunchAgent installed")
    return 0


def status_autostart() -> int:
    exists = PLIST_PATH.is_file()
    print(f"plist: {PLIST_PATH} ({'present' if exists else 'missing'})")
    if not exists:
        return 1
    uid = Path.home().stat().st_uid
    printed = _launchctl("print", f"gui/{uid}/{LABEL}")
    if printed.returncode == 0:
        # Keep it short — first lines are enough.
        lines = (printed.stdout or "").splitlines()
        for line in lines[:12]:
            print(line)
    else:
        print("launchd: not loaded (will load at next login after install)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Install/remove macOS login autostart for the BLE bridge.",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove the LaunchAgent",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show LaunchAgent status",
    )
    parser.add_argument(
        "--vibe-buddy",
        default=None,
        help="Absolute path to vibe-buddy (default: PATH)",
    )
    args = parser.parse_args(argv)
    if args.status:
        return status_autostart()
    if args.uninstall:
        return uninstall_autostart()
    return install_autostart(vibe_buddy=args.vibe_buddy)


if __name__ == "__main__":
    raise SystemExit(main())
