"""Embedding helpers shared by seed-time indexing and query-time retrieval.

Kept as a thin bridge so engine/ modules don't import services directly and
SQLite (no pgvector) never breaks at import time.
"""
from __future__ import annotations

from app.services.embed import embedding, embeddings

__all__ = ["embedding", "embeddings", "index_playbooks", "index_hook_examples"]


def index_playbooks(db, rows) -> int:
    """Attach embeddings to playbook rows that lack them. Returns count."""
    todo = [r for r in rows if r.embedding is None]
    if not todo:
        return 0
    vecs = embeddings([f"{r.topic}. {r.body}" for r in todo])
    if not vecs:
        return 0
    for r, v in zip(todo, vecs):
        r.embedding = v
    db.commit()
    return len(vecs)


def index_hook_examples(db, rows) -> int:
    todo = [r for r in rows if r.embedding is None]
    if not todo:
        return 0
    vecs = embeddings([f"{r.hook} ({r.archetype})" for r in todo])
    if not vecs:
        return 0
    for r, v in zip(todo, vecs):
        r.embedding = v
    db.commit()
    return len(vecs)
