"""RAG retrieval over the playbook knowledge base.

Vector-first: pgvector cosine similarity when embeddings exist (local
all-MiniLM-L6-v2 model + Postgres pgvector ext). Lexical scoring is the
permanent fallback — SQLite tests, missing extension, or embed failures.
"""
from __future__ import annotations

from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.engine import embed_bridge
from app.models.tables import Playbook

_STOP = {"the", "and", "for", "with", "that", "this", "your", "how", "what", "why", "who",
         "are", "can", "does", "into", "about", "want", "make", "make.", "please"}


def _tokens(text: str) -> set[str]:
    return {w.strip(".,!?;:()\"'").lower() for w in text.split()} - {""} - _STOP


def _lexical(rows: list[Playbook], query: str, k: int) -> list[Playbook]:
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


def retrieve(db: Session, platform: str | None, query: str, k: int = 3) -> list[Playbook]:
    scope = [platform, "cross"] if platform else None
    # vector path (Postgres + pgvector + embeddings present)
    qvec = embed_bridge.embedding(query)
    if qvec is not None and _pgvector_ready(db):
        try:
            params = {"qvec": str(qvec), "k": k}
            if scope:
                params["scope"] = scope
                sql = sql_text(
                    "SELECT id FROM playbooks WHERE platform = ANY(:scope) "
                    "AND embedding IS NOT NULL "
                    "ORDER BY embedding <=> CAST(:qvec AS vector) LIMIT :k")
            else:
                sql = sql_text(
                    "SELECT id FROM playbooks WHERE embedding IS NOT NULL "
                    "ORDER BY embedding <=> CAST(:qvec AS vector) LIMIT :k")
            ids = [r[0] for r in db.execute(sql, params).fetchall()]
            if ids:
                rows = {p.id: p for p in db.query(Playbook).filter(Playbook.id.in_(ids)).all()}
                return [rows[i] for i in ids if i in rows]
        except Exception as e:
            print(f"[rag] vector search failed ({e}) — lexical fallback")
    # lexical fallback
    q = db.query(Playbook)
    if scope:
        q = q.filter(Playbook.platform.in_(scope))
    return _lexical(q.all(), query, k)


_vector_ok: bool | None = None


def _pgvector_ready(db: Session) -> bool:
    global _vector_ok
    if _vector_ok is None:
        try:
            _vector_ok = db.execute(
                sql_text("SELECT 1 FROM pg_extension WHERE extname='vector'")).first() is not None
        except Exception:
            _vector_ok = False
    return _vector_ok


def context_block(playbooks: list[Playbook]) -> str:
    if not playbooks:
        return ""
    parts = ["Relevant algorithm strategy notes:\n"]
    for pb in playbooks:
        parts.append(f"- [{pb.platform}/{pb.topic}] {pb.body}\n")
    return "\n".join(parts)
