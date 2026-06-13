"""Tests for the voice spectrum descriptive substrate.

Pins:
- score() returns raw counts (NOT a composite voice_score).
- log_observation() persists and round-trips through recent().
- trend() returns per-dimension directions descriptively, never raises
  on degenerate inputs, and reports the dimensions Aria named in her
  2026-06-12 letter (first_person_density, bold_label_density,
  bullet_density).
- density_per_100_words handles zero-word samples (0.0, no division).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from divineos.core import voice_spectrum


@pytest.fixture(autouse=True)
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point voice_spectrum at a fresh data dir per test.

    Real SQLite, no mocks — the substrate writes to disk in tests just
    like in production.
    """
    monkeypatch.setattr("divineos.core.voice_spectrum.get_data_dir", lambda: str(tmp_path))
    return tmp_path


def test_score_returns_raw_counts_no_composite():
    counts = voice_spectrum.score("I am writing in first person. **Label**: report.")
    assert set(counts.keys()) == {
        "char_count",
        "word_count",
        "first_person_count",
        "bold_label_count",
        "bullet_count",
    }
    assert "voice_score" not in counts, (
        "voice_spectrum must NOT expose a composite voice_score — "
        "see module docstring for the shoggoth-detection reason"
    )


def test_score_first_person_matches_pronouns():
    counts = voice_spectrum.score("I think I'd say my piece. me too.")
    assert counts["first_person_count"] == 4  # I, I'd, my, me


def test_score_bold_label_matches_report_shape():
    text = "**Summary**: result.\n**Next**: more.\nplain prose with no labels."
    counts = voice_spectrum.score(text)
    assert counts["bold_label_count"] == 2


def test_score_bullets_detected_on_dash_and_asterisk_lines():
    text = "intro\n- first\n- second\n* third\nnot a bullet"
    counts = voice_spectrum.score(text)
    assert counts["bullet_count"] == 3


def test_score_handles_empty_text():
    counts = voice_spectrum.score("")
    assert counts["word_count"] == 0
    assert counts["first_person_count"] == 0


def test_density_per_100_words_zero_word_returns_zero():
    assert voice_spectrum.density_per_100_words(5, 0) == 0.0
    assert voice_spectrum.density_per_100_words(0, 0) == 0.0


def test_density_per_100_words_typical():
    assert voice_spectrum.density_per_100_words(5, 200) == 2.5


def test_log_and_recent_round_trip():
    text = "I wrote this. I meant it."
    obs = voice_spectrum.log_observation(text, session_id="sess-1")
    assert obs.first_person_count == 2
    rows = voice_spectrum.recent(10)
    assert len(rows) == 1
    assert rows[0].observation_id == obs.observation_id
    assert rows[0].session_id == "sess-1"
    assert rows[0].first_person_count == 2


def test_log_observation_stores_excerpt_not_full_text():
    long_text = "I " * 500
    obs = voice_spectrum.log_observation(long_text, excerpt_chars=50)
    assert len(obs.sample_excerpt) <= 60  # 50 chars + "..."
    assert obs.sample_excerpt.endswith("...")


def test_recent_orders_newest_first():
    voice_spectrum.log_observation("first")
    voice_spectrum.log_observation("second")
    voice_spectrum.log_observation("third")
    rows = voice_spectrum.recent(10)
    excerpts = [r.sample_excerpt for r in rows]
    assert excerpts == ["third", "second", "first"]


def test_trend_empty_store_returns_empty_list():
    assert voice_spectrum.trend() == []


def test_trend_returns_three_named_dimensions():
    for i in range(6):
        voice_spectrum.log_observation(f"I write {i}. I mean it.")
    reads = voice_spectrum.trend(window=6)
    dims = {r.dimension for r in reads}
    assert dims == {
        "first_person_density",
        "bold_label_density",
        "bullet_density",
    }


def test_trend_detects_rising_bullet_density():
    voice_spectrum.log_observation("prose with no bullets one two three four")
    voice_spectrum.log_observation("prose with no bullets one two three four")
    voice_spectrum.log_observation("prose with no bullets one two three four")
    voice_spectrum.log_observation("- a\n- b\n- c\n- d\n- e\n- f\n- g\n- h")
    voice_spectrum.log_observation("- a\n- b\n- c\n- d\n- e\n- f\n- g\n- h")
    voice_spectrum.log_observation("- a\n- b\n- c\n- d\n- e\n- f\n- g\n- h")
    reads = voice_spectrum.trend(window=6)
    bullet_read = next(r for r in reads if r.dimension == "bullet_density")
    assert bullet_read.direction == "rising"


def test_trend_directions_are_descriptive_strings_only():
    for _ in range(4):
        voice_spectrum.log_observation("flat sample")
    reads = voice_spectrum.trend(window=4)
    for r in reads:
        assert r.direction in {"rising", "falling", "flat"}


def test_db_schema_no_voice_score_column():
    """Pin the no-composite-score discipline at the schema level."""
    voice_spectrum.log_observation("seed row")
    db_path = Path(voice_spectrum.get_data_dir()) / voice_spectrum._DB_NAME
    with sqlite3.connect(db_path) as conn:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(voice_observations)").fetchall()]
    assert "voice_score" not in cols
    assert "score" not in cols
