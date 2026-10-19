"use client";

import { useEffect, useState } from "react";
import { api, type Trend } from "@/lib/api";

const PLATFORMS = ["all", "youtube", "instagram"];

export default function TrendsPage() {
  const [platform, setPlatform] = useState("all");
  const [rows, setRows] = useState<Trend[]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  // viral discovery state
  const [nicheQuery, setNicheQuery] = useState("");
  const [viralBusy, setViralBusy] = useState(false);
  const [viral, setViral] = useState<ViralRow[] | null>(null);
  const [viralMsg, setViralMsg] = useState("");

  type ViralRow = {
    title: string; channel: string; views: number; age_days: number;
    views_per_day: number; heat: number; url: string;
  };

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

  async function scanViral() {
    const q = nicheQuery.trim();
    if (!q || viralBusy) return;
    setViralBusy(true);
    setViralMsg("");
    try {
      const r = await api.post<{ results: ViralRow[] }>("/viral/scan", { query: q });
      setViral(r.results);
      if (!r.results.length) setViralMsg("No timestamped results came back — try a broader query.");
      load(platform);
    } catch (e) {
      setViralMsg(String(e).includes("429") ? "Rate limited — wait a bit." : String(e).slice(0, 120));
    } finally {
      setViralBusy(false);
    }
  }

  return (
    <div className="p-4 pb-24 md:p-6 md:pb-6">
      <div className="mb-4 flex flex-wrap items-center gap-2 md:gap-3">
        <h1 className="text-2xl font-bold">Trend board</h1>
        <div className="ml-auto flex flex-wrap gap-2">
          {PLATFORMS.map((p) => (
            <button
              key={p}
              onClick={() => setPlatform(p)}
              className={`tap rounded-full px-4 text-sm capitalize ${
                platform === p ? "bg-accent text-black font-semibold" : "border border-edge text-slate-400"
              }`}
            >
              {p}
            </button>
          ))}
          <button
            onClick={refresh}
            disabled={busy}
            className="tap rounded-full border border-accent2/40 px-4 text-sm text-accent2 hover:bg-accent2/10 disabled:opacity-40"
          >
            {busy ? "refreshing…" : "↻ refresh"}
          </button>
        </div>
      </div>
      {msg && <p className="mb-3 text-xs text-slate-500">{msg}</p>}

      {/* viral discovery: live search */}
      <section className="mb-6 rounded-xl border border-edge bg-panel p-4">
        <h2 className="font-semibold text-white">🔥 Find viral right now</h2>
        <p className="mt-0.5 text-xs text-slate-500">
          Live YouTube search — freshest short-form videos in your niche, ranked by views-per-day velocity. Results feed the AI's context too.
        </p>
        <form className="mt-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); scanViral(); }}>
          <input
            value={nicheQuery}
            onChange={(e) => setNicheQuery(e.target.value)}
            placeholder="your niche — e.g. ai tools, fitness, cooking…"
            className="min-h-[48px] flex-1 rounded-xl border border-edge bg-bg px-4 text-[15px] outline-none placeholder:text-slate-600 focus:border-accent"
          />
          <button type="submit" disabled={viralBusy || !nicheQuery.trim()}
            className="tap rounded-xl bg-accent px-5 font-semibold text-black disabled:opacity-40">
            {viralBusy ? "scanning…" : "Scan"}
          </button>
        </form>
        {viralMsg && <p className="mt-2 text-xs text-accent2">{viralMsg}</p>}
        {viral && viral.length > 0 && (
          <div className="mt-3 space-y-2">
            {viral.map((v) => (
              <a key={v.url} href={v.url} target="_blank" rel="noreferrer"
                className="block rounded-lg border border-edge bg-bg p-3 transition-colors hover:border-accent2/50">
                <div className="flex items-center gap-2 text-[11px] text-slate-500">
                  <span className="rounded bg-orange-500/20 px-1.5 py-0.5 font-bold text-orange-400">🔥 {v.heat.toFixed(0)}</span>
                  <span>{v.views.toLocaleString()} views in {v.age_days}d — {v.views_per_day.toLocaleString()}/day</span>
                  <span className="ml-auto truncate text-slate-600">{v.channel}</span>
                </div>
                <div className="mt-1 text-sm font-medium text-slate-100">{v.title}</div>
              </a>
            ))}
          </div>
        )}
      </section>

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
            <div className="text-[15px] font-medium text-slate-100">{t.title}</div>
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
