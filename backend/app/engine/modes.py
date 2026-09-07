"""Chat modes: research / creation / optimization, with auto-detection.

Each mode carries its own rubric (layered into the system prompt), temperature,
token budget, and tool bias.
"""
from __future__ import annotations

MODES = ["research", "creation", "optimization"]

KEYWORD_HINTS: dict[str, list[str]] = {
    "research": ["viral", "trending", "trends", "going viral", "what's hot", "whats hot",
                 "this week", "analyz", "research", "ideas for", "what should i post",
                 "opportunity", "signal", "niche report"],
    "creation": ["write", "draft", "create", "hook", "script", "caption for", "give me",
                 "make me", "3 options", "generate", "outline", "storyboard", "title ideas"],
    "optimization": ["critique", "improve", "review", "fix my", "increase shares", "better",
                     "optimize", "punch up", "rate my", "feedback on", "rewrite this"],
}

RUBRICS: dict[str, str] = {
    "research": (
        "MODE: RESEARCH. Ground every claim in the provided trend data — cite platform, "
        "signal and heat score. Rank opportunities, explain WHY the algorithm favors each, "
        "and end with the single best play this week. If trend data is thin, say so."
    ),
    "creation": (
        "MODE: CREATION. Produce ready-to-use content, not advice about content. Match the "
        "persona's tone and audience exactly. Give labeled variants (A/B/C) with the hook "
        "archetype named for each, and keep scripts timed (e.g. 0:00-0:05 blocks)."
    ),
    "optimization": (
        "MODE: OPTIMIZATION. Critique the user's draft against algorithm mechanics (hook "
        "strength, share triggers, length ratios, CTA). Be specific: quote the weak phrase, "
        "explain the failure, then show the improved version. Score 0-10 before/after."
    ),
}

TEMPS = {"research": 0.5, "creation": 0.8, "optimization": 0.4}
BUDGETS = {"research": 2048, "creation": 3072, "optimization": 2048}
TOOL_BIAS = {"research": "trend_lookup", "creation": "hook_generate", "optimization": "analyze_content"}


def detect_mode(text: str) -> str | None:
    low = text.lower()
    scores = {m: sum(1 for h in hints if h in low) for m, hints in KEYWORD_HINTS.items()}
    best = max(scores, key=lambda m: scores[m])
    return best if scores[best] > 0 else None
