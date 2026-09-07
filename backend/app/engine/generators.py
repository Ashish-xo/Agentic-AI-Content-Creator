"""Generators: hooks, scripts, critique, platform variants.

All persona-aware; JSON-mode outputs persisted by callers.
"""
from __future__ import annotations

from typing import Any

from app.services import llm

PERSONA_LINE = "Creator persona: {summary}"


def _persona_block(persona_summary: str | None) -> str:
    return PERSONA_LINE.format(summary=persona_summary) if persona_summary else ""


async def generate_hooks(
    topic: str,
    platform: str = "youtube",
    count: int = 3,
    persona: str | None = None,
) -> list[dict[str, Any]]:
    thumb = ", plus a matching thumbnail text pairing (max 4 words)" if platform == "youtube" else ""
    result = await llm.complete_json(
        [
            {
                "role": "system",
                "content": (
                    "You are a viral content hook writer. "
                    + _persona_block(persona)
                    + f"\nPlatform psychology: {'first-5-seconds payoff + open loop' if platform == 'youtube' else 'instant visual hook + DM-share trigger'}."
                    + "\nReturn ONLY a JSON array of objects with keys: hook, archetype, rationale"
                    + thumb
                    + ". No prose outside JSON."
                ),
            },
            {"role": "user", "content": f"Write {count} {platform} hooks about: {topic}"},
        ],
        temperature=0.8,
    )
    items = result if isinstance(result, list) else result.get("hooks", [])
    return items[:count]


async def generate_script(
    topic: str,
    platform: str = "youtube",
    seconds: int = 30,
    persona: str | None = None,
) -> dict[str, Any]:
    return await llm.complete_json(
        [
            {
                "role": "system",
                "content": (
                    "You are a short-form video scriptwriter. " + _persona_block(persona)
                    + f"\nReturn ONLY JSON: {{\"title\": str, \"blocks\": [{{\"time\": \"0:00-0:05\", \"visual\": str, \"audio\": str}}], \"cta\": str}}"
                    + f" for a {seconds}-second {platform} video."
                ),
            },
            {"role": "user", "content": f"Script about: {topic}"},
        ],
        temperature=0.8,
        max_tokens=3072,
    )


async def critique_content(
    draft: str,
    platform: str = "instagram",
    persona: str | None = None,
) -> dict[str, Any]:
    return await llm.complete_json(
        [
            {
                "role": "system",
                "content": (
                    "You are an algorithm-aware content editor. " + _persona_block(persona)
                    + "\nCritique the draft for hook strength, share triggers, length/CTA fit."
                    + "\nReturn ONLY JSON: {\"score_before\": int, \"score_after\": int, \"issues\": [{\"quote\": str, \"problem\": str, \"fix\": str}], \"rewritten\": str}"
                ),
            },
            {"role": "user", "content": f"Platform: {platform}\nDraft:\n{draft}"},
        ],
        temperature=0.4,
    )


async def make_variants(premise: str, persona: str | None = None) -> dict[str, Any]:
    """Platform-switching context: one premise -> per-platform executions."""
    return await llm.complete_json(
        [
            {
                "role": "system",
                "content": (
                    "You adapt one content premise for each platform's algorithm. "
                    + _persona_block(persona)
                    + "\nReturn ONLY JSON: {\"youtube_long\": {\"title\": str, \"hook\": str, \"outline\": [str]},"
                    " \"youtube_short\": {\"hook\": str, \"script\": str},"
                    " \"instagram_reel\": {\"first_frame\": str, \"hook\": str, \"caption\": str, \"share_cta\": str},"
                    " \"instagram_note\": str}"
                ),
            },
            {"role": "user", "content": f"Premise: {premise}"},
        ],
        temperature=0.7,
        max_tokens=3072,
    )
