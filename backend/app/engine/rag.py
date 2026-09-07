"""RAG retrieval over the playbook knowledge base.

Lexical scoring (keyword overlap + topic match) — the b.ai endpoint exposes no
embeddings route, so this is the honest floor. In prod with Supabase+pgvector,
swap `retrieve` for a cosine-similarity query; the call signature stays stable.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.tables import Playbook

_STOP = {"the", "and", "for", "with", "that", "this", "your", "how", "what", "why", "who",
         "are", "can", "does", "into", "about", "want", "make", "make.", "please"}


def _tokens(text: str) -> set[str]:
    return {w.strip(".,!?;:()\"'").lower() for w in text.split()} - {""} - _STOP


def retrieve(db: Session, platform: str | None, query: str, k: int = 3) -> list[Playbook]:
    q = db.query(Playbook)
    if platform:
        q = q.filter(Playbook.platform.in_([platform, "cross"]))
    rows = q.all()
    qt = _tokens(query)
    scored = []
    for pb in rows:
        st = _tokens(pb.topic + " " + " ".join(pb.keywords or []))
        overlap = len(qt & st)
        topic_bonus = 2 if any(w in pb.topic.lower() for w in qt if len(w) > 4) else 0
        scored.append((overlap * 2 + topic_bonus, pb))
    scored.sort(key=lambda x: -x[0])
    hits = [pb for score, pb in scored[:k] if score > 0]
    return hits or [pb for _, pb in scored[:k]]


def context_block(playbooks: list[Playbook]) -> str:
    if not playbooks:
        return ""
    parts = ["Relevant algorithm strategy notes:\n"]
    for pb in playbooks:
        parts.append(f"- [{pb.platform}/{pb.topic}] {pb.body}\n")
    return "\n".join(parts)
