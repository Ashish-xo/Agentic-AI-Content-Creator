"use client";

import { useEffect, useState } from "react";
import { api, type Project } from "@/lib/api";

export default function ProjectsPage() {
  const [rows, setRows] = useState<Project[]>([]);
  const [premise, setPremise] = useState("");
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState<Project | null>(null);

  const load = () => api.get<Project[]>("/projects").then(setRows).catch(() => {});
  useEffect(() => { load(); }, []);

  async function create() {
    if (!premise.trim()) return;
    setBusy(true);
    try {
      await api.post("/generate/variants", { premise });
      setPremise("");
      await load();
    } finally {
      setBusy(false);
    }
  }

  const v = open?.variants as Record<string, Record<string, unknown>> | undefined;

  return (
    <div className="p-6 max-w-5xl">
      <h1 className="mb-1 text-2xl font-bold">Projects</h1>
      <p className="mb-4 text-sm text-slate-500">
        One premise in → per-platform executions out (YouTube long-form, Short, Reel, Note).
      </p>
      <div className="mb-6 flex gap-2">
        <input value={premise} onChange={(e) => setPremise(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && create()}
          placeholder="e.g. 15-minute workouts for dads who think they have no time"
          className="flex-1 rounded-xl border border-edge bg-panel px-4 py-2.5 outline-none focus:border-accent" />
        <button onClick={create} disabled={busy}
          className="rounded-xl bg-accent px-5 py-2.5 font-semibold text-black disabled:opacity-40">
          {busy ? "adapting…" : "Make variants"}
        </button>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {rows.map((p) => (
          <button key={p.id} onClick={() => setOpen(p)}
            className="rounded-xl border border-edge bg-panel p-4 text-left hover:border-accent/50">
            <div className="font-semibold text-white">{p.name}</div>
            <div className="mt-1 line-clamp-2 text-sm text-slate-400">{p.premise}</div>
            <div className="mt-2 text-xs text-slate-600">{Object.keys(p.variants || {}).length} platform variants</div>
          </button>
        ))}
        {!rows.length && <p className="text-sm text-slate-500">No projects yet — add a premise above.</p>}
      </div>

      {open && v && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-6" onClick={() => setOpen(null)}>
          <div className="max-h-[85vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-edge bg-bg p-6"
            onClick={(e) => e.stopPropagation()}>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-bold">{open.name}</h2>
              <button onClick={() => setOpen(null)} className="text-slate-500 hover:text-white">✕</button>
            </div>
            <div className="space-y-4 text-sm">
              {Object.entries(v).map(([plat, body]) => (
                <div key={plat} className="rounded-xl border border-edge bg-panel p-4">
                  <div className="mb-2 text-[11px] font-bold uppercase tracking-wide text-accent">{plat.replace(/_/g, " ")}</div>
                  <pre className="whitespace-pre-wrap font-sans text-slate-300">{JSON.stringify(body, null, 2)}</pre>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
