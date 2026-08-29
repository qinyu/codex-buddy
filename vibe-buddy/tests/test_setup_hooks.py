#!/usr/bin/env python3
"""Tests for setup-hooks agent catalog / auto-detect."""

from __future__ import annotations

import unittest
from unittest import mock

from vibe_buddy.setup_hooks import AGENT_BY_ID, detect_agents, parse_agents, scan_report


class ParseAgentsTests(unittest.TestCase):
    def test_explicit(self) -> None:
        self.assertEqual(parse_agents(["cursor,pi"], auto=False), ["cursor", "pi"])

    def test_all(self) -> None:
        self.assertEqual(parse_agents(["all"], auto=False), list(AGENT_BY_ID))

    def test_auto_uses_detect(self) -> None:
        with mock.patch(
            "vibe_buddy.setup_hooks.detect_agents", return_value=["cursor", "opencodex"]
        ):
            self.assertEqual(parse_agents(None, auto=True), ["cursor", "opencodex"])
            self.assertEqual(parse_agents(["auto"], auto=False), ["cursor", "opencodex"])


class ScanReportTests(unittest.TestCase):
    def test_report_shape(self) -> None:
        rows = scan_report()
        self.assertTrue(rows)
        self.assertIn("id", rows[0])
        self.assertIn("installed", rows[0])
        ids = {r["id"] for r in rows}
        self.assertTrue({"cursor", "codex", "claude", "opencodex"} <= ids)


if __name__ == "__main__":
    unittest.main()
