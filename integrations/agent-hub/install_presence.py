#!/usr/bin/env python3
"""Back-compat shim → `vibe-buddy setup-hooks`."""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "vibe-buddy" / "src"
if _SRC.is_dir():
    sys.path.insert(0, str(_SRC))

from vibe_buddy.setup_hooks import main

if __name__ == "__main__":
    raise SystemExit(main())
