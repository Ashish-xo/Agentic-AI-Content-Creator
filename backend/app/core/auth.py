"""Auth: Clerk JWT verification with a dev-mode fallback identity.

Enforced when production or CLERK_SECRET_KEY is set; otherwise a fixed
'dev-user' keeps the app zero-config. The gate can never silently open in prod.
"""
from __future__ import annotations

import time

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt

from app.core.config import get_settings

_bearer = HTTPBearer(auto_error=False)
_jwks_cache: tuple[float, dict] = (0.0, {})
_JWKS_URL_TMPL = "https://{iss}/.well-known/jwks.json"


async def _get_jwks(issuer: str) -> dict:
    global _jwks_cache
    now = time.time()
    if _jwks_cache[1] and now - _jwks_cache[0] < 3600:
        return _jwks_cache[1]
    url = _JWKS_URL_TMPL.format(issuer.removeprefix("https://").removeprefix("http://"))
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url)
        r.raise_for_status()
        _jwks_cache = (now, r.json())
    return _jwks_cache[1]


async def _verify_jwt(token: str) -> str:
    try:
        header = jwt.get_unverified_header(token)
        claims = jwt.decode(token, key="", options={"verify_signature": False})
        issuer = claims.get("iss", "")
        jwks = await _get_jwks(issuer)
        kid = header.get("kid")
        key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), jwks)
        decoded = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=None,
            options={"verify_aud": False},  # NOTE: pin Clerk azp at real launch
        )
        sub = decoded.get("sub")
        if not sub:
            raise HTTPException(401, "Token missing sub")
        return str(sub)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(401, "Invalid token")


async def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    s = get_settings()
    if not s.auth_enabled:
        return "dev-user"
    if not creds:
        raise HTTPException(401, "Not authenticated")
    return await _verify_jwt(creds.credentials)
