# Agentic AI Content Creator

An algorithm-aware AI content copilot for YouTube and Instagram creators.
Instead of generic writing advice, it reasons about platform mechanics — hook rate,
retention curves, thumbnail CTR, DM-share triggers, reel-to-caption ratios — and
grounds every suggestion in real attention signals.

## What the chatbot does

**It interviews you first.** The first conversation is a 4-question persona setup —
niche, audience, tone, goal — parsed from free text by the LLM. Everything generated
afterwards is written *for you*.

**It works in three modes** (pick a chip or let auto-detection route your message):

- 🔍 **Research** — "what's going viral this week." Answers grounded in heat-scored
  trend signals (audio, formats, hashtags, queries) ranked by algorithm favor.
- ✍️ **Creation** — "write 3 hooks and a 30-second script." Hooks come with named
  archetypes, rationale, and thumbnail pairings; scripts come block-timed.
- 📈 **Optimization** — "critique my draft to increase shares." Quotes the weak phrase,
  explains the failure, shows the fix, scores before/after.

**It learns from real winners, not vibes.** Hook generation uses dynamic few-shot
prompting: 3–5 real high-performing examples closest to your topic are retrieved (RAG)
and placed inside the prompt — "analyze how these high-retention hooks work, now
generate in this exact, direct format" — so output inherits proven structure.

**It refuses to sound like AI.** Every output passes a saturation filter — a
post-processing gate that rejects cringe/AI-slop phrases ("game-changer", "feels
illegal to know", hype emoji) before they reach the UI, with a rewrite pass when too
many drafts fail.

**It switches platforms for you.** One premise in → per-platform executions out:
YouTube long-form outline, Short script, Reel with first-frame direction and share CTA.

**It runs while you sleep.** A scheduler refreshes trend signals every 6h and writes a
persona-aware daily digest of content opportunities.

## Stack

Next.js 15 + Tailwind · FastAPI · PostgreSQL (Supabase-ready) · b.ai LLM endpoint
(qwen3.8-flash / glm-5.2) · Clerk auth · Stripe billing · Upstash rate limiting.
Everything degrades gracefully without cloud keys — the app runs fully with only an
LLM API key. See README.md and docs/ARCHITECTURE.md.
