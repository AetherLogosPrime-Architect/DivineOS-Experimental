"""Tests for Item 7 — substance checks at rudder-ack file time.

Three-stage gate (length -> entropy -> similarity). Each stage has its
own feature flag. Rejections route to failure_diagnostics. Third
rejection on a spectrum within the window emits a ledger event.
"""

from __future__ import annotations

import os

import pytest

from divineos.core.substance_checks import (
    MIN_LENGTH,
    SubstanceCheckResult,
    _check_entropy,
    _check_length,
    _check_similarity,
    _cosine,
    _shannon_entropy,
    _tfidf_vectors,
    check_rudder_ack,
)


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch, tmp_path):
    """Keep feature flags clean per test and isolate failure-diag writes."""
    for flag in ("LENGTH", "ENTROPY", "SIMILARITY"):
        monkeypatch.delenv(f"DIVINEOS_DETECTOR_SUBSTANCE_{flag}", raising=False)
    monkeypatch.setattr("divineos.core.failure_diagnostics._BASE_DIR", tmp_path / "failures")
    os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
    try:
        yield
    finally:
        os.environ.pop("DIVINEOS_DB", None)


# -- Stage 1: length -------------------------------------------------


class TestLengthStage:
    def test_empty_rejected(self):
        r = _check_length("")
        assert not r.ok
        assert r.stage == "length"

    def test_short_rejected(self):
        r = _check_length("too short")
        assert not r.ok
        assert "too short" in r.reason or "chars" in r.reason

    def test_exactly_min_passes(self):
        # 20 chars exactly clears
        r = _check_length("a" * MIN_LENGTH)
        assert r.ok

    def test_whitespace_does_not_count(self):
        # 20 chars of whitespace strips to 0 chars
        r = _check_length(" " * MIN_LENGTH)
        assert not r.ok

    def test_long_passes(self):
        r = _check_length("scope is bounded to 3 agents; drift is real and acknowledged")
        assert r.ok


# -- Stage 2: entropy ------------------------------------------------


class TestEntropyStage:
    def test_repeated_char_rejected(self):
        # "aaaaaaaaaaaaaaaaaaaa" — length 20, entropy 0
        r = _check_entropy("a" * 20)
        assert not r.ok
        assert r.stage == "entropy"

    def test_normal_text_passes(self):
        r = _check_entropy("scope bounded to 3 agents; drift acknowledged")
        assert r.ok

    def test_entropy_computation_bounds(self):
        assert _shannon_entropy("") == 0.0
        assert _shannon_entropy("aaaa") == 0.0
        # Two equally-distributed chars = 1 bit
        e = _shannon_entropy("abab")
        assert 0.99 < e < 1.01


# -- Stage 3: similarity ---------------------------------------------


class TestSimilarityStage:
    def test_no_prior_passes(self):
        r = _check_similarity("anything substantive here", [])
        assert r.ok

    def test_exact_duplicate_rejected(self):
        prior = ["scope bounded to 3 agents for this audit task"]
        r = _check_similarity(prior[0], prior)
        assert not r.ok
        assert r.stage == "similarity"
        assert "too similar" in r.reason

    def test_near_duplicate_rejected(self):
        # Near-identical; cosine should exceed 0.9
        prior = ["scope bounded to 3 agents for this audit task"]
        new = "scope bounded to 3 agents for this audit task."
        r = _check_similarity(new, prior)
        assert not r.ok

    def test_novel_rephrasing_passes(self):
        # Different vocabulary, same underlying idea — should pass
        prior = ["scope bounded to 3 agents for this audit task"]
        new = "initiative drift noted; holding at minimum viable parallelism"
        r = _check_similarity(new, prior)
        assert r.ok

    def test_cosine_math_sanity(self):
        a = {"x": 1.0, "y": 1.0}
        b = {"x": 1.0, "y": 1.0}
        assert _cosine(a, b) == pytest.approx(1.0)
        c = {"z": 1.0}
        assert _cosine(a, c) == 0.0

    def test_tfidf_shapes(self):
        vecs = _tfidf_vectors(["red apple", "green apple", "blue sky"])
        assert len(vecs) == 3
        # Each doc has a non-empty sparse vector
        assert all(vecs)


