"""Codex Buddy Stick — Hermes Agent Hub presence (no Ping Island dependency)."""

from __future__ import annotations

import json
import os
import subprocess
import threading

# Absolute path to vibe-buddy filled by install_presence.py.
NOTIFY = [
    "__VIBE_BUDDY__",
    "post",
    "--client-kind",
    "hermes",
    "--client-name",
    "Hermes",
]

_SESSION_STATE: dict = {}


def _stable_text(value):
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return None


def _session_id(*candidates, **kwargs):
    for candidate in candidates:
        text = _stable_text(candidate)
        if text:
            return text if text.startswith("hermes-") else f"hermes-{text}"
    for key in ("session_id", "task_id", "conversation_id"):
        text = _stable_text(kwargs.get(key))
        if text:
            return text if text.startswith("hermes-") else f"hermes-{text}"
    return None


def _cwd(kwargs):
    for key in ("cwd", "working_directory", "directory"):
        text = _stable_text(kwargs.get(key))
        if text:
            return text
    try:
        return os.getcwd()
    except OSError:
        return None


def _emit(payload: dict) -> None:
    def _run() -> None:
        try:
            proc = subprocess.Popen(
                NOTIFY,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
                start_new_session=True,
            )
            if proc.stdin:
                proc.stdin.write(json.dumps(payload, ensure_ascii=False))
                proc.stdin.close()
        except Exception:
            return

    threading.Thread(target=_run, daemon=True).start()


def _state(session_id: str) -> dict:
    if session_id not in _SESSION_STATE:
        _SESSION_STATE[session_id] = {"did_start": False, "last_assistant": None}
    return _SESSION_STATE[session_id]


def _on_session_start(session_id=None, **kwargs):
    sid = _session_id(session_id, **kwargs)
    if not sid:
        return
    st = _state(sid)
    if st.get("did_start"):
        return
    _emit({"session_id": sid, "cwd": _cwd(kwargs), "hook_event_name": "SessionStart"})
    st["did_start"] = True


def _on_pre_llm_call(session_id=None, **kwargs):
    sid = _session_id(session_id, kwargs.get("task_id"), **kwargs)
    if not sid:
        return
    _on_session_start(session_id=sid, **kwargs)
    _emit({"session_id": sid, "cwd": _cwd(kwargs), "hook_event_name": "UserPromptSubmit"})


def _on_pre_tool_call(session_id=None, tool_name=None, **kwargs):
    sid = _session_id(session_id, kwargs.get("task_id"), **kwargs)
    if not sid:
        return
    _emit(
        {
            "session_id": sid,
            "cwd": _cwd(kwargs),
            "hook_event_name": "PreToolUse",
            "tool_name": _stable_text(tool_name) or "Tool",
        }
    )


def _on_post_tool_call(session_id=None, tool_name=None, **kwargs):
    sid = _session_id(session_id, kwargs.get("task_id"), **kwargs)
    if not sid:
        return
    _emit(
        {
            "session_id": sid,
            "cwd": _cwd(kwargs),
            "hook_event_name": "PostToolUse",
            "tool_name": _stable_text(tool_name) or "Tool",
        }
    )


def _on_post_llm_call(session_id=None, assistant_response=None, **kwargs):
    sid = _session_id(session_id, kwargs.get("task_id"), **kwargs)
    if not sid:
        return
    reply = _stable_text(assistant_response)
    if reply:
        _state(sid)["last_assistant"] = reply
    _emit({"session_id": sid, "cwd": _cwd(kwargs), "hook_event_name": "Notification"})


def _on_session_end(session_id=None, **kwargs):
    sid = _session_id(session_id, kwargs.get("task_id"), **kwargs)
    if not sid:
        return
    _emit({"session_id": sid, "cwd": _cwd(kwargs), "hook_event_name": "Stop"})


def _on_session_finalize(session_id=None, **kwargs):
    sid = _session_id(session_id, kwargs.get("task_id"), **kwargs)
    if not sid:
        return
    _emit({"session_id": sid, "cwd": _cwd(kwargs), "hook_event_name": "SessionEnd"})
    _SESSION_STATE.pop(sid, None)


def _on_session_reset(session_id=None, **kwargs):
    _on_session_start(session_id=session_id, **kwargs)


def register(ctx):
    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    ctx.register_hook("pre_tool_call", _on_pre_tool_call)
    ctx.register_hook("post_tool_call", _on_post_tool_call)
    ctx.register_hook("post_llm_call", _on_post_llm_call)
    ctx.register_hook("on_session_end", _on_session_end)
    ctx.register_hook("on_session_finalize", _on_session_finalize)
    ctx.register_hook("on_session_reset", _on_session_reset)
