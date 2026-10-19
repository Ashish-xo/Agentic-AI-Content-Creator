"""Curated seed data: algorithm playbooks (RAG floor) + initial trend signals.

Real providers (YouTube Data API v3 / Apify / SerpAPI) layer on top of this
floor when keys exist; without keys the app is fully functional on seed data.

Niche tags: playbooks/hook-examples carrying `niche` labels are niche-locked —
strict retrieval only serves them to matching niches. Cross-niche items
(generic platform strategy) have niche=None and serve everyone.
"""
from sqlalchemy.orm import Session

from app.models.tables import Playbook, TrendSignal

PLAYBOOKS: list[dict] = [
    dict(
        platform="youtube",
        topic="Hook rate (first 5 seconds)",
        body=(
            "The first 5 seconds decide the video. State the payoff or the tension immediately — "
            "no logos, no 'hey guys'. Best openers: a bold claim ('this tool replaces editors'), "
            "an open loop ('nobody tells you this about Shorts'), or a visual pattern interrupt "
            "(mid-action shot). Measure success as % of viewers still present at 0:05; under 70% "
            "means rewrite the cold open, not the thumbnail."
        ),
        keywords=["hook", "intro", "first 5 seconds", "retention", "cold open"],
    ),
    dict(
        platform="youtube",
        topic="Viewer retention curves",
        body=(
            "Retention dips cluster at topic switches and energy plateaus. Re-hook every 20-30s "
            "with a mini cliffhanger ('but here's where it gets weird'). Steepest recoverable dip "
            "is the 30-60s band — put the strongest B-roll or proof point there. Long-tail retention "
            "(>60%) at the end signals loop-worthy content, which YouTube rewards with impressions."
        ),
        keywords=["retention", "curve", "watch time", "re-hook", "drop-off"],
    ),
    dict(
        platform="youtube",
        topic="High-CTR thumbnail styles",
        body=(
            "Thumbnails that win: one dominant face with strong emotion, max 3-4 words of text that "
            "complement (never repeat) the title, high contrast against the platform's white/dark UI, "
            "and a visible knowledge gap ('before/after', arrow to the unexpected thing). Test title "
            "+ thumbnail as a pair: the title asks, the image teases the answer."
        ),
        keywords=["thumbnail", "ctr", "click through", "title"],
    ),
    dict(
        platform="youtube",
        topic="Search intent optimization",
        body=(
            "YouTube is the second search engine. Match query intent types: informational ('how to X') "
            "wants chaptered tutorials with the answer in the first 30s; navigational comparisons "
            "('a vs b') want verdicts early; transactional ('best X 2026') want lists with timestamps. "
            "Put the exact query phrase in title, first spoken line, and description's first 2 lines."
        ),
        keywords=["seo", "search", "intent", "keywords", "ranking"],
    ),
    dict(
        platform="youtube",
        topic="Shorts audio & formats",
        body=(
            "Shorts ride trending audio: a clip using an ascending-trend sound gets discovery boost in "
            "its first 24h. Winning formats: 3-part listicles at 25-35s, single-payoff jokes under 15s "
            "(loop rate matters — the last frame should flow into the first), and 'POV' text-overlay "
            "skits. Post the same hook across 2-3 format variants and keep the winner."
        ),
        keywords=["shorts", "audio", "trending", "loop", "format"],
    ),
    dict(
        platform="instagram",
        topic="Instant visual hook & watch-time loops",
        body=(
            "Reels are judged in under 1.5s — the first frame must contain motion or a face, never a "
            "static title card. Loop engineering: end the caption/visual mid-sentence so the replay "
            "hides the cut; watch-time >100% is the strongest single ranking signal for Reels reach."
        ),
        keywords=["hook", "reel", "loop", "watch time", "first frame"],
    ),
    dict(
        platform="instagram",
        topic="DM-share triggers",
        body=(
            "Sends-per-reach now outweighs likes. Build 'send this to...' moments: hyper-specific "
            "relatability ('send this to your gym partner'), useful-save triggers (checklists, "
            "presets, price comparisons), and mild controversy stated as an opinion, not a fact. "
            "One explicit share CTA in caption or on-screen text lifts sends 2-4x."
        ),
        keywords=["dm", "share", "sends", "viral", "trigger", "caption cta"],
    ),
    dict(
        platform="instagram",
        topic="Trending audio identification",
        body=(
            "Trending audio carries a rising-arrow badge in the Reels audio browser and typically "
            "peaks 3-10 days after entering the top 50. Use audio under 5k uses that is accelerating "
            "rather than saturated mega-sounds. Mute-friendly creators: keep original audio as a layer "
            "so the trend tag still applies."
        ),
        keywords=["audio", "trending", "music", "rising"],
    ),
    dict(
        platform="instagram",
        topic="Reel-to-caption length ratios",
        body=(
            "Short reel (under 15s) + long caption = dwell time on the post while reading, which "
            "counts as engagement. Long reel (30s+) + one-line caption. Rule of thumb: caption adds "
            "what the video can't (the list, the recipe, the receipts) — never summarize the video."
        ),
        keywords=["caption", "ratio", "length", "dwell"],
    ),
    dict(
        platform="instagram",
        topic="Negative hooks & listicle formats",
        body=(
            "Structural patterns that repeat in top niche posts: negative hook ('stop doing X'), "
            "curiosity gap listicle ('3 tools that feel illegal to know'), transformation arc "
            "(day 1 vs day 90), and contrarian take ('unpopular opinion'). Rotate archetypes; "
            "the same archetype twice in a row under-performs for the same audience."
        ),
        keywords=["listicle", "negative hook", "pattern", "structure", "storytelling arc"],
    ),
    dict(
        platform="cross",
        topic="Cross-platform repurposing",
        body=(
            "One premise, three executions: YouTube long-form = the proof and depth; Short = the "
            "single strongest claim with a link-out; Reel = the visual/relatable angle with a "
            "share CTA. Never port a Short to Reels with the watermark — reach is penalized. "
            "Re-time the hook per platform: YT viewers tolerate 5s setups, Reels viewers do not."
        ),
        keywords=["repurpose", "cross-platform", "variant", "adapt"],
    ),
    # ---- niche-locked playbooks (strict retrieval serves these only to the matching niche) ----
    dict(
        platform="cross", niche="software",
        topic="Coding tutorial hooks: the bug-first cold open",
        body=(
            "Dev audiences bail on intros — open with the broken thing: the stack trace, the 500 "
            "error, the 3-hour debugging spiral. Structure: bug (0-3s) -> false fix everyone tries "
            "(3-10s) -> the actual one-liner (10-20s) -> why it works (tail). Show real terminals and "
            "real repos; fake stock footage kills credibility instantly with this crowd. "
            "Strong archetypes: 'I replaced 3 tools with 40 lines of Python', 'this lint rule "
            "found a bug our whole team missed'."
        ),
        keywords=["coding", "programming", "developer", "bug", "tutorial", "software"],
    ),
    dict(
        platform="cross", niche="tech",
        topic="Tech review hooks: price-gap + torture test",
        body=(
            "Gadget content lives on specificity: exact price vs the category leader, exact "
            "benchmark numbers, and a torture test nobody else runs (dropped it, froze it, ran it "
            "for 72h). Cold open with the verdict for short-form, with the surprise for long-form "
            "('the $12 gadget beat the $600 one — but not how you think'). Spec-sheet recitals "
            "are retention poison; every spec must attach to a use case."
        ),
        keywords=["tech", "gadget", "review", "benchmark", "unboxing", "price"],
    ),
    dict(
        platform="cross", niche="fitness",
        topic="Fitness hooks: constraint + proof physique",
        body=(
            "Gym content converts on constraints (12 minutes, no equipment, bad knees) stacked "
            "with visible proof (your own transformation or a client's). Cold-open patterns: "
            "mid-set first frame, 'stop doing X in the gym' negatives, and day-1/day-90 splits. "
            "Form-correction clips (‘you're doing squats wrong — here's the fix') outperform "
            "generic motivation 3-to-1 for saves; motivation content wins reach, form content wins saves."
        ),
        keywords=["fitness", "gym", "workout", "muscle", "diet", "push-ups"],
    ),
    dict(
        platform="cross", niche="cooking",
        topic="Food hooks: the receipt shot + constraint recipes",
        body=(
            "Food audiences want feasibility: budget caps ($40 weekly haul), time caps (15-minute "
            "dinners), equipment caps (one pan). Open on the finished dish or the money shot of the "
            "process (cheese pull, sizzle, glaze) — never on ingredients alone. 'Receipts in "
            "caption' builds trust and drives saves; recipe-in-caption value-dumps are the highest-save "
            "format in the niche. ASMR audio layers (sizzle, chopping) carry muted autoplay."
        ),
        keywords=["cooking", "food", "recipe", "kitchen", "meal", "budget"],
    ),
    dict(
        platform="cross", niche="business",
        topic="Finance hooks: numbers in the first line",
        body=(
            "Business/finance audiences trust specifics, not vibes: revenue numbers, tax figures, "
            "real invoices (redacted) in the first 3 seconds. Winning arcs: 'how I got my first "
            "client' with actual outreach screenshots, 'I audited a failing business' teardowns, "
            "and myth-busting ('LLCs don't do what you think'). Avoid guaranteed-return framing — "
            "it kills credibility with sophisticated viewers and risks platform flags."
        ),
        keywords=["business", "finance", "money", "investing", "client", "revenue"],
    ),
    dict(
        platform="cross", niche="vlogging",
        topic="Vlog hooks: in-medias-res + serialized stakes",
        body=(
            "Vlogs die from 'hey guys welcome back' — open mid-event at the most dramatic moment, "
            "then rewind ('so, three hours before this...'). Serialize: numbered days, countdown "
            "arcs, and cliffhanger endings drive profile visits and next-video notifications. "
            "Voiceover-with-b-roll context layers outperform talking-head recaps; keep talking-head "
            "for reaction/emotion only. On Shorts, text-overlay context lets muted autoplay land the premise."
        ),
        keywords=["vlog", "lifestyle", "daily", "story", "day in the life"],
    ),
]

