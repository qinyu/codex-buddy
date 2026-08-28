// Codex Buddy Stick — Agent Hub presence (no Ping Island dependency).
// NOTIFY path placeholder filled by install_presence.py.
import { spawn } from "node:child_process";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const NOTIFY = [
  "python3",
  "__CODEX_BUDDY_NOTIFY__",
  "--client-kind",
  "pi",
  "--client-name",
  "Pi",
];

function send(payload: Record<string, unknown>): void {
  try {
    const child = spawn(NOTIFY[0], NOTIFY.slice(1), {
      stdio: ["pipe", "ignore", "ignore"],
      detached: true,
    });
    child.unref();
    child.stdin?.end(JSON.stringify(payload));
  } catch {
    // fail open
  }
}

function base(sessionId: string, cwd: string | undefined, extra: Record<string, unknown>) {
  return {
    session_id: `pi-${sessionId}`,
    cwd: cwd ?? undefined,
    ...extra,
  };
}

export default function (pi: ExtensionAPI): void {
  pi.on("session_start", async (_event, ctx) => {
    const sessionId = ctx.sessionManager.getSessionId();
    send(base(sessionId, ctx.cwd, { hook_event_name: "SessionStart" }));
  });

  pi.on("session_shutdown", async (_event, ctx) => {
    const sessionId = ctx.sessionManager.getSessionId();
    send(base(sessionId, ctx.cwd, { hook_event_name: "SessionEnd" }));
  });

  pi.on("before_agent_start", async (event, ctx) => {
    const sessionId = ctx.sessionManager.getSessionId();
    send(
      base(sessionId, ctx.cwd, {
        hook_event_name: "UserPromptSubmit",
        prompt: event.prompt ?? "",
      }),
    );
  });

  pi.on("tool_call", async (event, ctx) => {
    const sessionId = ctx.sessionManager.getSessionId();
    send(
      base(sessionId, ctx.cwd, {
        hook_event_name: "PreToolUse",
        tool_name: event.toolName,
        _pi_tool_call_id: event.toolCallId,
      }),
    );
  });

  pi.on("tool_result", async (event, ctx) => {
    const sessionId = ctx.sessionManager.getSessionId();
    send(
      base(sessionId, ctx.cwd, {
        hook_event_name: "PostToolUse",
        tool_name: event.toolName,
        is_error: event.isError,
        _pi_tool_call_id: event.toolCallId,
      }),
    );
  });

  pi.on("agent_end", async (_event, ctx) => {
    const sessionId = ctx.sessionManager.getSessionId();
    send(base(sessionId, ctx.cwd, { hook_event_name: "Stop" }));
  });
}
