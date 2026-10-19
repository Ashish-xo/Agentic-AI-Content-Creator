// Niche selection state — localStorage-first, DB-synced.
// The 6 canonical options map 1:1 to the onboarding modal cards.

export type NicheOption = { id: string; label: string; icon: string };

export const NICHE_OPTIONS: NicheOption[] = [
  { id: "tech", label: "Tech & Gadgets", icon: "💻" },
  { id: "software", label: "Software & Coding", icon: "⌨️" },
  { id: "fitness", label: "Fitness & Gym", icon: "💪" },
  { id: "cooking", label: "Cooking & Food", icon: "🍳" },
  { id: "business", label: "Business & Finance", icon: "📈" },
  { id: "vlogging", label: "Vlogging & Lifestyle", icon: "🎥" },
];

const KEY = "cc_niche";

export function getStoredNiche(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(KEY);
  } catch {
    return null; // private mode / storage disabled
  }
}

export function setStoredNiche(niche: string): void {
  try {
    window.localStorage.setItem(KEY, niche);
  } catch {
    /* storage unavailable — DB persona still carries it */
  }
}

export function clearStoredNiche(): void {
  try {
    window.localStorage.removeItem(KEY);
  } catch {
    /* noop */
  }
}

/** Match a stored/DB niche string to a canonical option (for pre-selecting a card). */
export function matchOption(niche: string | null | undefined): NicheOption | null {
  if (!niche) return null;
  const low = niche.toLowerCase();
  return (
    NICHE_OPTIONS.find((o) => low === o.label.toLowerCase()) ??
    NICHE_OPTIONS.find((o) => low.includes(o.id) || o.label.toLowerCase().includes(low.split(" ")[0])) ??
    null
  );
}
