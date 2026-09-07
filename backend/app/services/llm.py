"""LLM client — one interface over any OpenAI-compatible endpoint.

Presets: b.ai (qwen3.8-flash / glm-5.2 / deepseek-v4-flash). Reasoning models
return a `reasoning_content` field alongside `content` — we only surface
`content`. JSON mode = prompt instruction + robust ```-fence / brace extraction.
"""
from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import get_settings

MODEL_PRESETS = {
    "qwen3.8-flash": {"label": "Qwen 3.8 Flash (b.ai)", "fast": True},
    "glm-5.2": {"label": "GLM 5.2 (b.ai)", "fast": False},
    "deepseek-v4-flash": {"label": "DeepSeek V4 Flash (b.ai)", "fast": True},
}


def _headers() -> dict[str, str]:
    s = get_settings()
    return {"Authorization": f"Bearer {s.llm_api_key}", "Content-Type": "application/json"}


def _url() -> str:
    base = get_settings().llm_base_url.strip().rstrip("/")
    if not base.endswith("/v1"):
        base += "/v1"
    return base


async def complete(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> str:
    payload = {
        "model": model or get_settings().llm_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.post(f"{_url()}/chat/completions", headers=_headers(), json=payload)
        r.raise_for_status()
        data = r.json()
    msg = data["choices"][0]["message"]
    return (msg.get("content") or "").strip()


async def stream(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> AsyncIterator[str]:
    """Yield text deltas. Only `content` deltas — reasoning is dropped."""
    payload = {
        "model": model or get_settings().llm_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=300) as client:
        async with client.stream(
            "POST", f"{_url()}/chat/completions", headers=_headers(), json=payload
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                chunk = line[5:].strip()
                if chunk == "[DONE]":
                    return
                try:
                    obj: dict[str, Any] = json.loads(chunk)
                except json.JSONDecodeError:
                    continue
                choices = obj.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta", {}) or {}
                text = delta.get("content")
                if text:
                    yield text


_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json(text: str) -> Any:
    """Parse a JSON object/array out of an LLM reply (fences, prose, thinking tags)."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    m = _FENCE.search(text)
    if m:
        text = m.group(1)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for opener, closer in (("[", "]"), ("{", "}")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    # last resort: earliest valid JSON value anywhere in the text
    dec = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch in "{[":
            try:
                obj, _ = dec.raw_decode(text[i:])
                return obj
            except json.JSONDecodeError:
                continue
    raise ValueError(f"No JSON found in LLM reply: {text[:200]!r}")


async def complete_json(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.4,
    max_tokens: int = 2048,
    retries: int = 1,
) -> Any:
    """Ask for JSON, parse defensively, retry once on parse failure."""
    last_text = ""
    for attempt in range(retries + 1):
        text = await complete(messages, model=model, temperature=temperature, max_tokens=max_tokens)
        last_text = text
        try:
            return extract_json(text)
        except ValueError:
            if attempt < retries:
                messages = messages + [
                    {"role": "assistant", "content": text[:1000]},
                    {"role": "user", "content": "Return ONLY valid JSON, no prose, no fences."},
                ]
    raise ValueError(f"LLM did not return parseable JSON: {last_text[:300]!r}")
