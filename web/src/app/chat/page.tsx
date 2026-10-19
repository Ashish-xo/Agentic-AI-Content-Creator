"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api, chatStream, type Persona } from "@/lib/api";
import { getStoredNiche } from "@/lib/niche";

type UsedContext = { trends: { title: string; platform: string; heat: number }[]; playbooks: { topic: string; platform: string }[]; hooks: { hook: string; archetype: string }[] };
type Msg = { role: "user" | "assistant"; content: string; mode?: string | null; streaming?: boolean; context?: UsedContext };

const MODES = [
  { id: "auto", label: "✨ Auto" },
  { id: "research", label: "🔍 Research" },
  { id: "creation", label: "✍️ Creation" },
  { id: "optimization", label: "📈 Optimization" },
];

const PLATFORMS = [
  { id: "", label: "Both" },
  { id: "youtube", label: "▶ YouTube" },
  { id: "instagram", label: "📸 Instagram" },
];

export default function ChatPage() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState<string>("auto");
  const [platform, setPlatform] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [persona, setPersona] = useState<Persona | null>(null);
  const [chips, setChips] = useState<string[]>([]);
  const [niche, setNiche] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const pendingField = useRef<string | null>(null);

  // live-follow the niche chip (AppShell dispatches on change)
  useEffect(() => {
    setNiche(getStoredNiche());
    const onNiche = (e: Event) => setNiche((e as CustomEvent<string>).detail);
    window.addEventListener("cc-niche-changed", onNiche);
    return () => window.removeEventListener("cc-niche-changed", onNiche);
  }, []);

  const loadPersona = useCallback(async () => {
    const p = await api.get<Persona>("/persona");
    setPersona(p);
    pendingField.current = p.pending_field;
    if (!p.completed && p.pending_field) {
      setChips(p.quick_replies[p.pending_field] || []);
    } else {
      setChips([]);
    }
    return p;
  }, []);

  useEffect(() => {
    (async () => {
      const p = await loadPersona();
      const hist = await api.get<{ role: string; content: string; mode: string | null }[]>(
        "/chat/history?limit=30"
      ).catch(() => []);
      if (hist.length) {
        setMsgs(hist.map((h) => ({ role: h.role as Msg["role"], content: h.content, mode: h.mode })));
      } else if (!p.completed) {
        setMsgs([{ role: "assistant", content: "Hi! Two minutes of setup so everything I write fits you. " + (p.pending_field ? "What do you make content about?" : "") }]);
      }
    })();
  }, [loadPersona]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs, busy]);

  async function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || busy) return;
    setInput("");
    setBusy(true);
    setMsgs((m) => [...m, { role: "user", content: trimmed }]);
    const history = msgs.slice(-8).map(({ role, content }) => ({ role, content }));
    let acc = "";
    let ctx: UsedContext = { trends: [], playbooks: [], hooks: [] };
    try {
      await chatStream(trimmed, mode === "auto" ? null : mode, history, (e) => {
        if (e.type === "delta") {
          acc += e.text as string;
          setMsgs((m) => {
            const copy = [...m];
            const last = copy[copy.length - 1];
            if (last?.role === "assistant" && last.streaming) {
              copy[copy.length - 1] = { ...last, content: acc };
            } else {
              copy.push({ role: "assistant", content: acc, mode: (e.mode as string) || mode, streaming: true, context: ctx });
            }
            return copy;
          });
        } else if (e.type === "meta") {
          // mode/platform resolved server-side; capture retrieved RAG context
          ctx = {
            trends: ((e.trends_used as UsedContext["trends"]) || []).slice(0, 5),
            playbooks: (e.playbooks_used as UsedContext["playbooks"]) || [],
            hooks: (e.hooks_used as UsedContext["hooks"]) || [],
          };
        } else if (e.type === "onboarding") {
          loadPersona();
        } else if (e.type === "filter") {
          const vs = (e.violations as { phrase: string }[]) || [];
          if (vs.length) {
            acc += `\n\n> ⚠ **Saturation filter:** flagged ${vs.map((v) => `“${v.phrase}”`).join(", ")} in this reply.`;
            setMsgs((m) => {
              const copy = [...m];
              const last = copy[copy.length - 1];
              if (last?.role === "assistant") copy[copy.length - 1] = { ...last, content: acc };
              return copy;
            });
          }
        } else if (e.type === "truncated") {
          acc += `\n\n_✂️ Hit the ${e.budget}-token output cap — say "continue" for the rest._`;
        } else if (e.type === "error") {
          acc += `\n\n_(error: ${e.detail})_`;
        }
      }, platform || null, niche);
    } catch (err) {
      const e = err as Error;
      if (e.name === "RateLimitError") {
        const [, retry, limit] = e.message.split(":");
        const secs = Math.ceil(Number(retry) || 60);
        const limitNote = Number(limit) ? ` (free limit: ${limit}/min — add your own key in Settings for 30/min)` : "";
        setMsgs((m) => [...m, {
          role: "assistant",
          content: `🚦 **Slow down** — you're sending messages faster than the free engine allows. Try again in **${secs}s**${limitNote}.`,
        }]);
      } else {
        setMsgs((m) => [...m, { role: "assistant", content: `Something broke: ${String(err)}` }]);
      }
    } finally {
      setMsgs((m) => m.map((x) => ({ ...x, streaming: false } as Msg)));
      setBusy(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      {/* toolbar: segmented platform control + scrollable mode chips */}
      <div className="border-b border-edge bg-panel px-3 py-2">
        <div role="tablist" aria-label="Platform"
          className="flex rounded-xl border border-edge bg-bg p-1">
          {PLATFORMS.map((p) => (
            <button key={p.id || "both"} role="tab" aria-selected={platform === p.id}
              onClick={() => setPlatform(p.id)}
              title="Which platform's trend data and psychology to write for"
              className={`tap flex-1 rounded-lg text-sm font-medium transition-colors ${
                platform === p.id ? "bg-accent2 text-black" : "text-slate-400"}`}>
              {p.label}
            </button>
          ))}
        </div>
        <div className="scroll-ios mt-2 flex gap-2 overflow-x-auto pb-1">
          {MODES.map((m) => (
            <button key={m.id} onClick={() => setMode(m.id)}
              className={`tap shrink-0 rounded-full px-4 text-sm ${
                mode === m.id ? "bg-accent text-black font-semibold" : "border border-edge text-slate-400"}`}>
              {m.label}
            </button>
          ))}
          <span className="tap shrink-0 pl-2 text-[11px] text-slate-500">
            {persona?.completed ? `for: ${persona.niche}` : "setup…"}
          </span>
        </div>
      </div>

      {/* messages */}
      <div className="scroll-ios flex-1 overflow-y-auto px-3 py-4 md:px-4 md:py-5">
        <div className="mx-auto max-w-3xl space-y-4">
          {msgs.map((m, i) => (
            <div key={i} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
              <div
                className={`max-w-[92%] rounded-2xl px-3.5 py-2.5 text-[15px] md:max-w-[85%] ${
                  m.role === "user"
                    ? "bg-accent/15 border border-accent/25 text-slate-100 whitespace-pre-wrap"
                    : "bg-panel border border-edge"
                }`}
              >
                {m.role === "assistant" ? (
                  <div className="md-body">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content || "…"}</ReactMarkdown>
                  </div>
                ) : (
                  m.content
                )}
                {m.role === "assistant" && m.context && (m.context.playbooks.length > 0 || m.context.trends.length > 0 || m.context.hooks?.length > 0) && !m.streaming && (
                  <details className="mt-2 border-t border-edge pt-1.5 text-[11px] text-slate-500">
                    <summary className="cursor-pointer select-none list-none">
                      📚 {m.context.playbooks.length} playbook{m.context.playbooks.length === 1 ? "" : "s"}
                      {m.context.hooks?.length ? ` · ${m.context.hooks.length} hook pattern${m.context.hooks.length === 1 ? "" : "s"}` : ""}
                      {m.context.trends.length ? ` · ${m.context.trends.length} trend${m.context.trends.length === 1 ? "" : "s"} used` : " used"}
                    </summary>
                    <ul className="mt-1 space-y-0.5">
                      {m.context.playbooks.map((p, j) => (
                        <li key={`p${j}`}>▸ <span className="text-accent2">{p.platform}</span> — {p.topic}</li>
                      ))}
                      {m.context.hooks?.map((h, j) => (
                        <li key={`h${j}`}>🪝 <span className="text-accent2">{h.archetype}</span> — “{h.hook}”</li>
                      ))}
                      {m.context.trends.map((t, j) => (
                        <li key={`t${j}`}>▲ <span className="text-accent2">{t.platform}</span> — {t.title} <span className="text-slate-600">(heat {t.heat})</span></li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* quick-reply chips (onboarding) */}
      {chips.length > 0 && !busy && (
        <div className="px-3 pb-2 md:px-4">
          <div className="mx-auto flex max-w-3xl flex-wrap gap-2">
            {chips.map((c) => (
              <button
                key={c}
                onClick={() => send(c)}
                className="tap rounded-full border border-accent2/40 px-4 text-sm text-accent2 active:bg-accent2/10"
              >
                {c}
              </button>
            ))}
            <button
              onClick={() => send("skip")}
              className="tap rounded-full border border-edge px-4 text-sm text-slate-500 active:text-white"
            >
              skip
            </button>
          </div>
        </div>
      )}

      {/* composer (main's pb already clears the bottom nav + safe area) */}
      <div className="border-t border-edge bg-panel px-3 py-2 md:px-4 md:py-3">
        <form
          className="mx-auto flex max-w-3xl gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={persona?.completed ? "Ask anything — or pick a mode above" : "Answer the question above, or type skip"}
            className="min-h-[48px] flex-1 rounded-xl border border-edge bg-bg px-4 text-[15px] outline-none placeholder:text-slate-600 focus:border-accent"
            disabled={busy}
          />
          <button
            type="submit"
            disabled={busy || !input.trim()}
            className="tap rounded-xl bg-accent px-5 font-semibold text-black disabled:opacity-40"
          >
            {busy ? "…" : "Send"}
          </button>
        </form>
      </div>
    </div>
  );
}
