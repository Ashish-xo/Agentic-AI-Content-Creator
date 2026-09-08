"use client";

import { useEffect, useState } from "react";
import { api, type Persona } from "@/lib/api";

type SettingsView = {
  llm_model: string;
  environment: string;
  providers: Record<string, boolean>;
};
type Billing = { configured: boolean; current_plan: string; plans: { id: string; name: string; price_usd: number }[] };

export default function SettingsPage() {
  const [persona, setPersona] = useState<Persona | null>(null);
  const [settings, setSettings] = useState<SettingsView | null>(null);
  const [billing, setBilling] = useState<Billing | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.get<Persona>("/persona").then(setPersona).catch(() => {});
    api.get<SettingsView>("/settings").then(setSettings).catch(() => {});
    api.get<Billing>("/billing/config").then(setBilling).catch(() => {});
  }, []);

  async function save() {
    if (!persona) return;
    await api.put("/persona", {
      niche: persona.niche, target_audience: persona.target_audience,
      tone_of_voice: persona.tone_of_voice, content_goal: persona.content_goal,
    });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  async function reRun() {
    await api.post("/persona/reset");
    const p = await api.get<Persona>("/persona");
    setPersona(p);
  }

  const field = (key: keyof Persona, label: string) => (
    <label className="block">
      <span className="mb-1 block text-xs uppercase tracking-wide text-slate-500">{label}</span>
      <input
        value={(persona?.[key] as string) || ""}
        onChange={(e) => setPersona((p) => (p ? { ...p, [key]: e.target.value } : p))}
        className="min-h-[48px] w-full rounded-lg border border-edge bg-panel px-3 py-3 text-sm outline-none focus:border-accent"
      />
    </label>
  );

  return (
    <div className="max-w-3xl space-y-8 p-4 pb-24 md:p-6 md:pb-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      <section className="rounded-xl border border-edge bg-panel p-5 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-semibold text-white">Creator persona</h2>
          <button onClick={reRun} className="tap text-sm text-accent2 hover:underline">re-run onboarding</button>
        </div>
        {field("niche", "Niche")}
        {field("target_audience", "Target audience")}
        {field("tone_of_voice", "Tone of voice")}
        {field("content_goal", "Content goal")}
        <button onClick={save} className="tap rounded-lg bg-accent px-4 text-sm font-semibold text-black">
          {saved ? "Saved ✓" : "Save persona"}
        </button>
      </section>

      <section className="rounded-xl border border-edge bg-panel p-5">
        <h2 className="mb-3 font-semibold text-white">Engine & providers</h2>
        {settings && (
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="text-slate-500">LLM model</div>
            <div className="font-mono text-accent">{settings.llm_model}</div>
            <div className="text-slate-500">Environment</div>
            <div>{settings.environment}</div>
            {Object.entries(settings.providers).map(([k, v]) => (
              <div key={k} className="contents">
                <div className="text-slate-500">{k.replace(/_/g, " ")}</div>
                <div className={v ? "text-green-400" : "text-slate-600"}>{v ? "configured ✓" : "not set (dev fallback)"}</div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="rounded-xl border border-edge bg-panel p-5">
        <h2 className="mb-3 font-semibold text-white">Plan</h2>
        {billing && (
          <div className="flex flex-wrap gap-2 text-sm">
            {billing.plans.map((p) => (
              <div key={p.id}
                className={`rounded-lg border px-3 py-2 ${
                  billing.current_plan === p.id ? "border-accent text-accent" : "border-edge text-slate-400"}`}>
                <div className="font-semibold">{p.name}</div>
                <div className="text-xs">{p.price_usd === 0 ? "free" : `$${p.price_usd}/mo`}</div>
              </div>
            ))}
          </div>
        )}
        {billing && !billing.configured && (
          <p className="mt-3 text-xs text-slate-500">
            Stripe keys not set — checkout returns a clear 503 until configured in backend/.env.
          </p>
        )}
      </section>
    </div>
  );
}
