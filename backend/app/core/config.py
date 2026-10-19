"""Central configuration — env-only secrets, graceful no-key dev mode."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    port: int = 8787
    database_url: str = "postgresql+psycopg://postgres@localhost:5432/content_copilot"

    # LLM (OpenAI-compatible endpoint)
    llm_base_url: str = "https://text.pollinations.ai/openai/v1"
    llm_api_key: str = ""
    llm_model: str = "openai"

    # BYOK — Fernet master key for encrypting user-supplied API keys at rest
    byok_secret: str = ""

    # Visitor identity — HMAC secret for signed anonymous cookies (dev auth-off mode)
    session_secret: str = ""

    # Auth — Clerk
    clerk_secret_key: str = ""
    clerk_issuer: str = ""  # optional exact expected iss (custom domain); empty = Clerk-domain allowlist
    # Billing — Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    # Rate limiting — Upstash
    upstash_redis_url: str = ""
    upstash_redis_token: str = ""
    # Data providers
    youtube_api_key: str = ""
    apify_token: str = ""
    serpapi_key: str = ""
    trends_geo: str = "US"  # Google Trends RSS region

    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def auth_enabled(self) -> bool:
        return self.environment == "production" or bool(self.clerk_secret_key)

    @property
    def billing_enabled(self) -> bool:
        return bool(self.stripe_secret_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
