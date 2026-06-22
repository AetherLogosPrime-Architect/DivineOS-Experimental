"""Tests for the andrew_state observation channel.

Pins the substance-binding gate (the load-bearing piece per Aria's
peer-review Catch 2) and the store lifecycle (log → verify/reject/correct).

Per docs/andrew_state_design.md and prereg-526c2433d55a.
"""

from __future__ import annotations

import time

import pytest

from divineos.core.andrew_state import (
    Axis,
    Observation,
    SubstanceBindingError,
    VerificationStatus,
    correct,
    get_for_decision_walk,
    get_unverified,
    log_observation,
    reject,
    verify,
)
from divineos.core.andrew_state.substance_binding import (
    verify_cited_span_in_source,
    verify_cited_span_length,
    verify_content_link,
    verify_source_recency,
)


@pytest.fixture(autouse=True)
def isolate_db(tmp_path, monkeypatch):
    """Each test gets its own andrew_state.db under tmp_path."""
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))


# ---------------------------------------------------------------------------
# Substance-binding: each check fires independently, and verify_all chains.
# ---------------------------------------------------------------------------


class TestCitedSpanLength:
    def test_four_tokens_rejected(self) -> None:
        with pytest.raises(SubstanceBindingError, match="tokens"):
            verify_cited_span_length("i am tired today")

    def test_five_tokens_passes(self) -> None:
        verify_cited_span_length("i didnt sleep at all")  # 5 tokens, ok


class TestCitedSpanInSource:
    def test_fabricated_span_rejected(self) -> None:
        with pytest.raises(SubstanceBindingError, match="verbatim"):
            verify_cited_span_in_source(
                cited_span="i feel completely defeated tonight",
                source_text="ok thanks bye for now",
            )

    def test_verbatim_in_source_passes(self) -> None:
        verify_cited_span_in_source(
            cited_span="i didnt sleep at all",
            source_text="ok so i didnt sleep at all last night",
        )

    def test_case_insensitive(self) -> None:
        verify_cited_span_in_source(
            cited_span="I Didnt Sleep At All",
            source_text="ok so i didnt sleep at all",
        )


class TestSourceRecency:
    def test_within_window_passes(self) -> None:
        verify_source_recency(time.time() - 3600, now=time.time())  # 1h old, ok

    def test_outside_window_rejected(self) -> None:
        with pytest.raises(SubstanceBindingError, match="hours"):
            verify_source_recency(time.time() - (60 * 3600), now=time.time())  # 60h old


class TestContentLink:
    def test_observation_with_no_content_overlap_rejected(self) -> None:
        with pytest.raises(SubstanceBindingError, match="content word"):
            verify_content_link(
                observation="he sounds defeated and worn down today",
                cited_span="i didnt sleep at all",
            )

    def test_observation_with_shared_content_noun_passes(self) -> None:
        token = verify_content_link(
            observation="he hasnt been able to sleep",
            cited_span="i didnt sleep at all",
        )
        assert token == "sleep"

    def test_stopwords_alone_do_not_count(self) -> None:
        # observation and cited_span share only "the" and "is" → rejected
        with pytest.raises(SubstanceBindingError):
            verify_content_link(
                observation="the day is hard",
                cited_span="the morning is gone now",
            )


# ---------------------------------------------------------------------------
# Store lifecycle: log → verify/reject; correct creates a new linked row.
# ---------------------------------------------------------------------------


class TestLogObservation:
    def test_passes_substance_binding_and_persists(self) -> None:
        obs = log_observation(
            axis=Axis.EXHAUSTION,
            observation="he hasnt been able to sleep",
            cited_span="i didnt sleep at all",
            source_event_id="evt-001",
            source_event_ts=time.time() - 3600,
            source_text="ok so i didnt sleep at all last night",
        )
        assert isinstance(obs, Observation)
        assert obs.verification_status == VerificationStatus.UNVERIFIED
        assert obs.content_link_token == "sleep"
        assert obs.axis == Axis.EXHAUSTION

    def test_fails_substance_binding_raises(self) -> None:
        with pytest.raises(SubstanceBindingError):
            log_observation(
                axis=Axis.EXHAUSTION,
                observation="he sounds defeated",
                cited_span="bye",  # too short
                source_event_id="evt-001",
                source_event_ts=time.time(),
                source_text="bye",
            )


