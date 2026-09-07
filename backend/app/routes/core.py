"""Remaining API routes: trends, generate, projects, persona, digest, settings, billing."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.auth import current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.engine import generators, onboarding
from app.models.tables import GeneratedItem, Persona, Project
from app.services import billing, trends

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


@router.post("/api/trends/refresh")
async def refresh_trends(user_id: str = Depends(current_user), db: Session = Depends(get_db)):
    return await trends.refresh_all(db)


# ---------- generation ----------
class HookIn(BaseModel):
    topic: str
    platform: str = "youtube"
    count: int = 3


class ScriptIn(BaseModel):
    topic: str
    platform: str = "youtube"
    seconds: int = 30


class CritiqueIn(BaseModel):
    draft: str
    platform: str = "instagram"


class VariantIn(BaseModel):
    premise: str
    project_name: str | None = None


@router.post("/api/generate/hooks")
async def gen_hooks(body: HookIn, user_id: str = Depends(current_user),
                   db: Session = Depends(get_db)):
    persona = db.query(Persona).filter(Persona.user_id == user_id).first()
    items = await generators.generate_hooks(body.topic, body.platform, body.count,
                                            persona.summary() if persona and persona.completed else None)
    db.add(GeneratedItem(user_id=user_id, kind="hook", platform=body.platform,
                         topic=body.topic, payload={"hooks": items}))
    db.commit()
    return {"hooks": items}


@router.post("/api/generate/script")
async def gen_script(body: ScriptIn, user_id: str = Depends(current_user),
                     db: Session = Depends(get_db)):
    persona = db.query(Persona).filter(Persona.user_id == user_id).first()
    script = await generators.generate_script(body.topic, body.platform, body.seconds,
                                              persona.summary() if persona and persona.completed else None)
    db.add(GeneratedItem(user_id=user_id, kind="script", platform=body.platform,
                         topic=body.topic, payload=script))
    db.commit()
    return script


@router.post("/api/generate/critique")
async def gen_critique(body: CritiqueIn, user_id: str = Depends(current_user),
                       db: Session = Depends(get_db)):
    persona = db.query(Persona).filter(Persona.user_id == user_id).first()
    out = await generators.critique_content(body.draft, body.platform,
                                            persona.summary() if persona and persona.completed else None)
    db.add(GeneratedItem(user_id=user_id, kind="critique", platform=body.platform,
                         topic=body.draft[:80], payload=out))
    db.commit()
    return out


@router.post("/api/generate/variants")
async def gen_variants(body: VariantIn, user_id: str = Depends(current_user),
                       db: Session = Depends(get_db)):
    """Platform-switching: one premise -> per-platform variants, saved as a project."""
    persona = db.query(Persona).filter(Persona.user_id == user_id).first()
    variants = await generators.make_variants(body.premise,
                                              persona.summary() if persona and persona.completed else None)
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
    niche: str | None = None
    target_audience: str | None = None
    tone_of_voice: str | None = None
    content_goal: str | None = None


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
