"use client";

import { useEffect, useState } from "react";
import { api, type LibraryItem } from "@/lib/api";
import { CopyButton } from "@/components/copy-button";

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

  const hooks = (out as { hooks?: { hook: string; archetype: string; rationale: string; thumbnail_text?: string }[]; rejected?: { phrase: string; reason: string }[]; fewshot_examples_used?: { hook: string; archetype: string }[] } | null)?.hooks;
  const rejected = (out as { rejected?: { phrase: string; reason: string }[] } | null)?.rejected;
  const fewshotUsed = (out as { fewshot_examples_used?: { hook: string; archetype: string }[] } | null)?.fewshot_examples_used;
  const script = out as { title?: string; blocks?: { time: string; visual: string; audio: string }[]; cta?: string } | null;
  const crit = out as { score_before?: number; score_after?: number; issues?: { quote: string; problem: string; fix: string }[]; rewritten?: string } | null;

  return (
    <div className="max-w-4xl p-4 pb-24 md:p-6 md:pb-6">
      <h1 className="mb-4 text-2xl font-bold">Generate</h1>
      <div className="mb-4 flex flex-wrap gap-2">
        {(["hooks", "script", "critique"] as Tab[]).map((t) => (
          <button key={t} onClick={() => { setTab(t); setOut(null); }}
            className={`tap rounded-full px-4 text-sm capitalize ${
              tab === t ? "bg-accent font-semibold text-black" : "border border-edge text-slate-400"}`}>
            {t === "critique" ? "critique a draft" : t}
          </button>
        ))}
        <select value={platform} onChange={(e) => setPlatform(e.target.value)}
          className="ml-auto min-h-[48px] rounded-lg border border-edge bg-panel px-3 text-sm">
          <option value="youtube">YouTube</option>
          <option value="instagram">Instagram</option>
        </select>
      </div>

      <div className="mb-4 flex flex-col gap-2 sm:flex-row">
        <input value={topic} onChange={(e) => setTopic(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
          placeholder={tab === "critique" ? "Paste your draft caption/script…" : "Topic, e.g. AI tools for students"}
          className="min-h-[48px] flex-1 rounded-xl border border-edge bg-panel px-4 py-3 outline-none focus:border-accent" />
        <button onClick={run} disabled={busy}
          className="tap w-full rounded-xl bg-accent px-5 font-semibold text-black disabled:opacity-40 sm:w-auto">
          {busy ? "…" : "Go"}
        </button>
      </div>
      {err && <p className="mb-3 text-sm text-red-400">{err}</p>}

      {hooks && (
        <div className="space-y-3">
          {!!(out as { fewshot_examples_used?: { hook: string; archetype: string }[] })?.fewshot_examples_used?.length && (
            <div className="rounded-xl border border-edge bg-panel/60 p-3 text-xs text-slate-500">
              <span className="font-semibold text-slate-400">Few-shot examples analyzed (RAG):</span>{" "}
              {(out as { fewshot_examples_used: { hook: string }[] }).fewshot_examples_used
                .map((e) => `“${e.hook.slice(0, 40)}…”`).join(" ")}
            </div>
          )}
          {hooks.map((h, i) => (
            <div key={i} className="rounded-xl border border-edge bg-panel p-4">
              <div className="flex items-start justify-between gap-2">
                <div className="text-[11px] uppercase tracking-wide text-accent2">{h.archetype}{h.thumbnail_text ? ` · thumb: “${h.thumbnail_text}”` : ""}</div>
                <CopyButton text={h.hook} />
              </div>
              <div className="mt-1 font-medium text-white">“{h.hook}”</div>
              <div className="mt-1 text-sm text-slate-500">{h.rationale}</div>
            </div>
          ))}
          {!!rejected?.length && (
            <div className="rounded-xl border border-red-500/30 bg-panel p-4 text-sm">
              <div className="mb-1 text-[11px] uppercase tracking-wide text-red-400">
                Filtered out by the saturation gate ({rejected.length})
              </div>
              {rejected.map((r, i) => (
                <div key={i} className="text-slate-400">
                  <span className="text-red-400 line-through">“{r.phrase}”</span> — {r.reason}
                </div>
              ))}
            </div>
          )}
          {!!fewshotUsed?.length && (
            <div className="rounded-xl border border-edge bg-panel/60 p-4 text-sm">
              <div className="mb-1 text-[11px] uppercase tracking-wide text-accent">Few-shot examples fed to the model</div>
              {fewshotUsed.map((e, i) => (
                <div key={i} className="text-slate-500">“{e.hook}” <span className="text-accent2">· {e.archetype}</span></div>
              ))}
            </div>
          )}
        </div>
      )}
      {tab === "script" && script?.blocks && (
        <div className="rounded-xl border border-edge bg-panel p-4">
          <div className="mb-2 flex items-start justify-between gap-2">
            <div className="font-semibold text-white">{script.title}</div>
            <CopyButton
              text={[
                script.title ?? "",
                ...script.blocks.map((b) => `${b.time}\n${b.visual}\n${b.audio}`),
                script.cta ? `CTA: ${script.cta}` : "",
              ].filter(Boolean).join("\n\n")}
              label="Copy script"
            />
          </div>
          {script.blocks.map((b, i) => (
            <details key={i} open={i === 0}
              className="mb-2 rounded-lg border border-edge bg-panel/60 px-3 py-2">
              <summary className="tap cursor-pointer list-none text-sm font-medium text-accent">
                {b.time} · {b.visual.slice(0, 48)}{b.visual.length > 48 ? "…" : ""}
              </summary>
              <div className="mt-1 space-y-1 text-sm">
                <p className="text-slate-300">{b.visual}</p>
                <p className="italic text-slate-400">{b.audio}</p>
                <CopyButton text={`${b.time}\n${b.visual}\n${b.audio}`} label="Copy block" />
              </div>
            </details>
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
            <details key={i} className="mb-2 rounded-lg border border-edge bg-panel/60 px-3 py-2">
              <summary className="tap cursor-pointer list-none text-sm text-red-400 line-through">
                “{x.quote.slice(0, 56)}{x.quote.length > 56 ? "…" : ""}”
              </summary>
              <div className="mt-1 space-y-1 text-sm">
                <div className="text-red-400 line-through">“{x.quote}”</div>
                <div className="text-slate-400">{x.problem}</div>
                <div className="text-green-400">→ {x.fix}</div>
              </div>
            </details>
          ))}
          {crit.rewritten && (
            <div className="rounded-xl border border-accent/30 bg-panel p-4">
              <div className="flex items-center justify-between gap-2">
                <div className="text-[11px] uppercase text-accent">rewritten</div>
                <CopyButton text={crit.rewritten} label="Copy rewrite" />
              </div>
              <div className="mt-1 whitespace-pre-wrap text-slate-200">{crit.rewritten}</div>
            </div>
          )}
        </div>
      )}

      <h2 className="mb-2 mt-8 text-sm font-semibold text-slate-400">Recent library</h2>
      <div className="space-y-1 text-sm">
        {lib.map((r) => (
          <div key={r.id} className="flex min-h-[48px] items-center gap-3 rounded-lg border border-edge bg-panel px-3 py-2.5">
            <span className="w-16 shrink-0 text-xs uppercase text-accent2">{r.kind}</span>
            <span className="flex-1 truncate text-slate-300">{r.topic}</span>
            <span className="shrink-0 text-xs text-slate-600">{new Date(r.created_at).toLocaleDateString()}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
