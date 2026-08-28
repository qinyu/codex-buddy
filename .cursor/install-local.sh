#!/usr/bin/env bash
# Local dev bootstrap (macOS/Linux). Uses a project .venv — not Cloud Agent.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$REPO_ROOT/.venv"

if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
fi

"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install platformio bleak

cd "$REPO_ROOT"
"$VENV/bin/pio" pkg install -e m5stack-sticks3

echo ""
echo "Local dev ready. Activate with:"
echo "  source .venv/bin/activate"
echo "  pio run -e m5stack-sticks3 -t upload"
