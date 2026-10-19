"""Viral discovery — live search of YouTube for what's blowing up in a niche.

Keyless via yt-dlp (no API key). Strategy per platform:

youtube: yt-dlp search with freshness+duration filters, full extraction of the
top N results for exact timestamps -> velocity scoring (views/day since
publish). The shortlist is deliberately small: deep-extraction costs ~1
request per video.

instagram: Instagram login-walls anonymous scraping of feeds/explore/tags, so
there is NO reliable keyless discovery. Honest design: the scanner accepts
user-supplied reel URLs (from their own feed or saved posts), deep-extracts
real view/like/comment counts via yt-dlp, and velocity-scores them the same
way. Discovery there needs either (a) logged-in cookies, or (b) Apify — both
already supported by config: pass cookies via YT_DLP_COOKIES or set APIFY_TOKEN.

Heat formula: min(99, 50 + vpd/1000) where vpd = views per day since publish.
A 50k-views 2-day-old video (~25k/day) scores ~75; a 5M-views year-old video
(~14k/day) scores ~64. Recency wins — that's the point.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import urllib.parse

from sqlalchemy.orm import Session

from app.models.tables import TrendSignal

# YouTube search filter: upload month + duration <4min, relevance order
_SP_SHORT_MONTH = "CAMSBAgDEAE%3D"


def _heat(views_per_day: float) -> float:
    return min(99.0, 50 + views_per_day / 1000)


def _scan_sync(query: str, limit: int) -> list[dict]:
    """Blocking yt-dlp scan — runs inside a worker thread."""
    from yt_dlp import YoutubeDL

    now = dt.datetime.now(dt.timezone.utc)
    q = urllib.parse.quote(query)
    opts = {
        "quiet": True, "no_warnings": True, "skip_download": True,
        "playlist_items": f"1-{limit}",
        "socket_timeout": 20,
    }
    out: list[dict] = []
    with YoutubeDL(opts) as ydl:
        r = ydl.extract_info(
            f"https://www.youtube.com/results?search_query={q}&sp={_SP_SHORT_MONTH}",
            download=False,
        )
    for it in (r or {}).get("entries", []):
        if not it or not it.get("timestamp"):
            continue
        age = max(0.2, (now - dt.datetime.fromtimestamp(it["timestamp"], dt.timezone.utc)).total_seconds() / 86400)
        vc = it.get("view_count") or 0
        vpd = vc / age
        out.append({
            "title": (it.get("title") or "")[:180],
            "channel": it.get("channel") or "",
            "views": vc,
            "age_days": round(age, 1),
            "views_per_day": round(vpd),
            "heat": round(_heat(vpd), 1),
            "url": it.get("url") or f"https://www.youtube.com/watch?v={it.get('id', '')}",
            "duration_s": it.get("duration"),
        })
    out.sort(key=lambda x: -x["views_per_day"])
    return out


async def scan_youtube(query: str, limit: int = 6) -> list[dict]:
    """Search + score currently-viral short-form YouTube videos for a niche query."""
    if not query.strip():
        return []
    return await asyncio.to_thread(_scan_sync, query.strip()[:200], limit)


async def scan_instagram(urls: list[str]) -> list[dict]:
    """Score user-supplied Instagram reel URLs (login-walled discovery is impossible
    keyless — see module docstring). Real engagement numbers via yt-dlp."""
    from yt_dlp import YoutubeDL

    now = dt.datetime.now(dt.timezone.utc)

    def one(url: str) -> dict | None:
        try:
            with YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as ydl:
                it = ydl.extract_info(url, download=False)
            if not it:
                return None
            ts = it.get("timestamp")
            age = max(0.2, (now - dt.datetime.fromtimestamp(ts, dt.timezone.utc)).total_seconds() / 86400) if ts else 14.0
            vc = it.get("view_count") or 0
            return {
                "title": (it.get("title") or it.get("description") or "")[:180],
                "channel": it.get("channel") or it.get("uploader") or "",
                "views": vc,
                "likes": it.get("like_count"),
                "comments": it.get("comment_count"),
                "age_days": round(age, 1),
                "views_per_day": round(vc / age),
                "heat": round(_heat(vc / age), 1),
                "url": url,
            }
        except Exception:
            return None

    results = await asyncio.gather(*(asyncio.to_thread(one, u) for u in urls[:10]))
    rows = [r for r in results if r]
    rows.sort(key=lambda x: -x["views_per_day"])
    return rows


async def refresh_viral(db: Session, niches: list[str]) -> int:
    """Run viral scans for the given niche queries and store them as trend signals.
    Returns how many new signals were stored."""
    n = 0
    for niche in niches:
        try:
            rows = await scan_youtube(niche, limit=6)
        except Exception as e:
            print(f"[viral] scan '{niche}' failed: {e}")
            continue
        for row in rows:
            exists = (
                db.query(TrendSignal)
                .filter(TrendSignal.source == "viral_yt", TrendSignal.title == row["title"])
                .first()
            )
            if exists:
                exists.heat = max(exists.heat, row["heat"])
                continue
            db.add(TrendSignal(
                platform="youtube", kind="viral_video",
                title=row["title"],
                detail=(f"{row['views']:,} views in {row['age_days']}d "
                        f"({row['views_per_day']:,}/day) — {row['channel']} | {row['url']}"),
                heat=row["heat"], source="viral_yt",
            ))
            n += 1
    db.commit()
    return n
