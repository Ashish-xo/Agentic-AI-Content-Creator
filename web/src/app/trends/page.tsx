"use client";

import { useEffect, useState } from "react";
import { api, type Trend } from "@/lib/api";

const PLATFORMS = ["all", "youtube", "instagram"];

export default function TrendsPage() {
  const [platform, setPlatform] = useState("all");
  const [rows, setRows] = useState<Trend[]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  async function load(p: string) {
    setRows(await api.get<Trend[]>(`/trends?platform=${p}&limit=30`).catch(() => []));
  }
  useEffect(() => {
    load(platform);
  }, [platform]);

  async function refresh() {
    setBusy(true);
    setMsg("");
    try {
      const r = await api.post<Record<string, number>>("/trends/refresh");
      setMsg(`youtube:${r.youtube_api ?? 0} apify:${r.apify ?? 0} serpapi:${r.serpapi ?? 0} new signals (0 = no key configured, seed floor stays)`);
      load(platform);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="p-6">
      <div className="mb-4 flex items-center gap-3">
        <h1 className="text-2xl font-bold">Trend board</h1>
        <div className="ml-auto flex gap-2">
          {PLATFORMS.map((p) => (
            <button
              key={p}
              onClick={() => setPlatform(p)}
              className={`rounded-full px-3 py-1 text-xs capitalize ${
                platform === p ? "bg-accent text-black font-semibold" : "border border-edge text-slate-400"
              }`}
            >
              {p}
            </button>
          ))}
          <button
            onClick={refresh}
            disabled={busy}
            className="rounded-full border border-accent2/40 px-3 py-1 text-xs text-accent2 hover:bg-accent2/10 disabled:opacity-40"
          >
            {busy ? "refreshing…" : "↻ refresh providers"}
          </button>
        </div>
      </div>
      {msg && <p className="mb-3 text-xs text-slate-500">{msg}</p>}
      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {rows.map((t) => (
          <div key={`${t.platform}-${t.kind}-${t.title}`} className="rounded-xl border border-edge bg-panel p-4">
            <div className="mb-1 flex items-center gap-2 text-[11px]">
              <span className={`rounded px-1.5 py-0.5 font-bold ${
                t.platform === "youtube" ? "bg-red-500/20 text-red-400"
                : t.platform === "instagram" ? "bg-pink-500/20 text-pink-400"
                : "bg-slate-500/20 text-slate-300"}`}>
                {t.platform}
              </span>
              <span className="text-slate-500">{t.kind.replace(/_/g, " ")}</span>
              <span className="ml-auto font-mono text-accent">{t.heat.toFixed(0)}</span>
            </div>
            <div className="text-sm font-medium text-slate-100">{t.title}</div>
            {t.detail && <div className="mt-1 text-xs text-slate-500">{t.detail}</div>}
            <div className="mt-2 h-1 rounded bg-edge">
              <div className="h-1 rounded bg-accent" style={{ width: `${t.heat}%` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
