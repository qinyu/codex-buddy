#!/usr/bin/env bash
# Idempotent environment bootstrap for the Codex Buddy firmware + BLE bridge.
# Installs PlatformIO (firmware toolchain) and bleak (BLE bridge) into a venv,
# exposes the CLIs on PATH, and warms the ESP32 platform/library caches.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$HOME/.pio-venv"

if command -v sudo >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y python3-venv python3-pip
fi

if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
fi

"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install platformio bleak

# Expose the PlatformIO CLIs on PATH for interactive shells.
if command -v sudo >/dev/null 2>&1; then
  sudo ln -sf "$VENV/bin/pio" /usr/local/bin/pio
  sudo ln -sf "$VENV/bin/platformio" /usr/local/bin/platformio
fi

# Make the project venv the default interpreter for interactive shells so the
# documented `python3 .../codex_usage_ble_bridge.py` workflow (which needs
# bleak) works without activating the venv by hand.
SNIPPET="export PATH=\"$VENV/bin:\$PATH\""
if ! grep -qF "$SNIPPET" "$HOME/.bashrc" 2>/dev/null; then
  printf '\n# Codex Buddy project venv (PlatformIO + bleak)\n%s\n' "$SNIPPET" >> "$HOME/.bashrc"
fi

# Pre-fetch the ESP32 platform, toolchains, and libraries so the first
# `pio run` is fast and works even without network access.
cd "$REPO_ROOT"
"$VENV/bin/pio" pkg install
