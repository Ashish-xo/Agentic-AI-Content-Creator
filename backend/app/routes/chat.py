"""Chat route: SSE streaming copilot with onboarding intercept + mode dispatch."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.db.session import get_db
from app.engine import cringe, graph, modes, onboarding
from app.models.tables import ChatMessage
from app.services.ratelimit import chat_limit

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatIn(BaseModel):
    message: str
    mode: str | None = None  # research|creation|optimization|auto|None
    history: list[dict[str, str]] = []


def _resolve_mode(mode: str | None, message: str) -> str | None:
    if mode and mode in modes.MODES:
        return mode
    if mode == "auto" or not mode:
        return modes.detect_mode(message)
    return None


@router.post("/stream")
async def chat_stream(
    body: ChatIn,
    user_id: str = Depends(current_user),
    db: Session = Depends(get_db),
):
    await chat_limit.check(f"chat:{user_id}")
    persona = onboarding.get_or_create(db, user_id)

    async def event_gen():
        def sse(obj: dict) -> str:
            return f"data: {json.dumps(obj)}\n\n"

        # --- onboarding intercept: unfinished persona runs the interview ---
        if not persona.completed:
            q = onboarding.next_question(persona)
            if q:
                answer = body.message
                db.add(ChatMessage(user_id=user_id, role="user", content=answer, mode="onboarding"))
                nxt, done = await onboarding.handle_answer(db, user_id, answer)
                reply = (
                    "Persona saved — I'll write for you with that in mind from now on."
                    if done
                    else nxt or "What do you make content about?"
                )
                db.add(ChatMessage(user_id=user_id, role="assistant", content=reply, mode="onboarding"))
                db.commit()
                yield sse({"type": "onboarding", "done": done,
                           "progress": [f for f in onboarding.FIELDS if getattr(persona, f)]})
                yield sse({"type": "delta", "text": reply})
                yield sse({"type": "done"})
                return

        # --- normal copilot turn ---
        mode = _resolve_mode(body.mode, body.message)
        history = [{"role": h.get("role", "user"), "content": h.get("content", "")[:4000]}
                   for h in body.history[-8:] if h.get("content")]
        db.add(ChatMessage(user_id=user_id, role="user", content=body.message, mode=mode))
        db.commit()
        collected: list[str] = []
        try:
            async for ev in graph.stream_turn(db, body.message, history, persona, mode):
                if ev["type"] == "delta":
                    collected.append(ev["text"])
                yield sse(ev)
        except Exception as e:
            yield sse({"type": "error", "detail": str(e)[:300]})
            collected.append("(the model endpoint had a hiccup — try again)")
        answer = "".join(collected)
        if answer:
            db.add(ChatMessage(user_id=user_id, role="assistant", content=answer, mode=mode))
            db.commit()

    return StreamingResponse(event_gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("")
async def chat_once(
    body: ChatIn,
    user_id: str = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Non-streaming variant (tests + simple clients)."""
    await chat_limit.check(f"chat:{user_id}")
    persona = onboarding.get_or_create(db, user_id)
    if not persona.completed:
        nxt, done = await onboarding.handle_answer(db, user_id, body.message)
        return {"answer": ("Persona saved." if done else nxt), "onboarding": True, "done": done}
    mode = _resolve_mode(body.mode, body.message)
    history = [{"role": h.get("role", "user"), "content": h.get("content", "")[:4000]}
               for h in body.history[-8:] if h.get("content")]
    answer, rows = await graph.run_turn(db, body.message, history, persona, mode)
    return {"answer": answer, "mode": mode,
            "trends_used": [{"platform": r.platform, "title": r.title, "heat": r.heat} for r in rows[:5]]}


@router.get("/history")
async def chat_history(user_id: str = Depends(current_user), db: Session = Depends(get_db),
                       limit: int = 50):
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.id.desc())
        .limit(limit)
        .all()
    )
    return list(reversed([{"role": r.role, "content": r.content, "mode": r.mode,
                           "ts": r.created_at.isoformat()} for r in rows]))
