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
};

/** Stream SSE chat; onEvent per parsed event. */
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
    body: JSON.stringify({ message, mode, history, platform }),
  });
  if (!r.ok || !r.body) throw new Error(`chat ${r.status}`);
  const reader = r.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
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
        onEvent(JSON.parse(line.slice(5)));
      } catch {
        /* skip malformed */
      }
    }
  }
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