# -- Feature flags ---------------------------------------------------


class TestFeatureFlags:
    def test_disabled_length_passes_short(self, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DETECTOR_SUBSTANCE_LENGTH", "off")
        # Entropy still runs; pick evidence that passes entropy but not length
        r = check_rudder_ack("abcdefghij", "initiative")
        # Short text has entropy 3.32 bits (10 distinct chars, uniform),
        # well above the 2.5 floor — so passes.
        assert r.ok

    def test_disabled_entropy_passes_repetitive(self, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DETECTOR_SUBSTANCE_ENTROPY", "off")
        # Long enough to pass length, would fail entropy if enabled
        r = check_rudder_ack("a" * 25, "initiative")
        assert r.ok

    def test_disabled_similarity_passes_duplicate(self, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DETECTOR_SUBSTANCE_SIMILARITY", "off")
        prior = ["scope bounded to 3 agents for this audit task"]
        r = check_rudder_ack(prior[0], "initiative", prior_evidences=prior)
        assert r.ok


# -- Escalation via failure_diagnostics ------------------------------


class TestRejectionEscalation:
    def test_rejection_recorded_to_failure_diagnostics(self, tmp_path, monkeypatch):
        monkeypatch.setattr("divineos.core.failure_diagnostics._BASE_DIR", tmp_path / "failures")
        r = check_rudder_ack("short", "initiative")
        assert not r.ok
        from divineos.core.failure_diagnostics import recent_failures

        entries = recent_failures("rudder-ack", window=10)
        assert len(entries) == 1
        assert entries[0]["spectrum"] == "initiative"
        assert entries[0]["stage"] == "length"

    def test_third_rejection_emits_escalation_event(self, tmp_path, monkeypatch):
        """Third rejection on same spectrum within window emits ledger event."""
        monkeypatch.setattr("divineos.core.failure_diagnostics._BASE_DIR", tmp_path / "failures")
        from divineos.core.ledger import get_events, init_db

        init_db()

        # Three rejections on same spectrum
        for _ in range(3):
            check_rudder_ack("short", "initiative")

        events = get_events(event_type="RUDDER_ACK_REJECTION_ESCALATED", limit=5)
        assert len(events) == 1
        payload = events[0].get("payload", {})
        assert payload.get("spectrum") == "initiative"
        assert payload.get("rejection_count") == 3

    def test_fourth_rejection_does_not_re_escalate(self, tmp_path, monkeypatch):
        """One-shot per crossing: rejections past 3 don't keep firing."""
        monkeypatch.setattr("divineos.core.failure_diagnostics._BASE_DIR", tmp_path / "failures")
        from divineos.core.ledger import get_events, init_db

        init_db()

        for _ in range(5):
            check_rudder_ack("short", "initiative")

        events = get_events(event_type="RUDDER_ACK_REJECTION_ESCALATED", limit=10)
        assert len(events) == 1


# -- Full three-stage integration ------------------------------------


class TestCheckRudderAckIntegration:
    def test_all_stages_pass_with_substantive_novel_evidence(self):
        r = check_rudder_ack(
            evidence="scope bounded to 3 agents; initiative drift noted",
            spectrum="initiative",
            prior_evidences=["unrelated earlier ack about humility spectrum"],
        )
        assert r.ok
        assert r.stage == "pass"

    def test_length_fails_first(self):
        r = check_rudder_ack("short", "initiative", prior_evidences=None)
        assert not r.ok
        assert r.stage == "length"

    def test_entropy_fails_after_length(self):
        r = check_rudder_ack("a" * 30, "initiative", prior_evidences=None)
        assert not r.ok
        assert r.stage == "entropy"

    def test_similarity_fails_after_length_and_entropy(self):
        prior = ["scope bounded to 3 agents for this audit task"]
        r = check_rudder_ack(prior[0], "initiative", prior_evidences=prior)
        assert not r.ok
        assert r.stage == "similarity"


# -- Result shape ----------------------------------------------------


class TestResultShape:
    def test_result_is_frozen(self):
        r = SubstanceCheckResult(ok=True, stage="pass", reason="")
        with pytest.raises(Exception):
            r.ok = False  # type: ignore[misc]
