"""Copilot pipeline (LangGraph-shaped, dependency-free).

Stages: intent routing -> context assembly (persona + mode rubric + RAG +
trend lookup) -> streamed LLM answer. The same context assembly is shared
with the non-streaming path.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.orm import Session

from app.engine import cringe, modes, rag
from app.engine.onboarding import LABELS, FIELDS  # noqa: F401  (re-export for routes)
from app.models.tables import Persona
from app.services import llm, trends

SYSTEM_BASE = (
    "You are Content Copilot, an algorithm-aware assistant for creators on "
    "YouTube and Instagram. Reply style: short paragraphs and bullets, bold key "
    "terms, plain markdown, no hype or emoji spam, ONE clear next step at the "
    "end. Never invent trend numbers — use only the data you are given. "
    "Never use saturated phrases: " + cringe.banned_list_for_prompt(18) + "."
)


def build_messages(
    user_text: str,
    history: list[dict[str, str]],
    persona: Persona | None,
    mode: str | None,
    trend_rows: list[Any],
    playbook_ctx: str,
) -> list[dict[str, str]]:
    system = [SYSTEM_BASE]
    if persona and persona.completed:
        system.append(persona.summary())
    if mode:
        system.append(modes.RUBRICS[mode])
    if playbook_ctx:
        system.append(playbook_ctx)
    if trend_rows:
        lines = "\n".join(
            f"- [{r.platform}/{r.kind}] {r.title} (heat {r.heat:.0f})"
            + (f" — {r.detail}" if r.detail else "")
            for r in trend_rows
        )
        system.append("Current trend signals:\n" + lines)
    return [{"role": "system", "content": "\n\n".join(system)}] + history + [
        {"role": "user", "content": user_text}
    ]


async def run_turn(
    db: Session,
    user_text: str,
    history: list[dict[str, str]],
    persona: Persona | None,
    mode: str | None,
) -> tuple[str, list[Any]]:
    """Non-streaming turn. Returns (answer, trend rows used)."""
    platform = _pick_platform(user_text)
    rows = trends.query_trends(db, platform=platform, niche=persona.niche if persona else None)
    books = rag.retrieve(db, platform, user_text)
    msgs = build_messages(user_text, history, persona, mode, rows, rag.context_block(books))
    temp = modes.TEMPS.get(mode or "", 0.6)
    budget = modes.BUDGETS.get(mode or "", 2048)
    answer = await llm.complete(msgs, temperature=temp, max_tokens=budget)
    vs = cringe.scan(answer)
    if vs:
        answer += "\n\n> ⚠ filter: " + ", ".join(f'"{v.phrase}"' for v in vs) + " flagged as saturated."
    return answer, rows


async def stream_turn(
    db: Session,
    user_text: str,
    history: list[dict[str, str]],
    persona: Persona | None,
    mode: str | None,
) -> AsyncIterator[dict[str, Any]]:
    """Streaming turn. Yields events: {type: meta|trend|delta|done}."""
    platform = _pick_platform(user_text)
    rows = trends.query_trends(db, platform=platform, niche=persona.niche if persona else None)
    books = rag.retrieve(db, platform, user_text)
    msgs = build_messages(user_text, history, persona, mode, rows, rag.context_block(books))
    yield {"type": "meta", "mode": mode, "platform": platform,
           "tools": ["trend_lookup", "rag_retrieve"],
           "trends_used": [
               {"platform": r.platform, "kind": r.kind, "title": r.title, "heat": r.heat}
               for r in rows[:5]
           ]}
    temp = modes.TEMPS.get(mode or "", 0.6)
    budget = modes.BUDGETS.get(mode or "", 2048)
    collected: list[str] = []
    async for delta in llm.stream(msgs, temperature=temp, max_tokens=budget):
        collected.append(delta)
        yield {"type": "delta", "text": delta}
    # post-processing gate: scan the full answer after streaming completes
    violations = cringe.scan("".join(collected))
    if violations:
        yield {"type": "filter", "violations": cringe.violations_payload(violations)}
    yield {"type": "done"}


def _pick_platform(text: str) -> str | None:
    low = text.lower()
    if "instagram" in low or "reel" in low or "ig " in low:
        return "instagram"
    if "youtube" in low or "short" in low or "yt" in low:
        return "youtube"
    return None
