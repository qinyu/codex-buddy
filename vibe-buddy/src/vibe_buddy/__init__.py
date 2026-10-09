"""Vibe Buddy — PC companion for StickS3."""

from __future__ import annotations

from vibe_buddy.supervisor import ensure_running, start_bridge, status, stop_bridge

__all__ = [
    "ensure_running",
    "start_bridge",
    "status",
    "stop_bridge",
    "__version__",
]

__version__ = "0.1.0"
