// Clerk middleware — active only when NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY exists.
// Keyless dev: everything passes through (backend uses its dev-user fallback).
import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse, type NextRequest } from "next/server";

const CLERK_ON = !!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;

const isPublic = createRouteMatcher(["/", "/sign-in(.*)", "/sign-up(.*)"]);

const clerkHandler = clerkMiddleware(async (auth, req) => {
  if (!isPublic(req)) await auth.protect();
});

export default function middleware(req: NextRequest, event: { waitUntil(p: Promise<unknown>): void }) {
  if (!CLERK_ON) return NextResponse.next();
  return clerkHandler(req as never, event as never) as NextResponse;
}

export const config = {
  matcher: ["/((?!_next|favicon.ico|.*\\.[\\w]+$).*)", "/"],
};
