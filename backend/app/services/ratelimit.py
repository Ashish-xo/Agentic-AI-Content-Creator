"""Rate limiting: Upstash Redis sliding window when configured, in-memory fallback.

Every check records per-identity state (count, window, retry-after) so the app
can *detect* and *display* whether a visitor is currently rate limited — see
`snapshot()` / `/api/me`."""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.core.config import get_settings

_windows: dict[str, deque[float]] = defaultdict(deque)
# identity -> {"limit": int, "count": int, "window_reset": epoch, "blocked_until": epoch}
_state: dict[str, dict] = {}
_STATE_TTL = 300.0  # forget idle identities after 5 min


def _prune_state(now: float) -> None:
    dead = [k for k, v in _state.items() if now - v.get("last_seen", 0) > _STATE_TTL]
    for k in dead:
        _state.pop(k, None)


class Limiter:
    def __init__(self, per_minute: int):
        self.per_minute = per_minute

    async def check(self, key: str) -> None:
        s = get_settings()
        if s.upstash_redis_url and s.upstash_redis_token:
            ok, retry_after = await self._upstash(s, key)
        else:
            ok, retry_after = self._local(key)
        if not ok:
            raise HTTPException(429, {
                "error": "rate_limited",
                "message": "Rate limit exceeded — slow down.",
                "retry_after": round(retry_after, 1),
                "limit": self.per_minute,
            })

    def _record(self, key: str, count: int, window_start: float, blocked_until: float = 0.0) -> None:
        now = time.time()
        _prune_state(now)
        st = _state.setdefault(key, {})
        st.update(limit=self.per_minute, count=count,
                  window_reset=window_start + 60, blocked_until=blocked_until, last_seen=now)

    def _local(self, key: str) -> tuple[bool, float]:
        now = time.time()
        w = _windows[key]
        while w and now - w[0] > 60:
            w.popleft()
        if len(w) >= self.per_minute:
            retry_after = 60 - (now - w[0])
            self._record(key, len(w), w[0] if w else now, blocked_until=now + retry_after)
            return False, retry_after
        w.append(now)
        self._record(key, len(w), w[0] if w else now)
        return True, 0.0

    async def _upstash(self, s, key: str) -> tuple[bool, float]:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.post(
                    s.upstash_redis_url,
                    headers={"Authorization": f"Bearer {s.upstash_redis_token}"},
                    json=["rl", key, "1", "60"],  # ratelimit sliding window cmd
                )
                data = r.json()
                ok = bool(data.get("remaining", 0) >= 0) if isinstance(data, dict) else True
                reset = float(data.get("reset", 0)) if isinstance(data, dict) else 0
                self._record(key, self.per_minute - int(data.get("remaining", 0)) if isinstance(data, dict) else 0, time.time())
                return ok, max(0.0, reset - time.time())
        except Exception:
            return self._local(key)  # Redis down -> local guard still applies


chat_limit = Limiter(30)      # BYOK users — their key, their quota
free_chat_limit = Limiter(8)  # free-engine users — protects the shared Pollinations tier
http_limit = Limiter(120)
gen_limit = Limiter(10)       # generate/critique/variants — heavier prompts per call


async def chat_limit_for(db, user_id: str) -> None:
    """BYOK users get the standard budget; free-engine users a stricter one."""
    from app.services import byok

    row = byok.get_user_key(db, user_id)
    if row and row.provider and row.provider != "free":
        await chat_limit.check(f"chat:{user_id}")
    else:
        await free_chat_limit.check(f"chat:{user_id}")


def snapshot(user_id: str) -> dict:
    """Current rate-limit state for an identity (for /api/me + UI badges)."""
    st = _state.get(f"chat:{user_id}")
    if not st:
        return {"limited": False}
    now = time.time()
    blocked = now < st.get("blocked_until", 0)
    return {
        "limited": blocked,
        "count": st["count"],
        "limit": st["limit"],
        "window_reset": round(max(0.0, st["window_reset"] - now), 1),
        "retry_after": round(max(0.0, st["blocked_until"] - now), 1) if blocked else 0,
    }


def peer_identity(request: Request) -> str:
    """Stable identity for middleware-level (IP) limits."""
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")


async def guard_http(request: Request) -> None:
    # Key on client IP, not a spoofable header. Behind a reverse proxy,
    # X-Forwarded-For's leftmost hop is the client (uvicorn --proxy-headers
    # also normalizes request.client.host).
    await http_limit.check(f"http:{peer_identity(request)}")
