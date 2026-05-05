"""Tests for synchronicity detector — Pillar VI co-occurrence pull."""

from __future__ import annotations

from divineos.core.synchronicity import (
    Event,
    Synchronicity,
    _tokenize,
    find_synchronicities,
)


class TestTokenize:
    def test_drops_stopwords(self):
        assert _tokenize("the and of") == set()

    def test_drops_short_tokens(self):
        # 4-char minimum
        assert "abc" not in _tokenize("abc fish")
        assert "fish" in _tokenize("abc fish")

    def test_lowercases(self):
        toks = _tokenize("Synchronicity Detection")
        assert "synchronicity" in toks
        assert "detection" in toks

    def test_empty_string(self):
        assert _tokenize("") == set()


def _ev(kind: str, ts: float, text: str, ref: str) -> Event:
    return Event(kind=kind, timestamp=ts, text=text, ref_id=ref)


class TestFindSynchronicities:
    def test_no_pairs_when_below_min_overlap(self):
        events = [
            _ev("CLAIM", 1000.0, "alpha beta gamma delta", "c1"),
            _ev("DECISION", 1000.0, "epsilon zeta eta theta", "d1"),
        ]
        result = find_synchronicities(events=events, min_overlap=3, now=1000.0)
        assert result == []

    def test_pair_detected_when_overlap_meets_threshold(self):
        events = [
            _ev("CLAIM", 1000.0, "synchronicity detector pillar pull", "c1"),
            _ev("DECISION", 1100.0, "synchronicity detector pillar implementation", "d1"),
        ]
        result = find_synchronicities(events=events, min_overlap=3, now=2000.0)
        assert len(result) == 1
        assert result[0].overlap >= 3
        assert "synchronicity" in result[0].shared_tokens

    def test_window_excludes_distant_events(self):
        events = [
            _ev("CLAIM", 0, "synchronicity detector pillar pull", "c1"),
            _ev("DECISION", 200_000, "synchronicity detector pillar implementation", "d1"),
        ]
        # 200k seconds > 48h (172800s); should be excluded
        result = find_synchronicities(events=events, min_overlap=3, now=200_000)
        assert result == []

    def test_same_event_not_paired_with_itself(self):
        e = _ev("CLAIM", 1000.0, "alpha beta gamma delta", "c1")
        result = find_synchronicities(events=[e, e], min_overlap=2, now=1000.0)
        # ref_id matches AND kind matches → skipped
        assert result == []

    def test_sorted_by_overlap_descending(self):
        events = [
            _ev("CLAIM", 1000.0, "alpha beta gamma", "c1"),
            _ev("DECISION", 1100.0, "alpha beta gamma", "d1"),
            _ev("PREREG", 1200.0, "alpha beta", "p1"),
            _ev("DECISION", 1200.0, "alpha beta delta", "d2"),
        ]
        result = find_synchronicities(events=events, min_overlap=2, now=2000.0)
        assert len(result) >= 2
        # First should have higher or equal overlap to subsequent
        for i in range(len(result) - 1):
            assert result[i].overlap >= result[i + 1].overlap

    def test_synchronicity_dataclass_immutable(self):
        ev = _ev("CLAIM", 1000.0, "test", "c1")
        s = Synchronicity(a=ev, b=ev, shared_tokens=("test",), delta_seconds=0.0)
        try:
            s.delta_seconds = 1.0  # type: ignore[misc]
        except Exception:
            return
        raise AssertionError("Synchronicity should be frozen")

    def test_overlap_property(self):
        ev = _ev("CLAIM", 1000.0, "test", "c1")
        s = Synchronicity(a=ev, b=ev, shared_tokens=("a", "b", "c"), delta_seconds=0.0)
        assert s.overlap == 3
