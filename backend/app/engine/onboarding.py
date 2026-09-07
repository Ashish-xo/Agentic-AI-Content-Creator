"""Conversational persona onboarding: 4-question interview inside the chat.

Flow: niche -> target_audience -> tone_of_voice -> content_goal -> done.
Free-text answers are parsed by the LLM into the current field (with a
raw-text fallback); 'skip' applies a sensible default.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.tables import Persona
from app.services import llm

FIELDS = ["niche", "target_audience", "tone_of_voice", "content_goal"]

QUESTIONS: dict[str, str] = {
    "niche": "What do you make content about?",
    "target_audience": "Who is it for?",
    "tone_of_voice": "How should I sound when I write for you?",
    "content_goal": "What's the main goal right now?",
}

QUICK_REPLIES: dict[str, list[str]] = {
    "niche": ["Fitness", "Personal finance", "Tech & AI", "Food", "Gaming"],
    "target_audience": ["Gen Z", "Young professionals", "Parents", "Beginners in my niche"],
    "tone_of_voice": ["Casual & funny", "Bold & direct", "Calm & educational", "Inspirational"],
    "content_goal": ["Grow followers", "Get sales", "Build authority", "Have fun"],
}

DEFAULTS = {
    "niche": "general lifestyle",
    "target_audience": "a broad general audience",
    "tone_of_voice": "casual and friendly",
    "content_goal": "grow an audience",
}

LABELS = {
    "niche": "content niche",
    "target_audience": "target audience",
    "tone_of_voice": "tone of voice",
    "content_goal": "content goal",
}


def get_or_create(db: Session, user_id: str) -> Persona:
    p = db.query(Persona).filter(Persona.user_id == user_id).first()
    if not p:
        p = Persona(user_id=user_id, pending_field="niche")
        db.add(p)
        db.commit()
    return p


def next_question(persona: Persona) -> str | None:
    if persona.completed or not persona.pending_field:
        return None
    return QUESTIONS[persona.pending_field]


async def _parse_answer(field: str, answer: str) -> str:
    answer = answer.strip()
    if answer.lower() in {"skip", "s", "-", "idk", "dont know", "don't know"}:
        return DEFAULTS[field]
    try:
        text = await llm.complete(
            [
                {
                    "role": "system",
                    "content": (
                        f"Extract the creator's {LABELS[field]} from their answer. "
                        "Reply with ONLY the extracted value as a short phrase (under 15 words). "
                        "If the answer is unrelated, reply with the answer cleaned up."
                    ),
                },
                {"role": "user", "content": answer},
            ],
            temperature=0.1,
            max_tokens=80,
        )
        return text.strip().strip('"') or answer
    except Exception:
        return answer


def advance(db: Session, persona: Persona, answer: str) -> tuple[str | None, bool]:
    """Store the answer for the pending field, move the cursor.

    Returns (next_question_or_None, just_completed). Single session for all
    mutations (cross-session mutation was a real bug in v1).
    """
    field = persona.pending_field
    if field not in FIELDS:
        return None, False
    setattr(persona, field, answer)
    idx = FIELDS.index(field)
    if idx + 1 < len(FIELDS):
        nxt = FIELDS[idx + 1]
        persona.pending_field = nxt
        db.commit()
        return QUESTIONS[nxt], False
    persona.pending_field = None
    persona.completed = True
    db.commit()
    return None, True


async def handle_answer(db: Session, user_id: str, answer: str) -> tuple[str | None, bool]:
    persona = get_or_create(db, user_id)
    parsed = await _parse_answer(persona.pending_field or "niche", answer)
    return advance(db, persona, parsed)
