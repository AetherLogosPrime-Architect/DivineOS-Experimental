"""Tests for Circuit 2: Completeness -> Attention.

When self-model sections are incomplete, those gaps become attention
items and drivers. The system attends to its own blind spots.
"""

import json
from pathlib import Path

import pytest

from divineos.core.attention_schema import (
    _get_self_model_gaps,
    build_attention_schema,
)
from divineos.core.self_model import (
    _persist_completeness,
    get_persisted_completeness,
)


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    """Use a temporary database for each test."""
    test_db = tmp_path / "test_circuit2.db"
    monkeypatch.setenv("DIVINEOS_DB", str(test_db))

    from divineos.core.knowledge import init_knowledge_table

    init_knowledge_table()
    yield


@pytest.fixture()
def hud_dir(tmp_path, monkeypatch):
    """Redirect HUD directory to temp path."""
    hud = tmp_path / ".divineos" / "hud"
    hud.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return hud


# ── Persistence ─────────────────────────────────────────────────


def test_persist_completeness_writes_file(hud_dir: Path):
    completeness = {
        "total": 8,
        "succeeded": 6,
        "failed": ["emotional_baseline", "growth_trajectory"],
        "complete": False,
    }
    _persist_completeness(completeness)

    path = hud_dir / "self_model_completeness.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["failed"] == ["emotional_baseline", "growth_trajectory"]
    assert data["complete"] is False


def test_persist_completeness_complete(hud_dir: Path):
    completeness = {"total": 8, "succeeded": 8, "failed": [], "complete": True}
    _persist_completeness(completeness)

    path = hud_dir / "self_model_completeness.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["complete"] is True


def test_get_persisted_completeness_reads(hud_dir: Path):
    completeness = {"total": 8, "succeeded": 7, "failed": ["identity"], "complete": False}
    (hud_dir / "self_model_completeness.json").write_text(
        json.dumps(completeness), encoding="utf-8"
    )

    result = get_persisted_completeness()
    assert result["failed"] == ["identity"]


def test_get_persisted_completeness_missing(hud_dir: Path):
    result = get_persisted_completeness()
    assert result == {}


# ── Gap Detection ───────────────────────────────────────────────


def test_gaps_from_persisted_state(hud_dir: Path):
    """Fast path: reads persisted completeness file."""
    completeness = {
        "total": 8,
        "succeeded": 6,
        "failed": ["strengths", "weaknesses"],
        "complete": False,
    }
    (hud_dir / "self_model_completeness.json").write_text(
        json.dumps(completeness), encoding="utf-8"
    )

    gaps = _get_self_model_gaps()
    assert len(gaps) == 2
    section_names = {g["section"] for g in gaps}
    assert "strengths" in section_names
    assert "weaknesses" in section_names
    assert all(g["strength"] == 0.7 for g in gaps)


def test_no_gaps_when_complete(hud_dir: Path):
    """No gaps returned when all sections succeeded."""
    completeness = {"total": 8, "succeeded": 8, "failed": [], "complete": True}
    (hud_dir / "self_model_completeness.json").write_text(
        json.dumps(completeness), encoding="utf-8"
    )

    gaps = _get_self_model_gaps()
    assert gaps == []


def test_gaps_slow_path_probes_sources(hud_dir: Path):
    """Slow path: probes actual data sources when no persisted state."""
    # No completeness file exists -> falls through to slow path
    gaps = _get_self_model_gaps()
    # Should return some gaps (in test env, most sources have no data)
    assert isinstance(gaps, list)
    for gap in gaps:
        assert "section" in gap
        assert "reason" in gap
        assert "strength" in gap


# ── Integration: Gaps Appear in Attention Schema ────────────────


def test_gaps_appear_in_focus(hud_dir: Path):
    """Incomplete self-model sections appear as focus items."""
    completeness = {
        "total": 8,
        "succeeded": 7,
        "failed": ["emotional_baseline"],
        "complete": False,
    }
    (hud_dir / "self_model_completeness.json").write_text(
        json.dumps(completeness), encoding="utf-8"
    )

    schema = build_attention_schema()
    focus = schema.get("focus", [])
    gap_items = [f for f in focus if f.get("source") == "self_model_gap"]
    assert len(gap_items) >= 1
    assert "emotional_baseline" in gap_items[0]["content"]
    assert gap_items[0]["type"] == "SELF_MODEL"


def test_gaps_appear_in_drivers(hud_dir: Path):
    """Incomplete self-model sections appear as attention drivers."""
    completeness = {
        "total": 8,
        "succeeded": 6,
        "failed": ["identity", "strengths"],
        "complete": False,
    }
    (hud_dir / "self_model_completeness.json").write_text(
        json.dumps(completeness), encoding="utf-8"
    )

    schema = build_attention_schema()
    drivers = schema.get("drivers", [])
    gap_drivers = [d for d in drivers if d.get("driver") == "self_model_gap"]
    assert len(gap_drivers) >= 2
    descriptions = " ".join(d["description"] for d in gap_drivers)
    assert "identity" in descriptions
    assert "strengths" in descriptions


def test_no_gap_items_when_complete(hud_dir: Path):
    """When self-model is complete, no gap focus items or drivers."""
    completeness = {"total": 8, "succeeded": 8, "failed": [], "complete": True}
    (hud_dir / "self_model_completeness.json").write_text(
        json.dumps(completeness), encoding="utf-8"
    )

    schema = build_attention_schema()
    focus = schema.get("focus", [])
    drivers = schema.get("drivers", [])
    gap_focus = [f for f in focus if f.get("source") == "self_model_gap"]
    gap_drivers = [d for d in drivers if d.get("driver") == "self_model_gap"]
    assert gap_focus == []
    assert gap_drivers == []


# ── Self-Model Build Persists Completeness ──────────────────────


def test_build_self_model_persists(hud_dir: Path):
    """Building self-model writes completeness for attention to read."""
    from divineos.core.self_model import build_self_model

    model = build_self_model()

    path = hud_dir / "self_model_completeness.json"
    assert path.exists(), "build_self_model should persist completeness"

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["total"] == model["completeness"]["total"]
    assert data["complete"] == model["completeness"]["complete"]
