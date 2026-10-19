"""BYOK — per-user LLM credentials.

Providers are OpenAI-compatible presets (Groq / Gemini / OpenRouter / OpenAI /
Anthropic / custom). Keys are encrypted at rest with Fernet; the master key
lives in BYOK_SECRET (auto-generated once to backend/.byok_secret if unset).
The raw key is NEVER returned by any endpoint — only a masked preview.
Resolution order for a request: user's BYOK > global .env default (free).
"""
from __future__ import annotations

import base64
import secrets
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.tables import UserKey

# OpenAI-compatible endpoints. Anthropic is listed but needs its own dialect —
# excluded from the picker until a translate layer exists; keep for future.
PROVIDERS: dict[str, dict[str, str | None]] = {
    "free": {"base_url": None, "model": None, "label": "Free (Pollinations)", "needs_key": False},
    "groq": {"base_url": "https://api.groq.com/openai/v1", "model": "llama-3.3-70b-versatile",
             "label": "Groq (free tier, fast)", "needs_key": True},
    "gemini": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
               "model": "gemini-2.0-flash", "label": "Google Gemini (free tier)", "needs_key": True},
    "openrouter": {"base_url": "https://openrouter.ai/api/v1", "model": "meta-llama/llama-3.3-70b-instruct:free",
                   "label": "OpenRouter (any model)", "needs_key": True},
    "openai": {"base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini",
               "label": "OpenAI (paid)", "needs_key": True},
    "custom": {"base_url": None, "model": None, "label": "Custom OpenAI-compatible", "needs_key": True},
}

_SECRET_PATH = Path(__file__).resolve().parents[2] / ".byok_secret"


def _fernet() -> Fernet:
    s = get_settings()
    secret = (s.byok_secret or "").strip()
    if not secret:
        if _SECRET_PATH.exists():
            secret = _SECRET_PATH.read_text().strip()
        else:
            secret = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
            _SECRET_PATH.write_text(secret)
            _SECRET_PATH.chmod(0o600)
    try:
        return Fernet(secret.encode())
    except (ValueError, TypeError) as e:
        raise RuntimeError(f"BYOK_SECRET is not a valid Fernet key: {e}") from e


def encrypt_key(raw: str) -> str:
    return _fernet().encrypt(raw.encode()).decode()


def decrypt_key(enc: str) -> str:
    try:
        return _fernet().decrypt(enc.encode()).decode()
    except InvalidToken as e:
        raise RuntimeError("Stored key cannot be decrypted — BYOK_SECRET changed?") from e


def mask_key(raw: str) -> str:
    if len(raw) <= 8:
        return "••••"
    return f"{raw[:4]}••••{raw[-4:]}"


def get_user_key(db: Session, user_id: str) -> UserKey | None:
    return db.query(UserKey).filter(UserKey.user_id == user_id).first()


def llm_credentials(db: Session, user_id: str) -> dict:
    """Resolve the effective LLM credentials for a request.
    Returns {base_url, api_key, model, source} — BYOK wins over global default."""
    s = get_settings()
    row = get_user_key(db, user_id)
    if row and row.provider and row.provider != "free":
        preset = PROVIDERS.get(row.provider, PROVIDERS["custom"])
        key = decrypt_key(row.api_key_enc) if row.api_key_enc else ""
        return {
            "base_url": row.base_url or preset["base_url"] or s.llm_base_url,
            "api_key": key,
            "model": row.model or preset["model"] or s.llm_model,
            "source": row.provider,
        }
    # free / unset — global .env default (keyless Pollinations)
    return {"base_url": s.llm_base_url, "api_key": s.llm_api_key,
            "model": s.llm_model, "source": "free"}
