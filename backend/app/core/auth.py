"""Auth: Clerk JWT verification with a dev-mode fallback identity.

Enforced when production or CLERK_SECRET_KEY is set; otherwise a fixed
'dev-user' keeps the app zero-config. The gate can never silently open in prod.

Security model (audited 2026-09-08):
- The `iss` claim is NEVER trusted from the token itself for fetching keys.
  Only a fixed allowlist (Clerk domains) or the operator-set CLERK_ISSUER env
  may be contacted, and the resolved IP must be public (no SSRF to 127.x/10.x/
  192.168.x/169.254.x etc).
- The JWKS key must match the token's `kid` exactly — no fallback to "use the
  whole keyset", which let mismatched keys slip through.
"""
from __future__ import annotations

import ipaddress
import re
import socket
import time

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt

from app.core.config import get_settings

_bearer = HTTPBearer(auto_error=False)
_JWKS_URL_TMPL = "https://{issuer}/.well-known/jwks.json"
_TTL = 3600.0
_jwks_cache: dict[str, tuple[float, dict]] = {}

# Clerk-hosted issuers look like https://<instance>.clerk.accounts.dev or a
# custom domain under clerk.com. Anything else must come via CLERK_ISSUER.
_ALLOWED_ISSUER_RE = re.compile(
    r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*\.clerk\.(accounts\.dev|com)$"
)


def _issuer_allowed(iss: str) -> bool:
    """True only for https Clerk domains (or the exact operator-configured
    issuer) whose DNS resolves to a public IP."""
    if not iss or any(c in iss for c in ("\n", "\r", "@", "?", "#", "/", ":", "\\")) or " " in iss:
        return False
    s = get_settings()
    if s.clerk_issuer:
        if iss != s.clerk_issuer.removeprefix("https://").removeprefix("http://"):
            return False
    elif not _ALLOWED_ISSUER_RE.match(iss):
        return False
    try:
        infos = socket.getaddrinfo(iss, 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return False
    for family, _, _, _, sockaddr in infos:
        ip = ipaddress.ip_address(sockaddr[0])
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
            ip = ip.ipv4_mapped
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            return False
    return True


async def _get_jwks(issuer: str) -> dict:
    if not _issuer_allowed(issuer):
        raise HTTPException(401, "Untrusted token issuer")
    now = time.time()
    hit = _jwks_cache.get(issuer)
    if hit and now - hit[0] < _TTL:
        return hit[1]
    url = _JWKS_URL_TMPL.format(issuer=issuer)
    async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
        r = await client.get(url)
        r.raise_for_status()
        data = r.json()
    if not isinstance(data, dict) or not isinstance(data.get("keys"), list):
        raise HTTPException(401, "Malformed JWKS")
    _jwks_cache[issuer] = (now, data)
    return data


async def _verify_jwt(token: str) -> str:
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") != "RS256" or header.get("typ") not in (None, "JWT"):
            raise HTTPException(401, "Unexpected token header")
        claims = jwt.decode(token, key="", options={"verify_signature": False})
        issuer = str(claims.get("iss", ""))
        # strip scheme only for display; allowlist check works on the host part
        host = re.sub(r"^https?://", "", issuer).strip("/")
        jwks = await _get_jwks(host)
        kid = header.get("kid")
        key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if key is None:
            raise HTTPException(401, "Unknown signing key")
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
