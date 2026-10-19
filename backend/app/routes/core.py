"""Remaining API routes: trends, generate, projects, persona, digest, settings, billing."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.engine import generators, onboarding
from app.models.tables import GeneratedItem, Persona, Project, UserKey
from app.services import billing, byok, trends
from app.services.ratelimit import gen_limit

router = APIRouter(tags=["core"])


# ---------- trends ----------
@router.get("/api/trends")
def get_trends(platform: str | None = None, limit: int = 12,
               user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    persona = db.query(Persona).filter(Persona.user_id == user_id).first()
    rows = trends.query_trends(db, platform=platform, niche=persona.niche if persona else None,
                               limit=limit)
    return [{"platform": r.platform, "kind": r.kind, "title": r.title, "detail": r.detail,
             "heat": r.heat, "source": r.source, "captured_at": r.captured_at.isoformat()}
            for r in rows]


# ---------- viral discovery (live search) ----------
class ViralScanIn(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    limit: int = Field(default=6, ge=1, le=10)


class ViralIgIn(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=10)


@router.post("/api/viral/scan")
async def viral_scan(body: ViralScanIn, user_id: str = Depends(current_user),
                     db: Session = Depends(get_db)):
    """Live keyless YouTube search: freshest short-form videos for a niche,
    velocity-scored (views/day). Also stored as trend signals for the RAG layer."""
    from app.services import viral_scan
    from app.services.ratelimit import gen_limit

    await gen_limit.check(f"viral:{user_id}")
    rows = await viral_scan.scan_youtube(body.query, limit=body.limit)
    await viral_scan.refresh_viral(db, [body.query]) if rows else None
    return {"query": body.query, "results": rows}


@router.post("/api/viral/instagram")
async def viral_instagram(body: ViralIgIn, user_id: str = Depends(current_user)):
    """Score user-supplied Instagram reel URLs (IG blocks keyless discovery —
    this verifies real numbers on reels you already have)."""
    from app.services import viral_scan
    from app.services.ratelimit import gen_limit

    await gen_limit.check(f"viral:{user_id}")
    rows = await viral_scan.scan_instagram(body.urls)
    return {"results": rows}


@router.post("/api/trends/refresh")
async def refresh_trends(user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    return await trends.refresh_all(db)


# ---------- generation ----------
class HookIn(BaseModel):
    topic: str = Field(min_length=1, max_length=2000)
    platform: str = "youtube"
    count: int = Field(default=3, ge=1, le=10)


class ScriptIn(BaseModel):
    topic: str = Field(min_length=1, max_length=2000)
    platform: str = "youtube"
    seconds: int = Field(default=30, ge=5, le=600)


class CritiqueIn(BaseModel):
    draft: str = Field(min_length=1, max_length=20000)
    platform: str = "instagram"


class VariantIn(BaseModel):
    premise: str = Field(min_length=1, max_length=4000)
    project_name: str | None = Field(default=None, max_length=200)


@router.post("/api/generate/hooks")
async def gen_hooks(body: HookIn, user_id: str = Depends(current_user),
                   db: Session = Depends(get_db)):
    await gen_limit.check(f"gen:{user_id}")
    persona = db.query(Persona).filter(Persona.user_id == user_id).first()
    out = await generators.generate_hooks(body.topic, body.platform, body.count,
                                          persona.summary() if persona and persona.completed else None,
                                          db=db, user_id=user_id)
    db.add(GeneratedItem(user_id=user_id, kind="hook", platform=body.platform,
                         topic=body.topic, payload=out))
    db.commit()
    return out


@router.post("/api/generate/script")
async def gen_script(body: ScriptIn, user_id: str = Depends(current_user),
                     db: Session = Depends(get_db)):
    await gen_limit.check(f"gen:{user_id}")
    persona = db.query(Persona).filter(Persona.user_id == user_id).first()
    script = await generators.generate_script(body.topic, body.platform, body.seconds,
                                              persona.summary() if persona and persona.completed else None,
                                              db=db, user_id=user_id)
    db.add(GeneratedItem(user_id=user_id, kind="script", platform=body.platform,
                         topic=body.topic, payload=script))
    db.commit()
    return script


@router.post("/api/generate/critique")
async def gen_critique(body: CritiqueIn, user_id: str = Depends(current_user),
                       db: Session = Depends(get_db)):
    await gen_limit.check(f"gen:{user_id}")
    persona = db.query(Persona).filter(Persona.user_id == user_id).first()
    out = await generators.critique_content(body.draft, body.platform,
                                            persona.summary() if persona and persona.completed else None,
                                            db=db, user_id=user_id)
    db.add(GeneratedItem(user_id=user_id, kind="critique", platform=body.platform,
                         topic=body.draft[:80], payload=out))
    db.commit()
    return out


@router.post("/api/generate/variants")
async def gen_variants(body: VariantIn, user_id: str = Depends(current_user),
                       db: Session = Depends(get_db)):
    """Platform-switching: one premise -> per-platform variants, saved as a project."""
    await gen_limit.check(f"gen:{user_id}")
    persona = db.query(Persona).filter(Persona.user_id == user_id).first()
    variants = await generators.make_variants(body.premise,
                                              persona.summary() if persona and persona.completed else None,
                                              db=db, user_id=user_id)
    proj = Project(user_id=user_id, name=body.project_name or body.premise[:60],
                   premise=body.premise, variants=variants)
    db.add(proj)
    db.commit()
    return {"project_id": proj.id, "variants": variants}


@router.get("/api/library")
def library(kind: str | None = None, user_id: str = Depends(current_user),
            db: Session = Depends(get_db), limit: int = 30):
    q = db.query(GeneratedItem).filter(GeneratedItem.user_id == user_id)
    if kind:
        q = q.filter(GeneratedItem.kind == kind)
    rows = q.order_by(desc(GeneratedItem.id)).limit(limit).all()
    return [{"id": r.id, "kind": r.kind, "platform": r.platform, "topic": r.topic,
             "payload": r.payload, "created_at": r.created_at.isoformat()} for r in rows]


# ---------- projects ----------
@router.get("/api/projects")
def list_projects(user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(Project).filter(Project.user_id == user_id).order_by(desc(Project.id)).all()
    return [{"id": r.id, "name": r.name, "premise": r.premise, "variants": r.variants,
             "updated_at": r.updated_at.isoformat()} for r in rows]


@router.get("/api/projects/{project_id}")
def get_project(project_id: int, user_id: str = Depends(current_user),
                db: Session = Depends(get_db)):
    r = db.query(Project).filter(Project.id == project_id, Project.user_id == user_id).first()
    if not r:
        from fastapi import HTTPException
        raise HTTPException(404, "Project not found")
    return {"id": r.id, "name": r.name, "premise": r.premise, "variants": r.variants}


# ---------- persona ----------
class PersonaIn(BaseModel):
    niche: str | None = Field(default=None, max_length=500)
    target_audience: str | None = Field(default=None, max_length=500)
    tone_of_voice: str | None = Field(default=None, max_length=500)
    content_goal: str | None = Field(default=None, max_length=500)


@router.get("/api/persona")
def get_persona(user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    p = onboarding.get_or_create(db, user_id)
    return {"niche": p.niche, "target_audience": p.target_audience,
            "tone_of_voice": p.tone_of_voice, "content_goal": p.content_goal,
            "completed": p.completed, "pending_field": p.pending_field,
            "quick_replies": onboarding.QUICK_REPLIES}


@router.put("/api/persona")
def put_persona(body: PersonaIn, user_id: str = Depends(current_user),
                db: Session = Depends(get_db)):
    p = onboarding.get_or_create(db, user_id)
    for f in onboarding.FIELDS:
        v = getattr(body, f)
        if v:
            setattr(p, f, v)
    missing = [f for f in onboarding.FIELDS if not getattr(p, f)]
    p.completed = not missing
    p.pending_field = missing[0] if missing else None
    db.commit()
    return {"completed": p.completed, "pending_field": p.pending_field}


@router.post("/api/persona/reset")
def reset_persona(user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    p = onboarding.get_or_create(db, user_id)
    for f in onboarding.FIELDS:
        setattr(p, f, None)
    p.completed = False
    p.pending_field = "niche"
    db.commit()
    return {"ok": True}


# ---------- digest ----------
@router.get("/api/digest/latest")
def latest_digest(user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    row = (db.query(GeneratedItem)
           .filter(GeneratedItem.user_id == user_id, GeneratedItem.kind == "digest")
           .order_by(desc(GeneratedItem.id)).first())
    if not row:
        return {"body": None}
    return {"body": row.payload.get("body"), "created_at": row.created_at.isoformat()}


# ---------- BYOK: per-user LLM credentials ----------
class ByokIn(BaseModel):
    provider: str = Field(pattern="^(free|groq|gemini|openrouter|openai|custom)$")
    api_key: str | None = Field(default=None, max_length=400)
    base_url: str | None = Field(default=None, max_length=256)
    model: str | None = Field(default=None, max_length=128)


@router.get("/api/llm-key")
def get_llm_key(user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    """Masked view of the user's BYOK config — the raw key never leaves the server."""
    row = byok.get_user_key(db, user_id)
    if not row:
        return {"provider": "free", "api_key_preview": None, "base_url": None,
                "model": byok.PROVIDERS["free"]["model"], "label": byok.PROVIDERS["free"]["label"]}
    key_preview = None
    if row.api_key_enc:
        try:
            key_preview = byok.mask_key(byok.decrypt_key(row.api_key_enc))
        except RuntimeError:
            key_preview = "unreadable"
    preset = byok.PROVIDERS.get(row.provider, byok.PROVIDERS["custom"])
    return {"provider": row.provider, "api_key_preview": key_preview,
            "base_url": row.base_url, "model": row.model or preset["model"],
            "label": preset["label"]}


