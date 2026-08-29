#!/usr/bin/env python3
"""Packet-seam tests for Agent Hub hook ingest + chrome."""

from __future__ import annotations

import unittest

from vibe_buddy.bridge import AgentHub, UsageSnapshot, resolve_agent_id, state_from_hook_event


def _snap(**kwargs: object) -> UsageSnapshot:
    base = dict(
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
        provider_count=3,
        primary_label="mo",
        meter_count=1,
    )
    base.update(kwargs)
    return UsageSnapshot(**base)  # type: ignore[arg-type]


class AgentIdentityTests(unittest.TestCase):
    def test_resolve_first_class_ids(self) -> None:
        self.assertEqual(resolve_agent_id({"source": "codex"}), "codex")
        self.assertEqual(
            resolve_agent_id(
                {
                    "source": "claude",
                    "client_kind": "hermes",
                    "client_name": "Hermes",
                }
            ),
            "hermes",
        )
        self.assertEqual(
            resolve_agent_id({"client_kind": "pi", "client_name": "Pi Agent"}),
            "pi",
        )
        self.assertEqual(
            resolve_agent_id({"client_kind": "cursor", "client_name": "Cursor"}),
            "cursor",
        )
        self.assertEqual(resolve_agent_id({"client_kind": "dsh"}), "dsh")

    def test_hook_event_mapping(self) -> None:
        self.assertEqual(state_from_hook_event("UserPromptSubmit"), "busy")
        self.assertEqual(state_from_hook_event("PermissionRequest"), "attention")
        self.assertEqual(state_from_hook_event("SessionEnd"), "gone")
        self.assertEqual(state_from_hook_event("Stop"), "idle")


class AgentHubPacketTests(unittest.TestCase):
    def test_interleaved_hooks_build_roster_and_packet_state(self) -> None:
        hub = AgentHub(busy_window=60, attention_window=120, completed_window=25, presence_window=600)
        now = 1_700_000_000.0
        hub.ingest_hook(
            {
                "source": "codex",
                "hook_event_name": "UserPromptSubmit",
                "session_id": "c1",
            },
            now=now,
        )
        hub.ingest_hook(
            {
                "source": "claude",
                "client_kind": "pi",
                "client_name": "Pi Agent",
                "hook_event_name": "PermissionRequest",
                "session_id": "pi-1",
            },
            now=now + 1,
        )
        hub.ingest_hook(
            {
                "source": "claude",
                "client_kind": "hermes",
                "client_name": "Hermes",
                "hook_event_name": "PreToolUse",
                "session_id": "hermes-1",
            },
            now=now + 2,
        )
        hub.ingest_hook(
            {
                "client_kind": "cursor",
                "client_name": "Cursor",
                "hook_event_name": "UserPromptSubmit",
            },
            now=now + 3,
        )
        hub.ingest_hook(
            {"client_kind": "dsh", "hook_event_name": "Stop"},
            now=now + 4,
        )

        self.assertEqual(sorted(hub.agents), ["codex", "cursor", "dsh", "hermes", "pi"])
        hub.current_id = "pi"
        snap = _snap()
        state = hub.apply_to_snapshot(snap, now=now + 5)
        self.assertEqual(state, "attention")
        packet = snap.packet(state or "idle")
        self.assertEqual(packet["agent"], "PI")
        self.assertEqual(packet["agent_id"], "pi")
        self.assertEqual(packet["agent_count"], 5)
        self.assertEqual(packet["state"], "attention")
        self.assertEqual(packet["provider"], "openai")
        self.assertEqual(packet["provider_count"], 3)

    def test_session_end_removes_agent_from_carousel(self) -> None:
        hub = AgentHub(presence_window=600)
        now = 1_700_000_100.0
        hub.ingest_hook(
            {"client_kind": "dsh", "hook_event_name": "UserPromptSubmit"},
            now=now,
        )
        hub.ingest_hook(
            {"client_kind": "pi", "hook_event_name": "UserPromptSubmit"},
            now=now,
        )
        self.assertIn("dsh", hub.agents)
        hub.ingest_hook(
            {"client_kind": "dsh", "hook_event_name": "SessionEnd"},
            now=now + 1,
        )
        self.assertNotIn("dsh", hub.agents)
        self.assertNotIn("dsh", hub.visible_ids(now=now + 1))
        self.assertIn("pi", hub.visible_ids(now=now + 1))

    def test_quiet_timeout_prunes_agent_entirely(self) -> None:
        hub = AgentHub(presence_window=30)
        now = 1_700_000_200.0
        hub.ingest_hook(
            {"client_kind": "hermes", "hook_event_name": "PreToolUse"},
            now=now,
        )
        self.assertEqual(hub.visible_ids(now=now + 1), ["hermes"])
        hub.tick(now=now + 40)
        self.assertEqual(hub.visible_ids(now=now + 40), [])
        self.assertNotIn("hermes", hub.agents)

    def test_idle_codex_fallback_does_not_pin_forever(self) -> None:
        hub = AgentHub(presence_window=30)
        now = 1_700_000_300.0
        hub.note_codex_fallback("busy", now=now)
        self.assertIn("codex", hub.agents)
        hub.note_codex_fallback("idle", now=now + 1)  # must not refresh presence
        hub.prune(now=now + 40)
        self.assertNotIn("codex", hub.agents)

    def test_agent_next_prev_updates_packet_index(self) -> None:
        hub = AgentHub(presence_window=600)
        now = 1_700_000_200.0
        for kind, event in (
            ("codex", "UserPromptSubmit"),
            ("pi", "UserPromptSubmit"),
            ("hermes", "UserPromptSubmit"),
        ):
            hub.ingest_hook(
                {"client_kind": kind, "source": "claude" if kind != "codex" else "codex", "hook_event_name": event},
                now=now,
            )
        hub.current_id = "codex"
        hub.advance("next", now=now + 1)
        self.assertEqual(hub.current_id, "pi")
        snap = _snap()
        hub.apply_to_snapshot(snap, now=now + 1)
        packet = snap.packet(hub.agents["pi"].state)
        self.assertEqual(packet["agent_id"], "pi")
        self.assertEqual(packet["agent_index"], 1)
        self.assertEqual(packet["agent_count"], 3)
        hub.advance("prev", now=now + 2)
        self.assertEqual(hub.current_id, "codex")

    def test_auto_rotate_prefers_busy_and_respects_manual_grace(self) -> None:
        hub = AgentHub(rotate_idle_sec=5, rotate_busy_sec=20, manual_grace_sec=30, presence_window=600)
        now = 1_700_000_300.0
        hub.ingest_hook({"client_kind": "codex", "source": "codex", "hook_event_name": "Stop"}, now=now)
        hub.ingest_hook({"client_kind": "pi", "hook_event_name": "UserPromptSubmit"}, now=now)
        hub.current_id = "codex"
        hub._rotate_started_at = now
        # Idle dwell elapsed → rotate toward busy Pi.
        selected = hub.maybe_auto_rotate(now=now + 6)
        self.assertIsNotNone(selected)
        assert selected is not None
        self.assertEqual(selected.agent_id, "pi")

        hub.advance("next", now=now + 7)  # starts grace
        stayed = hub.maybe_auto_rotate(now=now + 10)
        assert stayed is not None
        self.assertEqual(stayed.agent_id, hub.current_id)


if __name__ == "__main__":
    unittest.main()
