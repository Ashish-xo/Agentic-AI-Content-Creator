"""Generators: hooks, scripts, critique, platform variants.

All persona-aware; JSON-mode outputs persisted by callers.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.engine import cringe, fewshot
from app.services import llm

PERSONA_LINE = "Creator persona: {summary}"


def _persona_block(persona_summary: str | None) -> str:
    return PERSONA_LINE.format(summary=persona_summary) if persona_summary else ""


BAN_LINE = (
    "BANNED phrases — using any of these gets the output rejected: "
    + cringe.banned_list_for_prompt()
    + ". Also no rocket/fire/100/eyes emoji."
)


def _filter_hooks(hooks: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict]]:
    """Post-processing gate: reject saturated hooks before they reach the UI."""
    kept, violations = cringe.clean_items(hooks, "hook")
    return kept, cringe.violations_payload(violations)


async def generate_hooks(
    topic: str,
    platform: str = "youtube",
    count: int = 3,
    persona: str | None = None,
    db: Session | None = None,
) -> dict[str, Any]:
    """Dynamic few-shot: retrieve 3-5 real high-performing hooks closest to the
    topic/platform, ask the model to analyze them, then generate in that format.
    Output passes through the cringe filter; rejected items are reported, not shown."""
    thumb = ", plus a matching thumbnail text pairing (max 4 words)" if platform == "youtube" else ""
    examples: list[Any] = []
    if db is not None:
        examples = fewshot.select_examples(db, platform, topic, k=5)
        task = fewshot.fewshot_block(examples, topic, count + 2)  # +2 buffer for filter rejects
    else:
        task = f"Write {count} {platform} hooks about: {topic}"
    result = await llm.complete_json(
        [
            {
                "role": "system",
                "content": (
                    "You are a viral content hook writer. "
                    + _persona_block(persona)
                    + f"\nPlatform psychology: {'first-5-seconds payoff + open loop' if platform == 'youtube' else 'instant visual hook + DM-share trigger'}."
                    + "\n" + BAN_LINE
                    + "\nReturn ONLY a JSON array of objects with keys: hook, archetype, rationale"
                    + thumb
                    + ". No prose outside JSON."
                ),
            },
            {"role": "user", "content": task},
        ],
        temperature=0.8,
    )
    items = result if isinstance(result, list) else result.get("hooks", [])
    kept, rejected = _filter_hooks(items)
    if len(kept) < count and items:
        # too many rejected -> one regeneration pass naming the offenders
        bad = ", ".join(v["phrase"] for v in rejected[:6])
        retry = await llm.complete_json(
            [
                {"role": "system", "content":
                    "You rewrite hooks that failed a saturation check. Keep the topic and "
                    "structure, drop every banned phrase. " + BAN_LINE
                    + "\nReturn ONLY a JSON array of {hook, archetype, rationale}" + thumb + "."},
                {"role": "user", "content":
                    f"Topic: {topic}. These drafts were rejected for banned phrases ({bad}):\n"
                    + json.dumps(items[:count], ensure_ascii=False)[:2000]},
            ],
            temperature=0.7,
        )
        retry_items = retry if isinstance(retry, list) else retry.get("hooks", [])
        kept2, _ = _filter_hooks(retry_items)
        kept = (kept + kept2)[:count]
    return {"hooks": kept,
            "rejected": rejected,
            "fewshot_examples_used": [
                {"hook": e.hook, "archetype": e.archetype} for e in examples]}


async def generate_script(
    topic: str,
    platform: str = "youtube",
    seconds: int = 30,
    persona: str | None = None,
) -> dict[str, Any]:
    script = await llm.complete_json(
        [
            {
                "role": "system",
                "content": (
                    "You are a short-form video scriptwriter. " + _persona_block(persona)
                    + "\n" + BAN_LINE
                    + f"\nReturn ONLY JSON: {{\"title\": str, \"blocks\": [{{\"time\": \"0:00-0:05\", \"visual\": str, \"audio\": str}}], \"cta\": str}}"
                    + f" for a {seconds}-second {platform} video."
                ),
            },
            {"role": "user", "content": f"Script about: {topic}"},
        ],
        temperature=0.8,
        max_tokens=3072,
    )
    # post-processing gate over the whole script text
    flat = json.dumps(script, ensure_ascii=False)
    violations = cringe.violations_payload(cringe.scan(flat))
    return {**script, "filter_violations": violations}


async def critique_content(
    draft: str,
    platform: str = "instagram",
    persona: str | None = None,
) -> dict[str, Any]:
    out = await llm.complete_json(
        [
            {
                "role": "system",
                "content": (
                    "You are an algorithm-aware content editor. " + _persona_block(persona)
                    + "\n" + BAN_LINE
                    + "\nCritique the draft for hook strength, share triggers, length/CTA fit."
                    + "\nReturn ONLY JSON: {\"score_before\": int, \"score_after\": int, \"issues\": [{\"quote\": str, \"problem\": str, \"fix\": str}], \"rewritten\": str}"
                ),
            },
            {"role": "user", "content": f"Platform: {platform}\nDraft:\n{draft}"},
        ],
        temperature=0.4,
    )
    # the rewritten version must itself pass the gate — reject it if not
    rewritten = str(out.get("rewritten", ""))
    vs = cringe.scan(rewritten)
    if vs:
        out["rewritten_rejected"] = True
        out["rewritten"] = ""
    out["filter_violations"] = cringe.violations_payload(vs)
    return out


async def make_variants(premise: str, persona: str | None = None) -> dict[str, Any]:
    """Platform-switching context: one premise -> per-platform executions."""
    out = await llm.complete_json(
        [
            {
                "role": "system",
                "content": (
                    "You adapt one content premise for each platform's algorithm. "
                    + _persona_block(persona)
                    + "\n" + BAN_LINE
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
    vs = cringe.scan(json.dumps(out, ensure_ascii=False))
    return {**out, "filter_violations": cringe.violations_payload(vs)}
