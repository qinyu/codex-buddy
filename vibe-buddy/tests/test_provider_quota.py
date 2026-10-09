#!/usr/bin/env python3
"""Unit tests for OpenCodex provider quota mapping."""

from __future__ import annotations

import unittest

from vibe_buddy.bridge import (
    UsageSnapshot,
    bar_is_visible,
    map_provider_quota,
    normalize_reset_at,
    parse_balance_display,
    reset_window_sec_for_label,
    MONTHLY_RESET_WINDOW_SEC,
    PRIMARY_RESET_WINDOW_SEC,
    SECONDARY_RESET_WINDOW_SEC,
)


class ProviderQuotaMappingTests(unittest.TestCase):
    def test_openai_monthly_only(self) -> None:
        view = map_provider_quota({"monthlyPercent": 100, "monthlyResetAt": 1790229363})
        self.assertEqual(view.primary.percent, 100)
        self.assertEqual(view.primary.label, "mo")
        self.assertEqual(view.meter_count, 1)
        self.assertFalse(bar_is_visible(view.secondary))

    def test_opencode_three_windows(self) -> None:
        view = map_provider_quota(
            {
                "fiveHourPercent": 0,
                "fiveHourResetAt": 1787909109224,
                "weeklyPercent": 50,
                "weeklyResetAt": 1788134400224,
                "monthlyPercent": 12,
                "monthlyResetAt": 1788244484224,
            }
        )
        self.assertEqual(view.meter_count, 3)
        self.assertEqual(view.primary.label, "5h")
        self.assertEqual(view.secondary.label, "7d")
        self.assertEqual(view.tertiary.label, "mo")
        self.assertEqual(view.primary.reset_at, 1787909109)
        self.assertEqual(view.secondary.reset_at, 1788134400)
        self.assertEqual(view.tertiary.reset_at, 1788244484)

    def test_opencode_five_hour_and_weekly_only(self) -> None:
        view = map_provider_quota(
            {
                "fiveHourPercent": 10,
                "fiveHourResetAt": 1787909109,
                "weeklyPercent": 50,
                "weeklyResetAt": 1788134400,
            }
        )
        self.assertEqual(view.meter_count, 2)
        self.assertEqual(view.primary.label, "5h")
        self.assertEqual(view.secondary.label, "7d")
        self.assertIsNone(view.tertiary)

    def test_deepseek_balance_only(self) -> None:
        view = map_provider_quota(
            {"customWindows": [{"label": "API balance ($80.45)", "percent": 0}]}
        )
        self.assertEqual(view.primary.display, "80")
        self.assertEqual(view.primary.label, "")
        self.assertEqual(view.meter_count, 1)
        self.assertEqual(view.primary.reset_at, 0)

    def test_cursor_three_line_usage(self) -> None:
        view = map_provider_quota(
            {
                "monthlyPercent": 1.21,
                "monthlyResetAt": 1789743659000,
                "customWindows": [
                    {"label": "First-party models", "percent": 0.911, "resetAt": 1789743659000},
                    {"label": "API usage", "percent": 3.018, "resetAt": 1789743659000},
                ],
            }
        )
        self.assertEqual(view.meter_count, 3)
        self.assertEqual(view.primary.label, "tot")
        self.assertEqual(view.primary.percent, 1)
        self.assertEqual(view.secondary.label, "1st")
        self.assertEqual(view.secondary.percent, 1)
        self.assertEqual(view.tertiary.label, "API")
        self.assertEqual(view.tertiary.percent, 3)
        self.assertEqual(view.primary.reset_at, 1789743659)

    def test_xai_weekly_only(self) -> None:
        view = map_provider_quota({"weeklyPercent": 90, "weeklyResetAt": 1788052312491})
        self.assertEqual(view.primary.label, "7d")
        self.assertEqual(view.meter_count, 1)

    def test_normalize_reset_at_milliseconds(self) -> None:
        self.assertEqual(normalize_reset_at(1789743659000), 1789743659)
        self.assertEqual(normalize_reset_at(1790229363), 1790229363)
        self.assertEqual(normalize_reset_at(0), 0)

    def test_parse_balance_display(self) -> None:
        self.assertEqual(parse_balance_display("API balance ($80.45)"), "80")
        self.assertEqual(parse_balance_display("API balance ($9.6)"), "10")
        self.assertIsNone(parse_balance_display("no money here"))

    def test_reset_window_for_labels(self) -> None:
        self.assertEqual(reset_window_sec_for_label("5h"), PRIMARY_RESET_WINDOW_SEC)
        self.assertEqual(reset_window_sec_for_label("7d"), SECONDARY_RESET_WINDOW_SEC)
        self.assertEqual(reset_window_sec_for_label("mo"), MONTHLY_RESET_WINDOW_SEC)
        self.assertEqual(reset_window_sec_for_label("tot"), MONTHLY_RESET_WINDOW_SEC)
        self.assertEqual(reset_window_sec_for_label("bal"), 0)


