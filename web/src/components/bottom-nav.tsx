"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/dashboard", label: "Home", icon: "▦" },
  { href: "/chat", label: "Chat", icon: "◇" },
  { href: "/trends", label: "Trends", icon: "▲" },
  { href: "/generate", label: "Create", icon: "✦" },
  { href: "/settings", label: "More", icon: "⚙" },
];

export function BottomNav() {
  const p = usePathname();
  return (
    <nav className="pb-safe fixed inset-x-0 bottom-0 z-30 flex border-t border-edge bg-panel/95 backdrop-blur md:hidden">
      {TABS.map((t) => (
        <Link
          key={t.href}
          href={t.href}
          className={`tap flex-1 flex-col !min-h-[56px] gap-0.5 text-[11px] ${
            p.startsWith(t.href) ? "text-accent" : "text-slate-500"
          }`}
        >
          <span className="text-lg leading-none">{t.icon}</span>
          {t.label}
        </Link>
      ))}
    </nav>
  );
}
