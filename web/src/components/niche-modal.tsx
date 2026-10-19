"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { NICHE_OPTIONS, setStoredNiche } from "@/lib/niche";

type Props = {
  open: boolean;
  /** initial selection (from localStorage or DB persona) */
  initial?: string | null;
  /** "first" = can't dismiss until chosen; "change" = reopen with close button */
  mode: "first" | "change";
  onClose: () => void;
  /** receives the canonical niche label, e.g. "Fitness & Gym" */
  onSaved: (niche: string) => void;
};

export function NicheModal({ open, initial, mode, onClose, onSaved }: Props) {
  const [selected, setSelected] = useState<string | null>(initial ?? null);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (open) {
      setSelected(initial ?? null);
      setErr("");
    }
  }, [open, initial]);

  if (!open) return null;

  async function save() {
    if (!selected || saving) return;
    setSaving(true);
    setErr("");
    try {
      const opt = NICHE_OPTIONS.find((o) => o.id === selected);
      const label = opt?.label ?? selected;
      // persist to DB persona (merges with any existing audience/tone/goal fields)
      await api.put("/persona", { niche: label });
      setStoredNiche(label);
      onSaved(label);
      onClose();
    } catch (e) {
      setErr(String(e).slice(0, 140));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 p-0 md:items-center md:p-4"
      role="dialog" aria-modal="true" aria-label="Choose your content niche">
      <div className="w-full max-w-lg rounded-t-2xl border border-edge bg-panel p-5 pb-[calc(20px+env(safe-area-inset-bottom))] md:rounded-2xl md:pb-5">
        <div className="mb-1 flex items-center justify-between">
          <h2 className="text-lg font-bold text-white">What&apos;s your content niche?</h2>
          {mode === "change" && (
            <button onClick={onClose} aria-label="Close"
              className="tap rounded-lg px-2 text-slate-500 hover:text-white">✕</button>
          )}
        </div>
        <p className="mb-4 text-xs text-slate-500">
          Pick what you create — hooks, scripts, and trend picks get tuned to it.
        </p>

        <div className="grid grid-cols-2 gap-2.5">
          {NICHE_OPTIONS.map((o) => (
            <button key={o.id} onClick={() => setSelected(o.id)}
              aria-pressed={selected === o.id}
              className={`tap flex min-h-[64px] flex-col items-center justify-center gap-1 rounded-xl border px-2 py-3 text-center transition-colors ${
                selected === o.id
                  ? "border-accent bg-accent/10 text-accent"
                  : "border-edge bg-bg text-slate-300 active:border-slate-500"
              }`}>
              <span className="text-xl leading-none">{o.icon}</span>
              <span className="text-[13px] font-medium leading-tight">{o.label}</span>
            </button>
          ))}
        </div>

        {err && <p className="mt-3 text-xs text-red-400">{err}</p>}

        <button onClick={save} disabled={!selected || saving}
          className="tap mt-4 min-h-[48px] w-full rounded-xl bg-accent font-semibold text-black disabled:opacity-40">
          {saving ? "Saving…" : mode === "first" ? "Start creating →" : "Save niche"}
        </button>
        {mode === "first" && (
          <p className="mt-2 text-center text-[11px] text-slate-600">
            You can change this anytime from the header.
          </p>
        )}
      </div>
    </div>
  );
}
