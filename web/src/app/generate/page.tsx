"use client";

import { useEffect, useState } from "react";
import { api, type LibraryItem } from "@/lib/api";

type Tab = "hooks" | "script" | "critique";

export default function GeneratePage() {
  const [tab, setTab] = useState<Tab>("hooks");
  const [topic, setTopic] = useState("");
  const [platform, setPlatform] = useState("youtube");
  const [out, setOut] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [lib, setLib] = useState<LibraryItem[]>([]);

  useEffect(() => {
    api.get<LibraryItem[]>("/library?limit=12").then(setLib).catch(() => {});
  }, [out]);

  async function run() {
    if (!topic.trim()) return;
    setBusy(true); setErr(""); setOut(null);
    try {
      if (tab === "hooks") {
        setOut(await api.post("/generate/hooks", { topic, platform, count: 3 }));
      } else if (tab === "script") {
        setOut(await api.post("/generate/script", { topic, platform, seconds: 30 }));
      } else {
        setOut(await api.post("/generate/critique", { draft: topic, platform }));
      }
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  const hooks = (out as { hooks?: { hook: string; archetype: string; rationale: string; thumbnail_text?: string }[] } | null)?.hooks;
  const script = out as { title?: string; blocks?: { time: string; visual: string; audio: string }[]; cta?: string } | null;
  const crit = out as { score_before?: number; score_after?: number; issues?: { quote: string; problem: string; fix: string }[]; rewritten?: string } | null;

  return (
    <div className="p-6 max-w-4xl">
      <h1 className="mb-4 text-2xl font-bold">Generate</h1>
      <div className="mb-4 flex gap-2">
        {(["hooks", "script", "critique"] as Tab[]).map((t) => (
          <button key={t} onClick={() => { setTab(t); setOut(null); }}
            className={`rounded-full px-4 py-1.5 text-sm capitalize ${
              tab === t ? "bg-accent text-black font-semibold" : "border border-edge text-slate-400"}`}>
            {t === "critique" ? "critique a draft" : t}
          </button>
        ))}
        <select value={platform} onChange={(e) => setPlatform(e.target.value)}
          className="ml-auto rounded-lg border border-edge bg-panel px-3 py-1.5 text-sm">
          <option value="youtube">YouTube</option>
          <option value="instagram">Instagram</option>
        </select>
      </div>

      <div className="mb-4 flex gap-2">
        <input value={topic} onChange={(e) => setTopic(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
          placeholder={tab === "critique" ? "Paste your draft caption/script…" : "Topic, e.g. AI tools for students"}
          className="flex-1 rounded-xl border border-edge bg-panel px-4 py-2.5 outline-none focus:border-accent" />
        <button onClick={run} disabled={busy}
          className="rounded-xl bg-accent px-5 py-2.5 font-semibold text-black disabled:opacity-40">
          {busy ? "…" : "Go"}
        </button>
      </div>
      {err && <p className="mb-3 text-sm text-red-400">{err}</p>}

      {hooks && (
        <div className="space-y-3">
          {hooks.map((h, i) => (
            <div key={i} className="rounded-xl border border-edge bg-panel p-4">
              <div className="text-[11px] uppercase tracking-wide text-accent2">{h.archetype}{h.thumbnail_text ? ` · thumb: “${h.thumbnail_text}”` : ""}</div>
              <div className="mt-1 font-medium text-white">“{h.hook}”</div>
              <div className="mt-1 text-sm text-slate-500">{h.rationale}</div>
            </div>
          ))}
        </div>
      )}
      {tab === "script" && script?.blocks && (
        <div className="rounded-xl border border-edge bg-panel p-4">
          <div className="mb-2 font-semibold text-white">{script.title}</div>
          {script.blocks.map((b, i) => (
            <div key={i} className="mb-2 grid grid-cols-[90px_1fr_1fr] gap-3 text-sm">
              <span className="font-mono text-accent">{b.time}</span>
              <span className="text-slate-300">{b.visual}</span>
              <span className="text-slate-400">{b.audio}</span>
            </div>
          ))}
          {script.cta && <div className="mt-2 text-sm text-accent2">CTA: {script.cta}</div>}
        </div>
      )}
      {tab === "critique" && crit?.issues && (
        <div className="space-y-3">
          <div className="text-sm text-slate-300">
            score <span className="font-mono text-red-400">{crit.score_before}/10</span> →{" "}
            <span className="font-mono text-green-400">{crit.score_after}/10</span>
          </div>
          {crit.issues.map((x, i) => (
            <div key={i} className="rounded-xl border border-edge bg-panel p-4 text-sm">
              <div className="text-red-400 line-through">“{x.quote}”</div>
              <div className="mt-1 text-slate-400">{x.problem}</div>
              <div className="mt-1 text-green-400">→ {x.fix}</div>
            </div>
          ))}
          {crit.rewritten && (
            <div className="rounded-xl border border-accent/30 bg-panel p-4">
              <div className="text-[11px] uppercase text-accent">rewritten</div>
              <div className="mt-1 whitespace-pre-wrap text-slate-200">{crit.rewritten}</div>
            </div>
          )}
        </div>
      )}

      <h2 className="mb-2 mt-8 text-sm font-semibold text-slate-400">Recent library</h2>
      <div className="space-y-1 text-sm">
        {lib.map((r) => (
          <div key={r.id} className="flex gap-3 rounded-lg border border-edge bg-panel px-3 py-2">
            <span className="w-16 text-xs uppercase text-accent2">{r.kind}</span>
            <span className="flex-1 truncate text-slate-300">{r.topic}</span>
            <span className="text-xs text-slate-600">{new Date(r.created_at).toLocaleDateString()}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
