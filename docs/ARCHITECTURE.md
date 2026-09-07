# Architecture decision record

Built 2026-09-07 on this machine (cartel), ported from the session on the
other device (`/home/fev/content-copilot`, commits 5d823cf → 1c356bc → bbc25d8).

## Decisions

1. **b.ai as the LLM endpoint** (was: local Ollama qwen3:8b on the other box).
   This machine has no Ollama. b.ai exposes an OpenAI-compatible
   `/v1/chat/completions` with `qwen3.8-flash`, `glm-5.2`, `deepseek-v4-flash`
   and others; the key is already in the Hermes env
   (`HERMES_CUSTOM_API_B_AI_API_KEY`) and mirrored into `backend/.env`.
   The client strips `reasoning_content` (thinking models) and tolerates the
   final empty-`choices` SSE chunk (real crash caught in verification).

2. **Local Postgres instead of Supabase for dev.** Postgres 18.6 runs on
   :5432 here; `content_copilot` DB created. Supabase is a drop-in via
   `DATABASE_URL`. pgvector is NOT installed locally (Arch package available:
   `pacman -S pgvector`, needs the user to run it) — so RAG is lexical
   scoring over the playbook table, with the retrieve() signature kept
   stable for a later pgvector swap. b.ai has no /embeddings route
   (verified: gateway rejects it), so embeddings are not an option on this
   provider regardless.

3. **No LangGraph dependency.** The pipeline (route mode → assemble persona +
   RAG + trend context → stream) is a plain async function chain in
   `engine/graph.py`. LangGraph adds a pin-conflict surface for a linear
   graph; the stage boundaries mirror it so a later port is mechanical.
   (Deviation from the user's stated stack, deliberate, documented.)

4. **Modes are data, not code paths.** `engine/modes.py` holds rubric,
   temperature, token budget and tool bias per mode; the chat route injects
   the rubric and picks the budget. Auto-detect is keyword-scored.

5. **Onboarding intercepts chat, not a separate wizard.** Persona interview
   runs inside the conversation (4 fields, LLM-parsed free text, skip
   defaults, quick-reply chips). Single-session mutation of the persona row
   (cross-session bug from v1 is designed out).

6. **Graceful degradation everywhere.** Clerk absent → dev-user. Stripe
   absent → 503 with message. Upstash absent → in-memory limiter. Provider
   keys absent → seed trend floor. The app must fully run with only
   LLM_API_KEY set — verified.

## Verified live (this machine)

- pytest 5/5
- API boot + seed on local Postgres
- hooks JSON generation via qwen3.8-flash (archetypes + thumbnail pairings)
- full 4-question onboarding incl. LLM free-text extraction
- SSE research mode: 240 deltas, grounded in heat-scored seed signals
- creation + optimization auto-detection with persona baked into output
