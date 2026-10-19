"use client";

import { authHeadersAsync } from "./auth";

const BASE = "/api";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(await authHeadersAsync()), ...(init?.headers as Record<string, string> | undefined) },
  });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json() as Promise<T>;
}

export const api = {
  get: <T>(p: string) => req<T>(p),
  post: <T>(p: string, body?: unknown) =>
    req<T>(p, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: <T>(p: string, body?: unknown) =>
    req<T>(p, { method: "PUT", body: body ? JSON.stringify(body) : undefined }),
  del: <T>(p: string) => req<T>(p, { method: "DELETE" }),
};

/** Stream SSE chat; onEvent per parsed event.
 * Deltas are coalesced: consecutive deltas merge and render at most once per
 * animation frame (16ms) — kills per-token React re-render jank on phones.
 * Non-delta events (meta/done/error/filter) flush immediately, order preserved. */
export async function chatStream(
  message: string,
  mode: string | null,
  history: { role: string; content: string }[],
  onEvent: (e: Record<string, unknown>) => void,
  platform: string | null = null,
): Promise<void> {
  const r = await fetch(`${BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeadersAsync()) },
    body: JSON.stringify({ message, mode, history, platform, compact: true }),
  });
  if (r.status === 429) {
    // parse the structured limit payload so the UI can show a retry countdown
    let retryAfter = 60;
    let limit = 0;
    try {
      const j = await r.json();
      const d = j?.detail ?? j;
      retryAfter = Number(d?.retry_after) || 60;
      limit = Number(d?.limit) || 0;
    } catch { /* opaque body — keep defaults */ }
    const err = new Error(`rate_limited:${retryAfter}:${limit}`) as Error & { name: string };
    err.name = "RateLimitError";
    throw err;
  }
  if (!r.ok || !r.body) throw new Error(`chat ${r.status}`);
  const reader = r.body.getReader();
  const dec = new TextDecoder();
  let buf = "";

  let pending: Record<string, unknown>[] = [];
  let raf = 0;
  const flush = () => {
    raf = 0;
    const batch = pending;
    pending = [];
    for (const e of batch) onEvent(e);
  };
  const dispatch = (e: Record<string, unknown>) => {
    if (e.type === "delta") {
      const last = pending[pending.length - 1];
      if (last && last.type === "delta") {
        last.text = (last.text as string) + (e.text as string);
      } else {
        pending.push({ ...e });
      }
      if (!raf && typeof requestAnimationFrame === "function") {
        raf = requestAnimationFrame(flush);
      } else if (!raf) {
        // environments without rAF: keep ordering via microtask
        Promise.resolve().then(flush);
      }
    } else {
      if (raf) {
        cancelAnimationFrame(raf);
        raf = 0;
      }
      flush(); // emit pending deltas before the control event
      onEvent(e);
    }
  };

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop() || "";
    for (const p of parts) {
      const line = p.trim();
      if (!line.startsWith("data:")) continue;
      try {
        dispatch(JSON.parse(line.slice(5)));
      } catch {
        /* skip malformed */
      }
    }
  }
  if (raf) {
    cancelAnimationFrame(raf);
    raf = 0;
  }
  flush(); // never drop the tail
}

export type Trend = {
  platform: string; kind: string; title: string; detail: string | null;
  heat: number; source: string; captured_at: string;
};
export type Persona = {
  niche: string | null; target_audience: string | null; tone_of_voice: string | null;
  content_goal: string | null; completed: boolean; pending_field: string | null;
  quick_replies: Record<string, string[]>;
};
export type LibraryItem = {
  id: number; kind: string; platform: string | null; topic: string | null;
  payload: Record<string, unknown>; created_at: string;
};
export type Project = {
  id: number; name: string; premise: string;
  variants: Record<string, Record<string, unknown>>; updated_at: string;
};
