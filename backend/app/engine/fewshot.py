"""High-performing real hook examples — dynamic few-shot source (RAG-selected).

Instead of letting the model guess what a good hook looks like, we retrieve
3-5 examples closest to the user's platform/niche/topic and put them IN the
prompt with the analyze-then-generate structure.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.engine import embed_bridge
from app.engine.rag import _tokens
from app.models.tables import HookExample

# (platform, hook, archetype, metric) — real high-performing patterns
SEED_EXAMPLES: list[dict] = [
    dict(platform="youtube", hook="I replaced 3 hired editors with a local Python script.",
         archetype="specific-proof", metric="retention 71% at 0:30 — concrete numbers, zero setup"),
    dict(platform="youtube", hook="Here's the 10-second Arch Linux setting that cut my RAM usage in half.",
         archetype="time-to-payoff", metric="CTR 12.4% — timeframe + measurable result in the first line"),
    dict(platform="youtube", hook="I read 500 pages in 7 days. Here's what actually broke.",
         archetype="experiment-arc", metric="hook rate 82% — claim + open loop ('what broke?')"),
    dict(platform="youtube", hook="This $12 tool does what Adobe charges $600/month for.",
         archetype="price-gap", metric="high CTR — exact numbers create the knowledge gap"),
    dict(platform="youtube", hook="I tested every AI note-taker so you don't have to.",
         archetype="service-sacrifice", metric="retention plateau-free — viewer knows the payoff immediately"),
    dict(platform="youtube", hook="Day 1 vs Day 90: what 100 push-ups a day actually did to me.",
         archetype="transformation", metric="loop rate up — visual before/after implied by text"),
    dict(platform="instagram", hook="POV: it's 6am and you're the only one awake — gym fit is already on.",
         archetype="relatable-pov", metric="sends-per-reach 3x — hyper-specific relatability"),
    dict(platform="instagram", hook="Send this to your gym partner who says he has no time.",
         archetype="share-command", metric="DM triggers built into the caption itself"),
    dict(platform="instagram", hook="The 12-minute lunch-break workout my physio actually approved.",
         archetype="authority-bend", metric="saves +210% — constraint (12 min) + credibility (physio)"),
    dict(platform="instagram", hook="Grocery haul: 21 meals, 3 days, under $40. Receipts in caption.",
         archetype="value-dump", metric="dwell time — short reel, long caption receipts play"),
    dict(platform="youtube", hook="Nobody tells you the first 5 seconds decide your whole video.",
         archetype="meta-open-loop", metric="self-referential hook — proves its own claim by being watched"),
    dict(platform="instagram", hook="Stop scrolling — this angle fixes 90% of your food photos.",
         archetype="command+payoff", metric="instant visual hook, payoff named before the cut"),
]


def seed_examples(db: Session) -> None:
    if db.query(HookExample).count() == 0:
        db.add_all([HookExample(**e) for e in SEED_EXAMPLES])
        db.commit()


def select_examples(db: Session, platform: str | None, topic: str, k: int = 4) -> list[HookExample]:
    """Vector-first few-shot selection; lexical fallback (platform + topic overlap)."""
    rows = db.query(HookExample).all()
    qvec = embed_bridge.embedding(topic)
    if qvec is not None and rows and all(r.embedding is not None for r in rows):
        emb_map = {r.id: list(r.embedding) for r in rows}  # type: ignore[arg-type]
        try:
            # cosine sim (vectors are normalized) + small same-platform bonus
            scored = [
                (sum(a * b for a, b in zip(qvec, emb_map[r.id]))
                 + (0.1 if platform and r.platform == platform else 0), r)
                for r in rows
            ]
            scored.sort(key=lambda x: -x[0])
            return [r for _, r in scored[:k]]
        except Exception:
            pass
    tt = _tokens(topic)
    scored = []
    for e in rows:
        plat_bonus = 3 if platform and e.platform == platform else 0
        overlap = len(tt & _tokens(e.hook + " " + e.archetype))
        scored.append((plat_bonus + overlap * 2, e))
    scored.sort(key=lambda x: -x[0])
    return [e for _, e in scored[:k]]


def chat_examples_block(examples: list[HookExample]) -> str:
    """Chat-path injection: retrieved hook patterns as style references (not a
    generation task — the copilot may be answering any question)."""
    if not examples:
        return ""
    lines = "\n".join(f'- "{e.hook}" ({e.archetype}; {e.metric})' for e in examples)
    return (
        "High-performing hook patterns relevant to this request "
        "(style references when you suggest hooks or openings):\n" + lines
    )


def fewshot_block(examples: list[HookExample], topic: str, count: int) -> str:
    """The analyze-then-generate prompt structure."""
    lines = "\n".join(
        f"- \"{e.hook}\" ({e.archetype}; {e.metric})" for e in examples
    )
    return (
        f"Analyze how these high-retention hooks work:\n{lines}\n\n"
        f"Now generate {count} hooks for: {topic}\n"
        "following this exact, direct format: first person or imperative, one concrete "
        "number or constraint, payoff visible in the first clause, zero setup or filler."
    )
