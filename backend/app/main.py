"""FastAPI app factory."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.session import Base, SessionLocal, engine
from app.engine import fewshot
from app.routes import chat, core
from app.seed.data import seed
from app.services import automation
from app.services.ratelimit import guard_http


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        seed(db)
        fewshot.seed_examples(db)
    finally:
        db.close()
    automation.start(SessionLocal)
    yield


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title="Content Copilot API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def rate_guard(request: Request, call_next):
        if request.url.path.startswith("/api"):
            await guard_http(request)
        return await call_next(request)

    @app.get("/api/health")
    async def health():
        return {"ok": True, "model": s.llm_model, "environment": s.environment}

    app.include_router(chat.router)
    app.include_router(core.router)
    return app


app = create_app()
