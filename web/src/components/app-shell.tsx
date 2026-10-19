"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { AuthWidget } from "@/components/auth-widget";
import { CLERK_ON } from "@/components/auth-provider";
import { BottomNav } from "@/components/bottom-nav";
import { NicheModal } from "@/components/niche-modal";
import { api } from "@/lib/api";
import { getStoredNiche, setStoredNiche } from "@/lib/niche";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: "▦" },
  { href: "/chat", label: "Copilot Chat", icon: "◇" },
  { href: "/trends", label: "Trends", icon: "▲" },
  { href: "/generate", label: "Generate", icon: "✦" },
  { href: "/projects", label: "Projects", icon: "◈" },
  { href: "/settings", label: "Settings", icon: "⚙" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [niche, setNiche] = useState<string | null>(null);
  const [nicheModal, setNicheModal] = useState(false);
  const isLanding = pathname === "/";

  // initial niche resolution: localStorage first, DB persona as source of truth
  useEffect(() => {
    if (isLanding) return;
    let cancelled = false;
    (async () => {
      const local = getStoredNiche();
      const p = await api.get<{ niche: string | null; completed: boolean }>("/persona").catch(() => null);
      if (cancelled) return;
      const dbNiche = p?.niche ?? null;
      if (dbNiche) {
        setStoredNiche(dbNiche); // keep local mirror in sync with DB
        setNiche(dbNiche);
      } else if (local) {
        setNiche(local);
        api.put("/persona", { niche: local }).catch(() => {}); // sync to DB
      } else {
        setNiche(null);
        setNicheModal(true); // first visit -> ask
      }
    })();
    return () => { cancelled = true; };
  }, [isLanding]);

  const onNicheSaved = useCallback((label: string) => {
    setNiche(label);
    window.dispatchEvent(new CustomEvent("cc-niche-changed", { detail: label }));
  }, []);

  // close drawer on navigation
  useEffect(() => { setOpen(false); }, [pathname]);

  if (isLanding) return <>{children}</>;

  return (
    <div className="flex h-[100dvh] overflow-hidden">
      {/* backdrop (mobile only, when drawer open) */}
      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
          onClick={() => setOpen(false)}
          aria-hidden
        />
      )}

      {/* drawer below md, fixed rail at md+ */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-60 shrink-0 transform flex-col border-r border-edge bg-panel transition-transform duration-200 ease-out md:static md:w-52 md:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="px-4 py-4 text-accent font-bold tracking-tight">
          Content<span className="text-accent2">Copilot</span>
        </div>
        <nav className="flex-1 px-2 space-y-1">
          {NAV.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              className={`tap !justify-start flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors ${
                pathname.startsWith(n.href)
                  ? "bg-edge text-white"
                  : "text-slate-400 hover:text-white hover:bg-edge/50"
              }`}
            >
              <span className="w-4 text-center">{n.icon}</span>
              {n.label}
            </Link>
          ))}
        </nav>
        <AuthWidget enabled={CLERK_ON} />
        {niche && (
          <button onClick={() => setNicheModal(true)}
            className="mx-4 mb-2 rounded-lg border border-edge px-3 py-1.5 text-left text-[11px] text-slate-400 hover:text-white"
            title="Change your niche">
            🎯 niche: <span className="text-slate-200">{niche}</span> · change
          </button>
        )}
        <div className="px-4 py-3 text-[11px] text-slate-500">
          brain: gpt-oss-20b · Pollinations (free) — BYOK in settings
        </div>
      </aside>

      <NicheModal
        open={nicheModal}
        initial={niche}
        mode={niche ? "change" : "first"}
        onClose={() => setNicheModal(false)}
        onSaved={onNicheSaved}
      />

      {/* hamburger + niche chip (mobile top bar) */}
      <div className="fixed left-2 top-2 z-20 flex gap-2 md:hidden">
        <button
          aria-label="Open menu"
          onClick={() => setOpen(true)}
          className="tap rounded-lg border border-edge bg-panel px-3 text-slate-300"
        >
          ☰
        </button>
        {niche && (
          <button onClick={() => setNicheModal(true)}
            className="tap max-w-[180px] truncate rounded-lg border border-edge bg-panel px-3 text-xs text-slate-300"
            title="Change your niche">
            🎯 {niche}
          </button>
        )}
      </div>

      <main className="scroll-ios flex-1 overflow-y-auto pt-14 pb-[calc(64px+env(safe-area-inset-bottom))] md:pt-0 md:pb-0">
        {children}
      </main>

      <BottomNav />
    </div>
  );
}
