"""FastAPI app factory."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import get_settings
from app.db.session import Base, SessionLocal, engine
from app.engine import embed_bridge, fewshot, rag
from app.engine.fewshot import seed_examples
from app.models.tables import HookExample, Playbook
from app.routes import chat, core
from app.seed.data import seed
from app.services import automation
from app.services.ratelimit import guard_http


def _index_vectors(db) -> None:
    """Attach local embeddings to seed knowledge (idempotent, non-fatal)."""
    try:
        n1 = embed_bridge.index_playbooks(db, db.query(Playbook).all())
        n2 = embed_bridge.index_hook_examples(db, db.query(HookExample).all())
        if n1 or n2:
            print(f"[embed] indexed {n1} playbooks + {n2} hook examples")
    except Exception as e:
        print(f"[embed] indexing skipped: {e} (lexical RAG still active)")
    # HNSW cosine indexes so vector search stays sub-ms as the KB grows
    # (idempotent; no-op on SQLite / when pgvector ext is absent)
    try:
        from sqlalchemy import text as sql_text
        if rag._pgvector_ready(db):
            db.execute(sql_text(
                "CREATE INDEX IF NOT EXISTS playbooks_embedding_hnsw "
                "ON playbooks USING hnsw (embedding vector_cosine_ops)"))
            db.execute(sql_text(
                "CREATE INDEX IF NOT EXISTS hook_examples_embedding_hnsw "
                "ON hook_examples USING hnsw (embedding vector_cosine_ops)"))
            db.commit()
            print("[embed] HNSW cosine indexes ensured")
    except Exception as e:
        print(f"[embed] HNSW index skipped: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        seed(db)
        seed_examples(db)
        _index_vectors(db)
    finally:
        db.close()
    automation.start(SessionLocal)
    yield


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title="Content Copilot API", version="0.1.0", lifespan=lifespan,
                  docs_url=None if s.environment == "production" else "/docs",
                  redoc_url=None, openapi_url=None if s.environment == "production" else "/openapi.json")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    # GZip JSON responses (trend lists/library shrink ~70% on 4G). SSE is left
    # raw on purpose — gzip middleware buffering would kill streaming smoothness.
    app.add_middleware(GZipMiddleware, minimum_size=864)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        from fastapi.responses import JSONResponse
        if request.url.path.startswith("/api"):
            try:
                await guard_http(request)
            except HTTPException as e:
                return JSONResponse({"detail": e.detail}, status_code=e.status_code)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response

    @app.get("/api/health")
    async def health():
        return {"ok": True, "model": s.llm_model, "environment": s.environment}

    app.include_router(chat.router)
    app.include_router(core.router)
    return app


app = create_app()
