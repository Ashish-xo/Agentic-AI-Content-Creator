# Content Copilot

Algorithm-aware AI content copilot for YouTube + Instagram creators.
Four layers: data aggregation → intelligence (RAG + modes) → platform-switching
context (projects/variants) → conversational interface (streaming chat).

## Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 15 + Tailwind (shadcn-style dark UI) |
| Backend | Python FastAPI (uv-managed venv) |
| Database | PostgreSQL (local dev; Supabase in prod) |
| LLM | b.ai OpenAI-compatible endpoint — `qwen3.8-flash` default, `glm-5.2` preset |
| Auth | Clerk JWT (dev fallback: fixed `dev-user`) |
| Billing | Stripe subscriptions (503s clearly until keys set) |
| Rate limit | Upstash Redis when configured, in-memory sliding window fallback |
| Data | YouTube Data API v3 / Apify / SerpAPI adapters over a curated seed floor |
| Automation | APScheduler: 6h trend refresh + daily persona-aware digest |

## Run

```bash
# API (port 8787)
cd backend && cp .env.example .env   # add LLM_API_KEY (b.ai)
uv sync && uv run uvicorn app.main:app --port 8787

# Web (port 3000, proxies /api -> 8787)
cd web && npm install && npm run dev   # or npm run build && npm start
```

Open http://localhost:3000 — first chat visit runs the 4-question persona
interview, then use the Research / Creation / Optimization chips.

## Layout

```
backend/app/
  core/       config, auth (Clerk JWT + dev fallback)
  db/         SQLAlchemy engine/session
  models/     tables: personas, trend_signals, playbooks, generated_items,
              projects, chat_messages, user_plans, usage_events
  engine/     graph (pipeline), modes, onboarding, generators, rag
  services/   llm (b.ai client, SSE + JSON mode), trends (adapters),
              ratelimit, billing, automation (scheduler)
  routes/     chat (SSE), core (trends/generate/projects/persona/digest/settings/billing)
  seed/       playbooks + initial trend signals
web/src/app/  landing, dashboard, chat, trends, generate, projects, settings
```

## API

- `POST /api/chat/stream` — SSE copilot (`{message, mode, history}`)
- `POST /api/chat` — non-streaming variant
- `GET /api/chat/history`
- `GET /api/trends` · `POST /api/trends/refresh`
- `POST /api/generate/{hooks,script,critique,variants}` · `GET /api/library`
- `GET /api/projects[/{id}]`
- `GET/PUT /api/persona` · `POST /api/persona/reset`
- `GET /api/digest/latest` · `GET /api/settings`
- `GET /api/billing/config` · `POST /api/billing/checkout` · `POST /api/billing/webhook`

## Going to production

1. Supabase: set `DATABASE_URL` to the pooled Postgres connection string;
   enable the `vector` extension and swap `engine/rag.py` retrieve() for a
   pgvector cosine query (signature is stable).
2. Clerk: create the app, set `CLERK_SECRET_KEY`, wire `@clerk/nextjs` in web
   (~10 lines) and send the bearer token; pin audience/azp in `core/auth.py`.
3. Stripe: create products, set both keys, replace the inline price creation
   with dashboard Price IDs.
4. Upstash / Apify / SerpAPI / YouTube keys → `.env`. Everything degrades
   gracefully without them.

Honest gaps before public launch: plan quotas are defined (`PLAN_LIMITS`) but
not enforced per-route yet; JWT `verify_aud` is off; no HTTPS at app layer
(terminate at proxy).
