"use client";

// Renders Clerk sign-in/sign-out UI when keys are configured; nothing otherwise.
import dynamic from "next/dynamic";

const SignedIn = dynamic(
  () => import("@clerk/nextjs").then((m) => m.SignedIn),
  { ssr: false },
);
const SignedOut = dynamic(
  () => import("@clerk/nextjs").then((m) => m.SignedOut),
  { ssr: false },
);
const UserButton = dynamic(
  () => import("@clerk/nextjs").then((m) => m.UserButton),
  { ssr: false },
);
const SignInButton = dynamic(
  () => import("@clerk/nextjs").then((m) => m.SignInButton),
  { ssr: false },
);

export function AuthWidget({ enabled }: { enabled: boolean }) {
  if (!enabled) return null;
  return (
    <div className="px-3 py-3">
      <SignedIn>
        <div className="flex items-center gap-2">
          <UserButton />
          <span className="text-[11px] text-slate-500">signed in</span>
        </div>
      </SignedIn>
      <SignedOut>
        <SignInButton mode="modal">
          <button className="w-full rounded-lg bg-accent px-3 py-2 text-sm font-semibold text-black">
            Sign in
          </button>
        </SignInButton>
      </SignedOut>
    </div>
  );
}
