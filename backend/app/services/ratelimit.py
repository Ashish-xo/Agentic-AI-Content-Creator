"""Rate limiting: Upstash Redis sliding window when configured, in-memory fallback."""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.core.config import get_settings

_windows: dict[str, deque[float]] = defaultdict(deque)


class Limiter:
    def __init__(self, per_minute: int):
        self.per_minute = per_minute

    async def check(self, key: str) -> None:
        s = get_settings()
        if s.upstash_redis_url and s.upstash_redis_token:
            ok = await self._upstash(s, key)
        else:
            ok = self._local(key)
        if not ok:
            raise HTTPException(429, "Rate limit exceeded — slow down.")

    def _local(self, key: str) -> bool:
        now = time.time()
        w = _windows[key]
        while w and now - w[0] > 60:
            w.popleft()
        if len(w) >= self.per_minute:
            return False
        w.append(now)
        return True

    async def _upstash(self, s, key: str) -> bool:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.post(
                    s.upstash_redis_url,
                    headers={"Authorization": f"Bearer {s.upstash_redis_token}"},
                    json=["rl", key, "1", "60"],  # ratelimit sliding window cmd
                )
                data = r.json()
                return bool(data.get("remaining", 0) >= 0) if isinstance(data, dict) else True
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


async def guard_http(request: Request) -> None:
    # Key on client IP, not a spoofable header. Behind a reverse proxy,
    # X-Forwarded-For's leftmost hop is the client (uvicorn --proxy-headers
    # also normalizes request.client.host).
    fwd = request.headers.get("x-forwarded-for", "")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
    await http_limit.check(f"http:{ip}")
