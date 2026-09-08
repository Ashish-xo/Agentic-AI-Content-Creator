"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AuthWidget } from "@/components/auth-widget";
import { CLERK_ON } from "@/components/auth-provider";

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
  const isLanding = pathname === "/";
  if (isLanding) return <>{children}</>;

  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="w-52 shrink-0 border-r border-edge bg-panel flex flex-col">
        <div className="px-4 py-4 text-accent font-bold tracking-tight">
          Content<span className="text-accent2">Copilot</span>
        </div>
        <nav className="flex-1 px-2 space-y-1">
          {NAV.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors ${
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
        <div className="px-4 py-3 text-[11px] text-slate-500">
          brain: qwen3.8-flash · b.ai
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto">{children}</main>
    </div>
  );
}
