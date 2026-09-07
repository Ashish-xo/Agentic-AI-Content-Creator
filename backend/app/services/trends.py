"""Trend data layer — provider adapters over the curated seed floor.

Adapters: YouTube Data API v3, Apify, SerpAPI. Each activates only when its
key exists; otherwise the seed table answers. Heat scores are 0-100.
"""
from __future__ import annotations

import httpx
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.tables import TrendSignal


async def refresh_youtube(db: Session) -> int:
    """YouTube Data API v3: most-viewed Shorts-region videos -> search-query signals."""
    s = get_settings()
    if not s.youtube_api_key:
        return 0
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {"part": "snippet,statistics", "chart": "mostPopular", "maxResults": 25,
              "videoDuration": "short", "key": s.youtube_api_key}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        items = r.json().get("items", [])
    n = 0
    for it in items:
        sn = it.get("snippet", {})
        views = int(it.get("statistics", {}).get("viewCount", 0) or 0)
        heat = min(99.0, 50 + views / 2_000_000)
        exists = (
            db.query(TrendSignal)
            .filter(TrendSignal.source == "youtube_api", TrendSignal.title == sn.get("title", "")[:200])
            .first()
        )
        if exists:
            exists.heat = max(exists.heat, heat)
            continue
        db.add(TrendSignal(
            platform="youtube", kind="search_query",
            title=(sn.get("title") or "")[:200],
            detail=f"channel: {sn.get('channelTitle','')}",
            heat=heat, source="youtube_api",
        ))
        n += 1
    db.commit()
    return n


async def refresh_apify(db: Session) -> int:
    """Apify Instagram Reels scraper -> trending audio/format signals (paid actor)."""
    s = get_settings()
    if not s.apify_token:
        return 0
    url = "https://api.apify.com/v2/acts/compass~crawler-instagram-reels/runs-sync"
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(f"{url}?token={s.apify_token}", json={
            "resultsSource": "explore", "maxItemsPerCrawl": 20})
        r.raise_for_status()
        dataset = r.json().get("defaultDataset", {})
    n = 0
    items_url = f"https://api.apify.com/v2/datasets/{dataset.get('id','')}/items?token={s.apify_token}"
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(items_url)
        if r.status_code == 200:
            for it in r.json()[:20]:
                title = (it.get("caption") or it.get("fullUrl") or "")[:200]
                if not title:
                    continue
                db.add(TrendSignal(
                    platform="instagram", kind="format", title=title,
                    detail=f"likes={it.get('likesCount', 0)}",
                    heat=min(99.0, 50 + int(it.get("likesCount", 0) or 0) / 50_000),
                    source="apify",
                ))
                n += 1
    db.commit()
    return n


async def refresh_serpapi(db: Session) -> int:
    """SerpAPI Google Trends -> rising query signals."""
    s = get_settings()
    if not s.serpapi_key:
        return 0
    url = "https://serpapi.com/search.json"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, params={"engine": "google_trends_trending_now",
                                          "geo": "US", "api_key": s.serpapi_key})
        r.raise_for_status()
        trends = r.json().get("trending_searches", [])
    n = 0
    for t in trends[:15]:
        q = (t.get("query") or "")[:200]
        if not q or db.query(TrendSignal).filter(TrendSignal.source == "serpapi",
                                                 TrendSignal.title == q).first():
            continue
        db.add(TrendSignal(platform="cross", kind="search_query", title=q,
                           detail=f"traffic: {t.get('traffic','')}", heat=75.0, source="serpapi"))
        n += 1
    db.commit()
    return n


async def refresh_all(db: Session) -> dict[str, int]:
    out = {}
    for name, fn in (("youtube_api", refresh_youtube), ("apify", refresh_apify), ("serpapi", refresh_serpapi)):
        try:
            out[name] = await fn(db)
        except Exception as e:  # provider down must never break the app
            out[name] = -1
            print(f"[trends] {name} refresh failed: {e}")
    return out


def query_trends(
    db: Session,
    platform: str | None = None,
    niche: str | None = None,
    limit: int = 12,
) -> list[TrendSignal]:
    q = db.query(TrendSignal)
    if platform and platform != "all":
        q = q.filter(TrendSignal.platform.in_([platform, "cross"]))
    q = q.order_by(desc(TrendSignal.heat))
    rows = q.limit(200).all()
    if niche:
        # soft-boost: signals whose text overlaps the niche words
        words = {w.lower() for w in niche.split() if len(w) > 3}
        rows.sort(
            key=lambda r: r.heat
            + (10 if words & set((r.title + " " + (r.detail or "")).lower().split()) else 0),
            reverse=True,
        )
    return rows[:limit]
