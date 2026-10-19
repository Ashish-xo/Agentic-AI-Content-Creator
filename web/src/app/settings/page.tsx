"use client";

import { useEffect, useState } from "react";
import { api, type Persona } from "@/lib/api";

type SettingsView = {
  llm_model: string;
  environment: string;
  providers: Record<string, boolean>;
};
type Billing = { configured: boolean; current_plan: string; plans: { id: string; name: string; price_usd: number }[] };
type LlmKey = { provider: string; api_key_preview: string | null; base_url: string | null; model: string | null; label: string };

const BYOK_PROVIDERS = [
  { id: "free", name: "Free (built-in)", hint: "Shared Pollinations engine — no key needed", keyless: true },
  { id: "groq", name: "Groq", hint: "Free tier at console.groq.com — fastest option", keyless: false },
  { id: "gemini", name: "Google Gemini", hint: "Free tier at aistudio.google.com", keyless: false },
  { id: "openrouter", name: "OpenRouter", hint: "One key, many models at openrouter.ai", keyless: false },
  { id: "openai", name: "OpenAI", hint: "Paid — platform.openai.com", keyless: false },
  { id: "custom", name: "Custom", hint: "Any OpenAI-compatible URL + model", keyless: false },
];

export default function SettingsPage() {
  const [persona, setPersona] = useState<Persona | null>(null);
  const [settings, setSettings] = useState<SettingsView | null>(null);
  const [billing, setBilling] = useState<Billing | null>(null);
  const [llmKey, setLlmKey] = useState<LlmKey | null>(null);
  const [saved, setSaved] = useState(false);

  // BYOK form state
  const [byokProvider, setByokProvider] = useState("free");
  const [byokKey, setByokKey] = useState("");
  const [byokBaseUrl, setByokBaseUrl] = useState("");
  const [byokModel, setByokModel] = useState("");
  const [byokSaving, setByokSaving] = useState(false);
  const [byokMsg, setByokMsg] = useState("");

  useEffect(() => {
    api.get<Persona>("/persona").then(setPersona).catch(() => {});
    api.get<SettingsView>("/settings").then(setSettings).catch(() => {});
    api.get<Billing>("/billing/config").then(setBilling).catch(() => {});
    api.get<LlmKey>("/llm-key").then((k) => {
      setLlmKey(k);
      setByokProvider(k.provider);
      setByokBaseUrl(k.base_url || "");
      setByokModel(k.model || "");
    }).catch(() => {});
  }, []);

  async function saveByok() {
    setByokSaving(true);
    setByokMsg("");
    try {
      const body: Record<string, string> = { provider: byokProvider };
      if (byokKey.trim()) body.api_key = byokKey.trim();
      if (byokProvider === "custom") {
        body.base_url = byokBaseUrl.trim();
        body.model = byokModel.trim();
      } else if (byokModel.trim() && byokProvider !== "free") {
        body.model = byokModel.trim();
      }
      await api.put("/llm-key", body);
      const k = await api.get<LlmKey>("/llm-key");
      setLlmKey(k);
      setByokKey("");
      setByokMsg("Saved ✓");
    } catch (e) {
      setByokMsg(`Failed: ${String(e).slice(0, 120)}`);
    } finally {
      setByokSaving(false);
      setTimeout(() => setByokMsg(""), 3000);
    }
  }

  async function resetByok() {
    setByokSaving(true);
    try {
      await api.del("/llm-key");
      const k = await api.get<LlmKey>("/llm-key");
      setLlmKey(k);
      setByokProvider("free");
      setByokBaseUrl("");
      setByokModel("");
      setByokMsg("Back on the free engine");
    } finally {
      setByokSaving(false);
      setTimeout(() => setByokMsg(""), 3000);
    }
  }

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

      <section className="rounded-xl border border-edge bg-panel p-5 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-semibold text-white">AI engine (bring your own key)</h2>
          {llmKey && llmKey.provider !== "free" && (
            <span className="text-xs text-green-400">
              {llmKey.label}{llmKey.api_key_preview ? ` · ${llmKey.api_key_preview}` : ""}
            </span>
          )}
        </div>
        <p className="text-xs text-slate-500">
          Your key is encrypted before storage and never shown again. It is used only for
          your requests. The free engine is shared and capped at ~8 chats/min — add your
          own key for 30/min and faster models.
        </p>
        <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
          {BYOK_PROVIDERS.map((p) => (
            <button key={p.id} onClick={() => setByokProvider(p.id)}
              title={p.hint}
              className={`tap rounded-lg border px-3 py-2 text-left text-sm ${
                byokProvider === p.id ? "border-accent bg-accent/10 text-accent" : "border-edge text-slate-400"}`}>
              <div className="font-semibold">{p.name}</div>
              <div className="text-[10px] leading-tight text-slate-500">{p.hint}</div>
            </button>
          ))}
        </div>
        {byokProvider !== "free" && (
          <div className="space-y-3 pt-1">
            <label className="block">
              <span className="mb-1 block text-xs uppercase tracking-wide text-slate-500">API key {llmKey?.api_key_preview ? `(saved: ${llmKey.api_key_preview})` : ""}</span>
              <input type="password" value={byokKey} onChange={(e) => setByokKey(e.target.value)}
                placeholder={llmKey?.api_key_preview ? "saved — leave blank to keep" : "paste your key"}
                className="min-h-[48px] w-full rounded-lg border border-edge bg-panel px-3 py-3 text-sm outline-none focus:border-accent" />
            </label>
            {byokProvider === "custom" && (
              <>
                <label className="block">
                  <span className="mb-1 block text-xs uppercase tracking-wide text-slate-500">Base URL</span>
                  <input value={byokBaseUrl} onChange={(e) => setByokBaseUrl(e.target.value)}
                    placeholder="https://your-provider.example/v1"
                    className="min-h-[48px] w-full rounded-lg border border-edge bg-panel px-3 py-3 text-sm outline-none focus:border-accent" />
                </label>
                <label className="block">
                  <span className="mb-1 block text-xs uppercase tracking-wide text-slate-500">Model name</span>
                  <input value={byokModel} onChange={(e) => setByokModel(e.target.value)}
                    placeholder="provider-model-id"
                    className="min-h-[48px] w-full rounded-lg border border-edge bg-panel px-3 py-3 text-sm outline-none focus:border-accent" />
                </label>
              </>
            )}
            {byokProvider !== "custom" && (
              <label className="block">
                <span className="mb-1 block text-xs uppercase tracking-wide text-slate-500">Model (optional override)</span>
                <input value={byokModel} onChange={(e) => setByokModel(e.target.value)}
                  placeholder="default model for this provider"
                  className="min-h-[48px] w-full rounded-lg border border-edge bg-panel px-3 py-3 text-sm outline-none focus:border-accent" />
              </label>
            )}
          </div>
        )}
        <div className="flex flex-wrap items-center gap-3">
          <button onClick={saveByok} disabled={byokSaving || byokProvider === "custom" ? byokSaving : byokSaving}
            className="tap rounded-lg bg-accent px-4 text-sm font-semibold text-black disabled:opacity-40">
            {byokSaving ? "Saving…" : byokProvider === "free" ? "Switch to free engine" : "Save key"}
          </button>
          {llmKey && llmKey.provider !== "free" && (
            <button onClick={resetByok} disabled={byokSaving}
              className="tap text-sm text-slate-500 hover:text-white">remove key</button>
          )}
          {byokMsg && <span className="text-xs text-accent2">{byokMsg}</span>}
        </div>
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
