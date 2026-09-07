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


chat_limit = Limiter(30)
http_limit = Limiter(120)


async def guard_http(request: Request) -> None:
    user = request.headers.get("x-user-id", "anon")
    await http_limit.check(f"http:{user}")