TRENDS: list[dict] = [
    # YouTube
    dict(platform="youtube", kind="audio", title="Whisper-ASMR voiceovers on tutorial Shorts", heat=95,
         detail="Soft-spoken narration over screen-recording; retention +18% vs energetic VO in how-to niches."),
    dict(platform="youtube", kind="format", title="'I tested X for 30 days' arcs", heat=92,
         detail="Day-1 vs Day-30 payoff structure; negative-hook cold open ('don't buy this') outperforms positive."),
    dict(platform="youtube", kind="search_query", title="best ai tools 2026", heat=90,
         detail="Query volume climbing; informational intent — verdict-first videos win the click."),
    dict(platform="youtube", kind="thumbnail_style", title="Split-face reaction + red arrow", heat=84,
         detail="High CTR in tech/finance; 3-word max overlay text, emotion on one half of frame."),
    dict(platform="youtube", kind="hook_pattern", title="Open-loop question cold opens", heat=88,
         detail="'Why does nobody talk about this?' — 5s retention lift across niches per seed analysis."),
    dict(platform="youtube", kind="format", title="Sub-15s loop Shorts", heat=86,
         detail="Single payoff, last frame flows into first; loop rate is the ranking lever."),
    # Instagram
    dict(platform="instagram", kind="audio", title="Accelerating ambient phonk edits", heat=93,
         detail="Under 5k uses and rising — gym/tech/lifestyle Reels riding the wave this week."),
    dict(platform="instagram", kind="format", title="'Send this to your ___' relatable POVs", heat=91,
         detail="DM-share trigger built into the format; sends-per-reach 3x niche average."),
    dict(platform="instagram", kind="hashtag", title="#aistarterpack", heat=82,
         detail="Meme-format tag bridging tech humor and shareability; low competition, high saves."),
    dict(platform="instagram", kind="format", title="Short reel + long caption value-dump", heat=87,
         detail="12s b-roll reel, 150-word caption with the actual list — dwell time play."),
    dict(platform="instagram", kind="hook_pattern", title="Mid-action first frame", heat=89,
         detail="No title cards; open at the peak of the motion, caption the context."),
    dict(platform="instagram", kind="hashtag", title="#day90challenge", heat=78,
         detail="Transformation arcs with serialized follow-along incentive."),
]


def seed(db: Session) -> None:
    if db.query(Playbook).count() == 0:
        db.add_all([Playbook(**p) for p in PLAYBOOKS])
    if db.query(TrendSignal).count() == 0:
        db.add_all([TrendSignal(**t, source="seed") for t in TRENDS])
    db.commit()
