"""Cringe / saturated-phrase filter — post-processing gate.

Two jobs:
1. scan(text) -> violations: catch overused AI-slop and dead-trend phrases
   BEFORE the response reaches the UI.
2. The phrase list is also injected into generation prompts as a negative
   constraint (prevention), while scan+reject is the enforcement layer.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# (phrase, why it's banned) — case-insensitive, substring match
BANNED: list[tuple[str, str]] = [
    # AI-slop verbs/adjectives
    ("game-changer", "saturated hype noun"),
    ("game changer", "saturated hype noun"),
    ("unlock the secret", "AI-slop cliché"),
    ("unlock the", "AI-slop cliché"),
    ("unleash", "AI-slop cliché"),
    ("supercharge", "AI-slop cliché"),
    ("elevate your", "AI-slop cliché"),
    ("revolutionize", "AI-slop cliché"),
    ("revolutionary", "AI-slop cliché"),
    ("cutting-edge", "AI-slop cliché"),
    ("state-of-the-art", "AI-slop cliché"),
    ("harness the power", "AI-slop cliché"),
    ("dive into", "AI-slop opener"),
    ("delve", "AI-slop word"),
    ("let's explore", "AI-slop opener"),
    ("in today's fast-paced", "AI-slop opener"),
    ("in this video, we'll", "generic filler intro"),
    # dead viral formats
    ("feels illegal to know", "saturated 2024 listicle hook"),
    ("secret gurus don't want", "saturated guru hook"),
    ("they don't want you to know", "saturated conspiracy hook"),
    ("no-brainer", "saturated hype"),
    ("mind-blowing", "saturated hype"),
    ("blown away", "saturated hype"),
    ("mind = blown", "dead meme"),
    ("level up", "saturated gaming metaphor"),
    ("next level", "saturated hype"),
    ("take it to the next level", "saturated hype"),
    ("you won't believe", "clickbait floor"),
    ("you won't want to miss", "clickbait floor"),
    ("trust me on this", "filler credibility"),
    ("let that sink in", "dead engagement bait"),
    ("plot twist", "dead meme"),
    ("real talk", "dead filler"),
    ("smash that", "dead CTA"),
    ("like and subscribe", "generic CTA (rephrase with a reason)"),
    ("transform your life", "AI-slop promise"),
    ("change your life forever", "AI-slop promise"),
    ("the ultimate guide to", "saturated title"),
    ("must-see", "saturated hype"),
    ("don't sleep on", "saturated slang"),
    ("slaps", "dead slang"),
    ("this is your sign to", "dead TikTok format"),
    ("main character energy", "dead meme"),
    ("it's giving", "dead slang"),
    # emoji spam markers
    ("🚀", "emoji hype spam"),
    ("🔥", "emoji hype spam"),
    ("💯", "emoji hype spam"),
    ("👀", "emoji hype spam"),
]

_COMPILED = [
    (re.compile(re.escape(p), re.IGNORECASE), p, why) for p, why in BANNED
]


@dataclass
class Violation:
    phrase: str
    reason: str
    context: str  # snippet around the match


def scan(text: str) -> list[Violation]:
    """Return every banned-phrase hit with surrounding context."""
    out: list[Violation] = []
    seen: set[str] = set()
    for rx, phrase, why in _COMPILED:
        m = rx.search(text)
        if m and phrase not in seen:
            seen.add(phrase)
            start = max(0, m.start() - 30)
            end = min(len(text), m.end() + 30)
            out.append(Violation(phrase=phrase, reason=why,
                                 context="…" + text[start:end].replace("\n", " ") + "…"))
    return out


def violations_payload(vs: list[Violation]) -> list[dict]:
    return [{"phrase": v.phrase, "reason": v.reason, "context": v.context} for v in vs]


def banned_list_for_prompt(max_items: int = 25) -> str:
    """Compact negative-constraint list for generation prompts."""
    phrases = [p for p, _ in BANNED if len(p) > 3 and not ord(p[0]) > 0x1F000]
    return ", ".join(f'"{p}"' for p in phrases[:max_items])


def clean_items(items: list[dict], text_key: str) -> tuple[list[dict], list[Violation]]:
    """Reject dict items whose text_key contains a banned phrase.

    Returns (kept_items, violations) — rejected items never reach the UI.
    """
    kept, violations = [], []
    for it in items:
        text = str(it.get(text_key, ""))
        vs = scan(text)
        if vs:
            violations.extend(vs)
        else:
            kept.append(it)
    return kept, violations
