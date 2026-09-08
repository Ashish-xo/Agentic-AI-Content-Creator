"use client";

// Clerk provider — mounts only when publishable key is present (NEXT_PUBLIC_*
// is inlined at build). Keyless dev: renders children untouched.
import { useMemo } from "react";
import dynamic from "next/dynamic";

const ClerkProvider = dynamic(
  () => import("@clerk/nextjs").then((m) => m.ClerkProvider),
  { ssr: false },
);

export const CLERK_ON = !!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const on = useMemo(() => CLERK_ON, []);
  if (!on) return <>{children}</>;
  return <ClerkProvider>{children}</ClerkProvider>;
}
