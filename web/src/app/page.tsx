import Link from "next/link";

export default function Landing() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6 text-center">
      <div className="text-xs uppercase tracking-[0.3em] text-accent mb-4">
        algorithm-aware · youtube + instagram
      </div>
      <h1 className="text-5xl font-bold leading-tight max-w-3xl">
        The AI copilot that knows <span className="text-accent">why</span> things go viral.
      </h1>
      <p className="mt-5 max-w-xl text-slate-400 text-lg">
        Trend signals, platform psychology, persona-aware hooks, scripts, critiques
        and cross-platform variants — one conversational workspace.
      </p>
      <div className="mt-8 flex gap-3">
        <Link
          href="/dashboard"
          className="rounded-xl bg-accent px-6 py-3 font-semibold text-black hover:bg-accent/90"
        >
          Open dashboard
        </Link>
        <Link
          href="/chat"
          className="rounded-xl border border-edge px-6 py-3 font-semibold text-slate-200 hover:bg-panel"
        >
          Talk to the copilot
        </Link>
      </div>
      <div className="mt-14 grid grid-cols-1 md:grid-cols-4 gap-3 max-w-4xl text-sm text-left">
        {[
          ["Data layer", "Heat-scored trend signals from YouTube/Instagram, live adapters when keys exist."],
          ["Intelligence", "RAG over curated algorithm playbooks: hook rate, retention, share triggers."],
          ["Platform switching", "One premise in, per-platform variants out — re-timed hooks, re-cultured CTAs."],
          ["Conversation", "Persona onboarding + research / creation / optimization modes, streamed."],
        ].map(([t, d]) => (
          <div key={t} className="rounded-xl border border-edge bg-panel p-4">
            <div className="font-semibold text-white mb-1">{t}</div>
            <div className="text-slate-400 text-[13px]">{d}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
