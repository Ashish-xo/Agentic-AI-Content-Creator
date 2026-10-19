"""Anonymous visitor identity — signed cookies with an IP+UA fallback.

When auth is off (dev / no Clerk), every visitor still gets a stable,
tamper-proof identity so rate limits and BYOK keys attach to *them*, not to a
shared "dev-user". The cookie value is `<id>.<hmac>` — forging an id requires
the server secret. If cookies are blocked, identity degrades to a hash of
client IP + User-Agent (same protection, weaker persistence).

Real authentication (Clerk JWT) overrides this entirely when enabled.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets

from fastapi import Request, Response

COOKIE = "cc_vid"
MAX_AGE = 60 * 60 * 24 * 365


def _secret() -> bytes:
    s = get_settings()
    if s.session_secret:
        return s.session_secret.encode()
    # dev fallback: derive from BYOK master (also file-backed) — stable across restarts
    from app.services.byok import _SECRET_PATH  # local import avoids cycle
    raw = _SECRET_PATH.read_text().strip() if _SECRET_PATH.exists() else "dev-insecure"
    return hashlib.sha256(("cc-session:" + raw).encode()).digest()


from app.core.config import get_settings  # noqa: E402  (after helper to avoid cycle)


def _sign(vid: str) -> str:
    return hmac.new(_secret(), vid.encode(), hashlib.sha256).hexdigest()[:32]


def _fingerprint(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
    ua = request.headers.get("user-agent", "")[:200]
    raw = f"{ip}|{ua}"
    return "ip-" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def resolve(request: Request) -> str:
    """Read the visitor id from the request (cookie -> signed verify -> fingerprint).
    Stashes the id + whether a fresh cookie must be set on request.state."""
    raw = request.cookies.get(COOKIE, "")
    if raw and "." in raw:
        vid, sig = raw.rsplit(".", 1)
        if hmac.compare_digest(sig, _sign(vid)) and vid.startswith("v-"):
            request.state.vid = vid
            request.state.vid_set = False
            return vid
    # missing or tampered -> fingerprint for THIS request; new cookie after
    vid = _fingerprint(request)
    request.state.vid = vid
    request.state.vid_new = secrets.token_hex(8)  # random id to mint
    request.state.vid_set = True
    return vid


def attach(response: Response, request: Request) -> None:
    """Set the cookie when this request minted a new identity."""
    if getattr(request.state, "vid_set", False):
        new_id = "v-" + request.state.vid_new
        response.set_cookie(
            COOKIE, f"{new_id}.{_sign(new_id)}",
            max_age=MAX_AGE, httponly=True, samesite="lax",
            secure=get_settings().environment == "production",
        )


def current(request: Request) -> str:
    """The identity this request acts as (cookie id or IP fingerprint)."""
    return getattr(request.state, "vid", None) or _fingerprint(request)
