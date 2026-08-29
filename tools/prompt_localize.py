#!/usr/bin/env python3
"""Localize Stick approval prompt text (ZH→EN) before BLE.

Pipeline: ASCII passthrough → MyMemory → Argos zh→en → pinyin / placeholder.
See docs/specs/stick-human-approval.md / issue #11.
"""

from __future__ import annotations

import concurrent.futures
import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

PLACEHOLDER = "Chinese text (see PC)"

# Process-local default cache shared across prepare_prompt_fields calls.
_DEFAULT_CACHE: dict[str, str] = {}


def is_ascii_only(text: str) -> bool:
    return all(ord(c) < 128 for c in text)


def fit_chars(value: Any, limit: int, fallback: str = "") -> str:
    """Truncate by Unicode characters; stay within `limit` including `...`."""
    text = str(value if value is not None else fallback).replace("\n", " ").strip()
    if not text:
        text = fallback
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    return text[: limit - 3] + "..."


def _mymemory_translate(
    text: str,
    *,
    timeout_s: float,
    email: str | None = None,
) -> str | None:
    """Free MyMemory HTTP API. Returns None on any failure."""
    q = urllib.parse.urlencode(
        {
            "q": text,
            "langpair": "zh|en",
            **({"de": email} if email else {}),
        }
    )
    url = f"https://api.mymemory.translated.net/get?{q}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "codex-buddy-bridge/1.0"})
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None
    try:
        translated = (payload.get("responseData") or {}).get("translatedText")
    except AttributeError:
        return None
    if not isinstance(translated, str):
        return None
    out = translated.strip()
    if not out or out.upper() == "NO QUERY SPECIFIED":
        return None
    # MyMemory sometimes echoes the source on failure / quota.
    if out == text:
        return None
    return out


def _argos_translate(text: str, *, timeout_s: float = 3.0) -> str | None:
    """Local Argos zh→en. Optional dependency; None if missing/fails/times out."""
    try:
        from argostranslate import translate as argos_translate
    except ImportError:
        return None

    def _run() -> str | None:
        try:
            out = argos_translate.translate(text, "zh", "en")
        except Exception:
            return None
        if not isinstance(out, str):
            return None
        out = out.strip()
        if not out or out == text:
            return None
        return out

    # Argos cold start can take seconds; never block the BLE event loop forever.
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(_run)
            return fut.result(timeout=max(0.5, float(timeout_s)))
    except (concurrent.futures.TimeoutError, Exception):
        return None


def _pinyin_fallback(text: str) -> str | None:
    try:
        from pypinyin import lazy_pinyin
    except ImportError:
        return None
    try:
        parts = lazy_pinyin(text)
    except Exception:
        return None
    if not parts:
        return None
    return " ".join(parts)


def translate_for_stick(
    text: str,
    *,
    mode: str = "auto",
    timeout_ms: int = 600,
    mymemory_email: str | None = None,
    cache: dict[str, str] | None = None,
) -> str:
    """Return Stick-safe English (or ASCII) for an approval hint/tool string."""
    cleaned = str(text or "").replace("\n", " ").strip()
    if not cleaned:
        return cleaned
    if is_ascii_only(cleaned):
        return cleaned

    mode_norm = (mode or "auto").strip().lower()
    if mode_norm in {"off", "none", "false", "0"}:
        # Stick has no CJK font — do not forward raw glyphs (would render blank).
        return PLACEHOLDER

    store = _DEFAULT_CACHE if cache is None else cache
    if cleaned in store:
        return store[cleaned]

    timeout_s = max(0.1, float(timeout_ms) / 1000.0)
    result: str | None = None
    result = _mymemory_translate(cleaned, timeout_s=timeout_s, email=mymemory_email)
    if result is None:
        # Allow Argos a bit longer than MyMemory; still bounded.
        result = _argos_translate(cleaned, timeout_s=max(3.0, timeout_s * 4))
    if result is None:
        result = _pinyin_fallback(cleaned)
    if result is None:
        result = PLACEHOLDER

    # Prefer ASCII-ish output for the default Stick font.
    if not is_ascii_only(result):
        ascii_only = "".join(c if ord(c) < 128 else " " for c in result)
        ascii_only = " ".join(ascii_only.split())
        result = ascii_only or PLACEHOLDER

    store[cleaned] = result
    return result


def prepare_prompt_fields(
    tool: str,
    hint: str,
    *,
    mode: str = "auto",
    timeout_ms: int = 600,
    mymemory_email: str | None = None,
    tool_limit: int = 19,
    hint_limit: int = 63,
    cache: dict[str, str] | None = None,
    translate: Callable[..., str] | None = None,
) -> tuple[str, str]:
    """Localize then fit tool/hint for BLE → Stick buffers."""
    fn = translate or (
        lambda s, **kw: translate_for_stick(
            s,
            mode=mode,
            timeout_ms=timeout_ms,
            mymemory_email=mymemory_email,
            cache=cache,
        )
    )
    tool_out = fn(str(tool or "APPROVAL"))
    hint_out = fn(str(hint or "Codex approval"))
    return (
        fit_chars(tool_out, tool_limit, "APPROVAL"),
        fit_chars(hint_out, hint_limit, "Codex approval"),
    )
