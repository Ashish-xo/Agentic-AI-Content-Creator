"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api, chatStream, type Persona } from "@/lib/api";

type Msg = { role: "user" | "assistant"; content: string; mode?: string | null; streaming?: boolean };

const MODES = [
  { id: "auto", label: "✨ Auto" },
  { id: "research", label: "🔍 Research" },
  { id: "creation", label: "✍️ Creation" },
  { id: "optimization", label: "📈 Optimization" },
];

export default function ChatPage() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState<string>("auto");
  const [busy, setBusy] = useState(false);
  const [persona, setPersona] = useState<Persona | null>(null);
  const [chips, setChips] = useState<string[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const pendingField = useRef<string | null>(null);

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
              copy.push({ role: "assistant", content: acc, mode: (e.mode as string) || mode, streaming: true });
            }
            return copy;
          });
        } else if (e.type === "meta") {
          // mode/platform resolved server-side
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
        } else if (e.type === "error") {
          acc += `\n\n_(error: ${e.detail})_`;
        }
      });
    } catch (err) {
      setMsgs((m) => [...m, { role: "assistant", content: `Something broke: ${String(err)}` }]);
    } finally {
      setMsgs((m) => m.map((x) => ({ ...x, streaming: false } as Msg)));
      setBusy(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      {/* slim toolbar */}
      <div className="flex items-center gap-2 border-b border-edge bg-panel px-4 py-2">
        {MODES.map((m) => (
          <button
            key={m.id}
            onClick={() => setMode(m.id)}
            className={`rounded-full px-3 py-1 text-xs transition-colors ${
              mode === m.id ? "bg-accent text-black font-semibold" : "border border-edge text-slate-400 hover:text-white"
            }`}
          >
            {m.label}
          </button>
        ))}
        <div className="ml-auto text-xs text-slate-500">
          {persona?.completed ? `for: ${persona.niche}` : "setup in progress"}
        </div>
      </div>

      {/* messages */}
      <div className="flex-1 overflow-y-auto px-4 py-5">
        <div className="mx-auto max-w-3xl space-y-4">
          {msgs.map((m, i) => (
            <div key={i} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-[15px] ${
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
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* quick-reply chips (onboarding) */}
      {chips.length > 0 && !busy && (
        <div className="px-4 pb-2">
          <div className="mx-auto flex max-w-3xl flex-wrap gap-2">
            {chips.map((c) => (
              <button
                key={c}
                onClick={() => send(c)}
                className="rounded-full border border-accent2/40 px-3 py-1 text-xs text-accent2 hover:bg-accent2/10"
              >
                {c}
              </button>
            ))}
            <button
              onClick={() => send("skip")}
              className="rounded-full border border-edge px-3 py-1 text-xs text-slate-500 hover:text-white"
            >
              skip
            </button>
          </div>
        </div>
      )}

      {/* composer */}
      <div className="border-t border-edge bg-panel px-4 py-3">
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
            className="flex-1 rounded-xl border border-edge bg-bg px-4 py-3 text-[15px] outline-none placeholder:text-slate-600 focus:border-accent"
            disabled={busy}
          />
          <button
            type="submit"
            disabled={busy || !input.trim()}
            className="rounded-xl bg-accent px-5 py-3 font-semibold text-black disabled:opacity-40"
          >
            {busy ? "…" : "Send"}
          </button>
        </form>
      </div>
    </div>
  );
}
