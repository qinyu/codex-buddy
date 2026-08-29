#!/usr/bin/env python3
"""Seam tests for Stick approval prompt localization (issue #11)."""

from __future__ import annotations

import unittest
from unittest import mock

from prompt_localize import (
    PLACEHOLDER,
    fit_chars,
    is_ascii_only,
    prepare_prompt_fields,
    translate_for_stick,
)


class FitCharsTests(unittest.TestCase):
    def test_short_unchanged(self) -> None:
        self.assertEqual(fit_chars("hello", 10), "hello")

    def test_truncates_by_unicode_chars(self) -> None:
        # CJK counts as one char each; result stays within limit.
        src = "一二三四五六七八九十"
        out = fit_chars(src, 6)
        self.assertEqual(len(out), 6)
        self.assertTrue(out.endswith("..."))
        self.assertEqual(out, "一二三...")

    def test_ascii_long(self) -> None:
        out = fit_chars("abcdefghijklmnop", 10)
        self.assertEqual(out, "abcdefg...")
        self.assertEqual(len(out), 10)


class AsciiPassthroughTests(unittest.TestCase):
    def test_ascii_detection(self) -> None:
        self.assertTrue(is_ascii_only("git push origin HEAD"))
        self.assertFalse(is_ascii_only("请批准删除文件"))

    def test_ascii_skips_translators(self) -> None:
        with mock.patch("prompt_localize._mymemory_translate") as mm:
            with mock.patch("prompt_localize._argos_translate") as ag:
                out = translate_for_stick("ls -la /tmp", mode="auto")
        self.assertEqual(out, "ls -la /tmp")
        mm.assert_not_called()
        ag.assert_not_called()


class PipelineTests(unittest.TestCase):
    def test_mymemory_primary(self) -> None:
        cache: dict[str, str] = {}
        with mock.patch(
            "prompt_localize._mymemory_translate", return_value="Please delete the file"
        ) as mm:
            with mock.patch("prompt_localize._argos_translate") as ag:
                out = translate_for_stick(
                    "请删除文件", mode="auto", timeout_ms=500, cache=cache
                )
        self.assertEqual(out, "Please delete the file")
        mm.assert_called_once()
        ag.assert_not_called()

    def test_argos_fallback(self) -> None:
        cache: dict[str, str] = {}
        with mock.patch("prompt_localize._mymemory_translate", return_value=None):
            with mock.patch(
                "prompt_localize._argos_translate", return_value="Please delete the file"
            ) as ag:
                out = translate_for_stick("请删除文件", mode="auto", cache=cache)
        self.assertEqual(out, "Please delete the file")
        ag.assert_called_once()

    def test_placeholder_last_resort(self) -> None:
        cache: dict[str, str] = {}
        with mock.patch("prompt_localize._mymemory_translate", return_value=None):
            with mock.patch("prompt_localize._argos_translate", return_value=None):
                with mock.patch("prompt_localize._pinyin_fallback", return_value=None):
                    out = translate_for_stick("请删除文件", mode="auto", cache=cache)
        self.assertEqual(out, PLACEHOLDER)

    def test_cache_avoids_repeat(self) -> None:
        cache: dict[str, str] = {}
        with mock.patch(
            "prompt_localize._mymemory_translate", return_value="Delete file"
        ) as mm:
            a = translate_for_stick("请删除", mode="auto", cache=cache)
            b = translate_for_stick("请删除", mode="auto", cache=cache)
        self.assertEqual(a, b)
        self.assertEqual(mm.call_count, 1)

    def test_off_mode_uses_placeholder_for_non_ascii(self) -> None:
        with mock.patch("prompt_localize._mymemory_translate") as mm:
            out = translate_for_stick("请批准", mode="off", cache={})
        self.assertEqual(out, PLACEHOLDER)
        mm.assert_not_called()


class PrepareFieldsTests(unittest.TestCase):
    def test_prepare_fits_limits(self) -> None:
        tool, hint = prepare_prompt_fields(
            "BASH",
            "请" * 80,
            mode="auto",
            tool_limit=19,
            hint_limit=63,
            translate=lambda s, **_: "EN " + ("x" * 100),
        )
        self.assertLessEqual(len(tool), 19)
        self.assertLessEqual(len(hint), 63)
        self.assertTrue(hint.endswith("..."))

    def test_prepare_ascii_passthrough(self) -> None:
        tool, hint = prepare_prompt_fields(
            "BASH",
            "git status",
            mode="auto",
            hint_limit=43,
        )
        self.assertEqual(hint, "git status")


if __name__ == "__main__":
    unittest.main()