class UsageSnapshotPacketTests(unittest.TestCase):
    def test_cursor_packet_includes_three_meters(self) -> None:
        snap = UsageSnapshot(
            tokens=0,
            primary=1,
            secondary=1,
            primary_resets_at=1789743659,
            secondary_resets_at=1789743659,
            source=__file__,
            event_ts=None,
            limit_id="cursor",
            limit_name="Cursor",
            provider="cursor",
            label="Cursor",
            provider_index=0,
            provider_count=7,
            primary_label="tot",
            secondary_label="1st",
            tertiary=3,
            tertiary_label="API",
            tertiary_resets_at=1789743659,
            meter_count=3,
        )
        packet = snap.packet("idle")
        self.assertEqual(packet["meter_count"], 3)
        self.assertEqual(packet["tertiary"], 3)
        self.assertEqual(packet["tertiary_label"], "API")
        self.assertEqual(packet["primary_label"], "tot")
        self.assertIn("provider_count", packet)

    def test_single_provider_still_sends_index(self) -> None:
        snap = UsageSnapshot(
            tokens=0,
            primary=10,
            secondary=0,
            primary_resets_at=0,
            secondary_resets_at=0,
            source=__file__,
            event_ts=None,
            limit_id="openai",
            limit_name="OpenAI",
            provider="openai",
            label="OpenAI",
            provider_index=0,
            provider_count=1,
            primary_label="mo",
            meter_count=1,
        )
        packet = snap.packet("idle")
        self.assertEqual(packet["provider_index"], 0)
        self.assertEqual(packet["provider_count"], 1)

    def test_opencode_packet_includes_three_meters(self) -> None:
        snap = UsageSnapshot(
            tokens=0,
            primary=0,
            secondary=50,
            primary_resets_at=1787909109,
            secondary_resets_at=1788134400,
            source=__file__,
            event_ts=None,
            limit_id="opencode-go",
            limit_name="opencode go",
            provider="opencode-go",
            label="opencode go",
            provider_index=1,
            provider_count=7,
            primary_label="5h",
            secondary_label="7d",
            tertiary=12,
            tertiary_label="mo",
            tertiary_resets_at=1788244484,
            meter_count=3,
        )
        packet = snap.packet("idle")
        self.assertEqual(packet["meter_count"], 3)
        self.assertEqual(packet["tertiary_label"], "mo")

    def test_packet_includes_codex_agent_chrome(self) -> None:
        snap = UsageSnapshot(
            tokens=0,
            primary=10,
            secondary=20,
            primary_resets_at=0,
            secondary_resets_at=0,
            source=__file__,
            event_ts=None,
            limit_id="openai",
            limit_name="OpenAI",
            provider="openai",
            label="OpenAI",
            provider_index=0,
            provider_count=1,
            primary_label="mo",
            meter_count=1,
        )
        packet = snap.packet("busy")
        self.assertEqual(packet["agent"], "CODEX")
        self.assertEqual(packet["agent_id"], "codex")
        self.assertEqual(packet["agent_index"], 0)
        self.assertEqual(packet["agent_count"], 1)
        self.assertEqual(packet["state"], "busy")
        self.assertEqual(packet["provider"], "openai")
        self.assertEqual(packet["provider_index"], 0)

    def test_explicit_agent_chrome_overrides_defaults(self) -> None:
        snap = UsageSnapshot(
            tokens=0,
            primary=0,
            secondary=0,
            primary_resets_at=0,
            secondary_resets_at=0,
            source=__file__,
            event_ts=None,
            limit_id=None,
            limit_name=None,
            agent="PI",
            agent_id="pi",
            agent_index=2,
            agent_count=5,
        )
        packet = snap.packet("idle")
        self.assertEqual(packet["agent"], "PI")
        self.assertEqual(packet["agent_id"], "pi")
        self.assertEqual(packet["agent_index"], 2)
        self.assertEqual(packet["agent_count"], 5)


if __name__ == "__main__":
    unittest.main()
