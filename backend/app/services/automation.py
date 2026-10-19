"""Automation: APScheduler trend refresh + persona-aware daily digest."""
from __future__ import annotations

import datetime as dt

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session

from app.engine import generators
from app.models.tables import GeneratedItem, Persona
from app.services import llm, trends

scheduler = AsyncIOScheduler()


def start(db_factory) -> None:
    # next_run_time=now => fires at boot, then on schedule (run_on_start is NOT a
    # valid trigger arg — that was a real crash in v1).
    scheduler.add_job(
        _refresh, IntervalTrigger(hours=6), args=[db_factory],
        next_run_time=dt.datetime.now(), id="trend_refresh",
    )
    scheduler.add_job(
        _digest, IntervalTrigger(hours=24), args=[db_factory],
        next_run_time=dt.datetime.now() + dt.timedelta(hours=1), id="daily_digest",
    )
    scheduler.start()


async def _refresh(db_factory) -> None:
    db: Session = db_factory()
    try:
        await trends.refresh_all(db)
        # viral discovery: scan the distinct niches users actually create in
        niches = [r[0] for r in db.query(Persona.niche).filter(
            Persona.niche.isnot(None)).distinct().limit(5).all() if r[0] and isinstance(r[0], str)]
        if niches:
            from app.services import viral_scan
            added = await viral_scan.refresh_viral(db, niches)
            print(f"[viral] +{added} signals from {len(niches)} niche(s)")
    finally:
        db.close()


async def _digest(db_factory) -> None:
    db: Session = db_factory()
    try:
        personas = db.query(Persona).filter(Persona.completed.is_(True)).all()
        for p in personas:
            top = trends.query_trends(db, niche=p.niche, limit=5)
            lines = "\n".join(f"- [{r.platform}] {r.title} (heat {r.heat:.0f})" for r in top)
            try:
                body = await llm.complete(
                    [
                        {"role": "system", "content":
                            "Write a 5-line daily content-opportunity digest for this creator. "
                            f"Persona: {p.summary()}. Use only the trend data given. Plain markdown."},
                        {"role": "user", "content": f"Today's signals:\n{lines}"},
                    ],
                    temperature=0.5, max_tokens=512,
                )
                db.add(GeneratedItem(user_id=p.user_id, kind="digest", platform=None,
                                     topic="daily digest", payload={"body": body}))
                db.commit()
            except Exception as e:
                print(f"[digest] {p.user_id} failed: {e}")
    finally:
        db.close()
