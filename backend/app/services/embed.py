"""Local sentence embeddings for the pgvector layer.

Model: all-MiniLM-L6-v2 (~90MB, runs comfortably on this 7GB box). Embeddings
are computed locally — no provider embedding API needed (b.ai has none).
If sentence-transformers is unavailable, embedding() returns None and RAG
falls back to lexical scoring, so the app never hard-depends on this.
"""
from __future__ import annotations

import threading
from functools import lru_cache

_model = None
_lock = threading.Lock()
DIM = 384


@lru_cache(maxsize=1)
def _get_model():
    global _model
    with _lock:
        if _model is None:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _model


def embedding(text: str) -> list[float] | None:
    try:
        return [float(x) for x in _get_model().encode(text, normalize_embeddings=True)]
    except Exception as e:
        print(f"[embed] unavailable ({e}) — RAG will use lexical fallback")
        return None


def embeddings(texts: list[str]) -> list[list[float]] | None:
    try:
        return [[float(x) for x in row] for row in
                _get_model().encode(texts, normalize_embeddings=True)]
    except Exception as e:
        print(f"[embed] unavailable ({e})")
        return None
