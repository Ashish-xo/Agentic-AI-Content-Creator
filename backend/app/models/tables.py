"""ORM models."""
from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

try:
    from pgvector.sqlalchemy import Vector
    _EMBEDDING_COL = Vector(384)
except ImportError:  # pgvector python pkg absent -> embedding column degrades to JSON
    _EMBEDDING_COL = JSON

from app.db.session import Base


class Persona(Base):
    __tablename__ = "personas"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    niche: Mapped[str | None] = mapped_column(Text)
    target_audience: Mapped[str | None] = mapped_column(Text)
    tone_of_voice: Mapped[str | None] = mapped_column(Text)
    content_goal: Mapped[str | None] = mapped_column(Text)
    pending_field: Mapped[str | None] = mapped_column(String(32))  # onboarding cursor
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def summary(self) -> str:
        parts = []
        if self.niche:
            parts.append(f"Niche: {self.niche}")
        if self.target_audience:
            parts.append(f"Audience: {self.target_audience}")
        if self.tone_of_voice:
            parts.append(f"Tone: {self.tone_of_voice}")
        if self.content_goal:
            parts.append(f"Goal: {self.content_goal}")
        return "; ".join(parts) if parts else "No persona set yet."


class TrendSignal(Base):
    """One attention signal scraped/seeded per platform."""

    __tablename__ = "trend_signals"
    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)  # youtube|instagram
    kind: Mapped[str] = mapped_column(String(32))  # audio|format|hashtag|search_query|thumbnail_style|hook_pattern
    title: Mapped[str] = mapped_column(Text)
    detail: Mapped[str | None] = mapped_column(Text)
    niche: Mapped[str | None] = mapped_column(String(128))  # NULL = cross-niche
    heat: Mapped[float] = mapped_column(Float, default=50.0)  # 0-100 attention score
    source: Mapped[str] = mapped_column(String(32), default="seed")  # seed|youtube_api|apify|serpapi
    captured_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class Playbook(Base):
    """Curated algorithm-strategy knowledge base (RAG floor)."""

    __tablename__ = "playbooks"
    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    topic: Mapped[str] = mapped_column(String(128))
    body: Mapped[str] = mapped_column(Text)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    niche: Mapped[str | None] = mapped_column(String(64), index=True)  # None = cross-niche
    embedding: Mapped[list[float] | None] = mapped_column(_EMBEDDING_COL)


class GeneratedItem(Base):
    """Persisted outputs: hooks, scripts, critiques, variants."""

    __tablename__ = "generated_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    kind: Mapped[str] = mapped_column(String(32))  # hook|script|critique|variant|digest
    platform: Mapped[str | None] = mapped_column(String(32))
    topic: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Project(Base):
    """Platform-switching context: one premise, per-platform variants."""

    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(256))
    premise: Mapped[str] = mapped_column(Text)
    variants: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # platform -> content
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    role: Mapped[str] = mapped_column(String(16))  # user|assistant
    content: Mapped[str] = mapped_column(Text)
    mode: Mapped[str | None] = mapped_column(String(24))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserPlan(Base):
    __tablename__ = "user_plans"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    plan: Mapped[str] = mapped_column(String(32), default="free")  # free|starter|pro|studio
    stripe_customer_id: Mapped[str | None] = mapped_column(String(128))
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(128))


class UsageEvent(Base):
    __tablename__ = "usage_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    feature: Mapped[str] = mapped_column(String(64))
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class HookExample(Base):
    """Real high-performing hooks used as dynamic few-shot examples (RAG)."""

    __tablename__ = "hook_examples"
    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    hook: Mapped[str] = mapped_column(Text)
    archetype: Mapped[str] = mapped_column(String(64))
    metric: Mapped[str | None] = mapped_column(Text)  # why it performed
    niche: Mapped[str | None] = mapped_column(String(64), index=True)  # None = cross-niche
    embedding: Mapped[list[float] | None] = mapped_column(_EMBEDDING_COL)


class UserKey(Base):
    """BYOK: per-user LLM credentials. api_key is encrypted at rest (Fernet);
    empty api_key + provider set = user opted back into the shared free engine."""

    __tablename__ = "user_keys"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(32), default="free")  # free|groq|gemini|openrouter|openai|anthropic|custom
    api_key_enc: Mapped[str | None] = mapped_column(Text)  # encrypted; never returned raw
    base_url: Mapped[str | None] = mapped_column(String(256))  # custom providers only
    model: Mapped[str | None] = mapped_column(String(128))
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
