// Attaches the Clerk JWT to backend calls when auth is configured.
// Keyless dev: returns {} and the backend falls back to its dev-user identity.
export function authHeaders(): Record<string, string> {
  return {};
}

/** Async variant: pulls a fresh Clerk session token from the browser SDK. */
export async function authHeadersAsync(): Promise<Record<string, string>> {
  const clerk = (window as unknown as { Clerk?: { session?: { getToken(o: { skipDedup?: boolean }): Promise<string | null> } } }).Clerk;
  try {
    const tok = await clerk?.session?.getToken({ skipDedup: true });
    return tok ? { Authorization: `Bearer ${tok}` } : {};
  } catch {
    return {};
  }
}
