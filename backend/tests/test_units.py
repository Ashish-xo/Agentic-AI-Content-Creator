"""Unit tests — offline-safe (LLM calls mocked)."""
from __future__ import annotations

import pytest

from app.engine import modes, rag
from app.engine.llm_json import extract_json  # re-export shim
from app.engine.onboarding import advance, get_or_create
from app.seed.data import PLAYBOOKS, TRENDS


def test_detect_mode():
    assert modes.detect_mode("show me what's going viral this week") == "research"
    assert modes.detect_mode("write 3 hook options and a script") == "creation"
    assert modes.detect_mode("critique my draft caption to increase shares") == "optimization"
    assert modes.detect_mode("hello there") is None


def test_extract_json():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Sure! [{"x": 2}] done') == [{"x": 2}]
    assert extract_json('plain {"ok": true} text') == {"ok": True}


def test_seed_data_shape():
    assert len(PLAYBOOKS) >= 10
    platforms = {t["platform"] for t in TRENDS}
    assert {"youtube", "instagram"} <= platforms
    assert all(0 <= t["heat"] <= 100 for t in TRENDS)


def test_rag_retrieve(db_session):
    from app.models.tables import Playbook
    db_session.add_all([Playbook(**p) for p in PLAYBOOKS])
    db_session.commit()
    hits = rag.retrieve(db_session, "youtube", "how do I improve my thumbnail ctr")
    assert hits
    assert any("thumbnail" in h.topic.lower() for h in hits)


def test_onboarding_flow(db_session):
    p = get_or_create(db_session, "tester")
    q, done = advance(db_session, p, "fitness")
    assert q and not done  # next question: audience
    assert p.target_audience is None and p.niche == "fitness"
    q, done = advance(db_session, p, "gen z")
    q, done = advance(db_session, p, "casual")
    q, done = advance(db_session, p, "grow followers")
    assert done and q is None
    assert p.completed and p.niche == "fitness"
    assert "fitness" in p.summary().lower()


def test_cringe_scan_and_clean():
    from app.engine import cringe
    vs = cringe.scan("This game-changer will unlock the secret to going viral 🚀")
    phrases = {v.phrase for v in vs}
    assert "game-changer" in phrases and "unlock the secret" in phrases and "🚀" in phrases
    assert cringe.scan("I replaced 3 editors with a Python script.") == []
    kept, viol = cringe.clean_items(
        [{"hook": "delve into my routine"}, {"hook": "I ran 100 miles in 7 days"}], "hook")
    assert len(kept) == 1 and kept[0]["hook"].startswith("I ran")
    assert viol and viol[0].phrase == "delve"


def test_fewshot_selection_and_block(db_session):
    from app.engine import fewshot
    fewshot.seed_examples(db_session)
    picked = fewshot.select_examples(db_session, "instagram", "12 minute lunch workout", k=3)
    assert len(picked) == 3
    assert all(p.platform == "instagram" for p in picked)  # platform bonus dominates
    block = fewshot.fewshot_block(picked, "home workouts", 5)
    assert block.startswith("Analyze how these high-retention hooks work:")
    assert "Now generate 5 hooks for: home workouts" in block


def test_history_trim():
    from app.routes.chat import _trim_history
    hist = [{"role": "user", "content": "y" * 9999} for _ in range(10)]
    trimmed = _trim_history(hist)
    assert len(trimmed) == 8  # last 8 kept
    assert all(len(m["content"]) == 4000 for m in trimmed)
    compact = _trim_history(hist, compact=True)
    assert all(len(m["content"]) == 1500 for m in compact)
    # messages without content are dropped
    mixed = [{"role": "user", "content": "hi"}, {"role": "assistant"}, {"role": "user", "content": "yo"}]
    assert len(_trim_history(mixed)) == 2