@router.put("/api/llm-key")
def put_llm_key(body: ByokIn, user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    row = byok.get_user_key(db, user_id)
    if not row:
        row = UserKey(user_id=user_id)
        db.add(row)
    row.provider = body.provider
    if body.provider == "free":
        row.api_key_enc = None
        row.base_url = None
        row.model = None
    else:
        if body.api_key:  # only overwrite when a new key is supplied
            row.api_key_enc = byok.encrypt_key(body.api_key)
        if body.provider == "custom":
            if not body.base_url or not body.model:
                from fastapi import HTTPException
                raise HTTPException(422, "Custom provider needs base_url and model")
            row.base_url = body.base_url
            row.model = body.model
        else:
            preset = byok.PROVIDERS[body.provider]
            row.base_url = None  # preset URL applies
            row.model = body.model or preset["model"]
    db.commit()
    return {"ok": True, "provider": row.provider}


@router.delete("/api/llm-key")
def delete_llm_key(user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    row = byok.get_user_key(db, user_id)
    if row:
        db.delete(row)
        db.commit()
    return {"ok": True, "provider": "free"}


# ---------- settings / billing ----------
@router.get("/api/settings")
def settings_view(user_id: str = Depends(current_user)):
    s = get_settings()
    return {
        "llm_model": s.llm_model,
        "providers": {
            "clerk_auth": bool(s.clerk_secret_key),
            "stripe_billing": s.billing_enabled,
            "upstash": bool(s.upstash_redis_url),
            "youtube_api": bool(s.youtube_api_key),
            "apify": bool(s.apify_token),
            "serpapi": bool(s.serpapi_key),
        },
        "environment": s.environment,
    }


@router.get("/api/billing/config")
def billing_config(db: Session = Depends(get_db), user_id: str = Depends(current_user)):
    s = get_settings()
    return {"configured": s.billing_enabled, "plans": billing.PLANS,
            "current_plan": billing.get_plan(db, user_id)}


@router.post("/api/billing/checkout")
async def billing_checkout(plan: str, user_id: str = Depends(current_user),
                           db: Session = Depends(get_db)):
    return await billing.create_checkout(db, user_id, plan)


@router.post("/api/billing/webhook")
async def billing_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    await billing.handle_webhook(db, payload, request.headers.get("stripe-signature", ""))
    return {"received": True}
