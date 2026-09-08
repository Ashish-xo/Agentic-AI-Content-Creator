"use client";

import { useState } from "react";

export function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [ok, setOk] = useState(false);

  async function copy() {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
      } else {
        // non-secure context / old iOS fallback
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        ta.remove();
      }
    } catch {
      return; // silently fail rather than crash the page
    }
    setOk(true);
    setTimeout(() => setOk(false), 1500);
  }

  return (
    <button
      onClick={copy}
      className="tap rounded-lg border border-edge px-3 text-xs text-slate-400 hover:text-white active:bg-edge"
    >
      {ok ? "✓ Copied" : label}
    </button>
  );
}
