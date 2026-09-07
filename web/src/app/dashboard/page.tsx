"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type Persona, type Trend } from "@/lib/api";

export default function Dashboard() {
  const [trends, setTrends] = useState<Trend[]>([]);
  const [persona, setPersona] = useState<Persona | null>(null);
  const [digest, setDigest] = useState<{ body: string | null }>({ body: null });

  useEffect(() => {
    api.get<Trend[]>("/trends?limit=6").then(setTrends).catch(() => {});
    api.get<Persona>("/persona").then(setPersona).catch(() => {});
    api.get<{ body: string | null }>("/digest/latest").then(setDigest).catch(() => {});
  }, []);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <Link href="/chat" className="rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-black">
          Open Copilot →
        </Link>
      </div>

      {persona && !persona.completed && (
        <Link
          href="/chat"
          className="block rounded-xl border border-accent2/40 bg-accent2/10 p-4 text-sm hover:bg-accent2/20"
        >
          <span className="font-semibold text-accent2">Finish your creator profile →</span>{" "}
          <span className="text-slate-300">
            4 quick questions in chat so every hook, script and critique is written for your niche.
          </span>
        </Link>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        <section className="rounded-xl border border-edge bg-panel p-4">
          <h2 className="mb-3 font-semibold text-white">Hottest signals right now</h2>
          <ul className="space-y-2 text-sm">
            {trends.map((t) => (
              <li key={`${t.platform}-${t.title}`} className="flex items-start gap-2">
                <span
                  className={`mt-0.5 rounded px-1.5 py-0.5 text-[10px] font-bold ${
                    t.platform === "youtube" ? "bg-red-500/20 text-red-400"
                    : t.platform === "instagram" ? "bg-pink-500/20 text-pink-400"
                    : "bg-slate-500/20 text-slate-300"
                  }`}
                >
                  {t.platform}
                </span>
                <div className="flex-1">
                  <div className="text-slate-200">{t.title}</div>
                  <div className="text-xs text-slate-500">{t.kind} · heat {t.heat.toFixed(0)}</div>
                </div>
              </li>
            ))}
            {!trends.length && <li className="text-slate-500">loading…</li>}
          </ul>
          <Link href="/trends" className="mt-3 inline-block text-xs text-accent hover:underline">
            full trend board →
          </Link>
        </section>

        <section className="rounded-xl border border-edge bg-panel p-4">
          <h2 className="mb-3 font-semibold text-white">Daily digest</h2>
          {digest.body ? (
            <div className="md-body text-sm whitespace-pre-wrap text-slate-300">{digest.body}</div>
          ) : (
            <p className="text-sm text-slate-500">
              The scheduler writes a persona-aware opportunity digest every 24h (and once at boot).
              Finish the creator profile to personalize it.
            </p>
          )}
        </section>
      </div>

      <div className="grid gap-4 md:grid-cols-3 text-sm">
        {[
          { href: "/generate", t: "Generate", d: "Hooks, scripts, critiques — persisted to your library." },
          { href: "/projects", t: "Projects", d: "One premise → YouTube long/short + Reel variants." },
          { href: "/settings", t: "Settings", d: "Persona, model, plan, provider keys status." },
        ].map((c) => (
          <Link key={c.href} href={c.href} className="rounded-xl border border-edge bg-panel p-4 hover:border-accent/50">
            <div className="font-semibold text-white">{c.t}</div>
            <div className="mt-1 text-slate-400">{c.d}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
