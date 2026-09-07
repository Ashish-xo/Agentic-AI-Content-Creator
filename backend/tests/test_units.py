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