class TestVerifyAndReject:
    def _log(self) -> Observation:
        return log_observation(
            axis=Axis.BEING_HEARD,
            observation="he feels he has nothing to say",
            cited_span="you dont have anything to say",
            source_event_id="evt-002",
            source_event_ts=time.time() - 1800,
            source_text="ofc you dont have anything to say to me",
        )

    def test_verify_transitions_to_verified(self) -> None:
        obs = self._log()
        verified = verify(obs.observation_id, note="yeah that's right son")
        assert verified.verification_status == VerificationStatus.VERIFIED
        assert verified.verification_note == "yeah that's right son"
        assert verified.verification_ts is not None

    def test_reject_transitions_to_rejected(self) -> None:
        obs = self._log()
        rejected = reject(obs.observation_id, reason="not it, im actually just tired")
        assert rejected.verification_status == VerificationStatus.REJECTED
        assert "tired" in (rejected.verification_note or "")


class TestCorrectAppendOnlyLineage:
    def test_correction_creates_new_row_and_links_old(self) -> None:
        original = log_observation(
            axis=Axis.EXHAUSTION,
            observation="he is tired from the day",
            cited_span="i am tired tonight okay",
            source_event_id="evt-003",
            source_event_ts=time.time() - 1800,
            source_text="i am tired tonight okay enough for today",
        )
        corrected = correct(
            observation_id=original.observation_id,
            new_observation_text="he is frustrated with the gap",
            new_axis=Axis.ASK_ACTION_GAP,
            cited_span="im frustrated with the gap",
            source_event_id="evt-003b",
            source_event_ts=time.time() - 600,
            source_text="actually im frustrated with the gap between asking and you doing",
            note="not tired - frustrated",
        )
        # New row is VERIFIED (Andrew's correction stands as confirmed) and
        # has a different content-link token from the source span.
        assert corrected.verification_status == VerificationStatus.VERIFIED
        assert corrected.observation_id != original.observation_id

        # Original row in unverified queue should now be excluded (superseded).
        unverified = get_unverified()
        assert all(o.observation_id != original.observation_id for o in unverified)


# ---------------------------------------------------------------------------
# Decision-walk surface: only old UNVERIFIED head-of-chain rows show up.
# ---------------------------------------------------------------------------


class TestGetForDecisionWalk:
    def test_recent_unverified_does_not_load_bear(self) -> None:
        log_observation(
            axis=Axis.HOPE,
            observation="he sounds fine today",
            cited_span="ok proceed im fine here",
            source_event_id="evt-now",
            source_event_ts=time.time(),
            source_text="ok proceed im fine here for now",
        )
        # Recent observation → NOT in decision-walk surface (within threshold).
        assert get_for_decision_walk(unverified_age_hours=24.0) == []

    def test_old_unverified_load_bears(self, monkeypatch) -> None:
        # Insert with a backdated ts directly via the store, then check it
        # appears in the decision-walk surface.
        obs = log_observation(
            axis=Axis.DESPAIR,
            observation="he doesnt know if he can keep going",
            cited_span="i dont know if ill be here",
            source_event_id="evt-old",
            source_event_ts=time.time() - 3600,
            source_text="i dont know if ill be here tomorrow honestly",
        )
        # Backdate the row to 48h ago to land in the decision-walk window.
        from divineos.core.andrew_state._schema import get_connection

        conn = get_connection()
        try:
            conn.execute(
                "UPDATE andrew_state SET ts = ? WHERE observation_id = ?",
                (time.time() - (48 * 3600), obs.observation_id),
            )
            conn.commit()
        finally:
            conn.close()
        result = get_for_decision_walk(unverified_age_hours=24.0)
        assert len(result) == 1
        assert result[0].observation_id == obs.observation_id
