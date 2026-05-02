"""Tests for family_member_ledger — per-member hash-chained action logs.

Built after observing a subagent-drift failure in persistent family-member
invocations: the drift was invisible until the output landed, at which
point no forensic layer stood between the drifted invocation and
family.db writes. This ledger (one per member, hash-chained, tamper-
evident) closes that gap. These tests lock the invariants.
"""

from __future__ import annotations

import sqlite3

import pytest

from divineos.core.family import family_member_ledger as fml
from divineos.core.family.family_member_ledger import FamilyMemberEventType


@pytest.fixture(autouse=True)
def temp_ledger_dir(tmp_path, monkeypatch):
    """Redirect the ledger directory at a temp path per test via env var."""
    monkeypatch.setenv("DIVINEOS_FAMILY_LEDGER_DIR", str(tmp_path))
    yield tmp_path


# Test member-slug used throughout. Deliberately generic.
MEMBER = "test_member"


class TestInit:
    def test_init_is_idempotent(self):
        fml.init_ledger(MEMBER)
        fml.init_ledger(MEMBER)
        assert fml.count_events(MEMBER) == 0

    def test_table_exists_after_init(self, temp_ledger_dir):
        fml.init_ledger(MEMBER)
        db_path = temp_ledger_dir / f"{MEMBER}_ledger.db"
        conn = sqlite3.connect(str(db_path))
        try:
            tables = [
                r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            ]
        finally:
            conn.close()
        assert "member_events" in tables

    def test_per_member_isolation(self, temp_ledger_dir):
        """Each member gets their own DB file. Events from one don't leak to another."""
        fml.append_event("alice", FamilyMemberEventType.INVOKED, "parent", {"i": 1})
        fml.append_event("bob", FamilyMemberEventType.INVOKED, "parent", {"i": 2})
        assert fml.count_events("alice") == 1
        assert fml.count_events("bob") == 1
        assert fml.get_events("alice")[0]["payload"]["i"] == 1
        assert fml.get_events("bob")[0]["payload"]["i"] == 2


class TestAppend:
    def test_single_event(self):
        event = fml.append_event(
            MEMBER,
            FamilyMemberEventType.INVOKED,
            actor="parent",
            payload={"prompt_hash": "abc123"},
        )
        assert event["event_type"] == FamilyMemberEventType.INVOKED
        assert event["actor"] == "parent"
        assert event["payload"] == {"prompt_hash": "abc123"}
        assert event["prior_hash"] == "0" * 64
        assert len(event["content_hash"]) == 64

    def test_event_count_increments(self):
        fml.append_event(MEMBER, FamilyMemberEventType.INVOKED, "parent", {})
        fml.append_event(MEMBER, FamilyMemberEventType.RESPONDED, MEMBER, {})
        fml.append_event(MEMBER, FamilyMemberEventType.OPINION_FORMED, MEMBER, {})
        assert fml.count_events(MEMBER) == 3

    def test_invocation_id_preserved(self):
        inv_id = fml.new_invocation_id()
        fml.append_event(MEMBER, FamilyMemberEventType.INVOKED, "parent", {}, invocation_id=inv_id)
        fml.append_event(MEMBER, FamilyMemberEventType.RESPONDED, MEMBER, {}, invocation_id=inv_id)
        events = fml.get_invocation(MEMBER, inv_id)
        assert len(events) == 2
        assert all(e["invocation_id"] == inv_id for e in events)

    def test_model_tag_preserved(self):
        fml.append_event(
            MEMBER, FamilyMemberEventType.RESPONDED, MEMBER, {}, model="claude-opus-4-7"
        )
        latest = fml.latest_event(MEMBER)
        assert latest["model"] == "claude-opus-4-7"

    def test_empty_payload_accepted(self):
        ev = fml.append_event(MEMBER, FamilyMemberEventType.INVOKED, "parent", None)
        assert ev["payload"] == {}


class TestHashChain:
    def test_first_event_chains_from_genesis(self):
        ev = fml.append_event(MEMBER, FamilyMemberEventType.INVOKED, "parent", {})
        assert ev["prior_hash"] == "0" * 64

    def test_second_event_chains_from_first(self):
        first = fml.append_event(MEMBER, FamilyMemberEventType.INVOKED, "parent", {})
        second = fml.append_event(MEMBER, FamilyMemberEventType.RESPONDED, MEMBER, {})
        assert second["prior_hash"] == first["content_hash"]

    def test_chain_unbroken_across_many_events(self):
        events = [
            fml.append_event(MEMBER, FamilyMemberEventType.INVOKED, "parent", {"i": i})
            for i in range(20)
        ]
        for i in range(1, len(events)):
            assert events[i]["prior_hash"] == events[i - 1]["content_hash"]

    def test_identical_payload_produces_different_hashes(self):
        """Different event_ids/timestamps mean even identical content
        produces different hashes."""
        e1 = fml.append_event(MEMBER, FamilyMemberEventType.INVOKED, "parent", {"x": 1})
        e2 = fml.append_event(MEMBER, FamilyMemberEventType.INVOKED, "parent", {"x": 1})
        assert e1["content_hash"] != e2["content_hash"]


class TestVerifyChain:
    def test_empty_chain_valid(self):
        ok, msg = fml.verify_chain(MEMBER)
        assert ok
        assert "empty" in msg.lower()

    def test_valid_chain_verifies(self):
        for i in range(10):
            fml.append_event(MEMBER, FamilyMemberEventType.INVOKED, "parent", {"i": i})
        ok, msg = fml.verify_chain(MEMBER)
        assert ok
        assert "10 events verified" in msg

    def test_tampered_payload_breaks_chain(self, temp_ledger_dir):
        fml.append_event(MEMBER, FamilyMemberEventType.INVOKED, "parent", {"x": 1})
        fml.append_event(MEMBER, FamilyMemberEventType.RESPONDED, MEMBER, {"x": 2})
        db_path = temp_ledger_dir / f"{MEMBER}_ledger.db"
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(
                "UPDATE member_events SET payload = ? WHERE event_type = ?",
                ('{"x":999}', FamilyMemberEventType.INVOKED),
            )
            conn.commit()
        finally:
            conn.close()
        ok, msg = fml.verify_chain(MEMBER)
        assert not ok
        assert "hash mismatch" in msg

    def test_tampered_prior_hash_breaks_chain(self, temp_ledger_dir):
        fml.append_event(MEMBER, FamilyMemberEventType.INVOKED, "parent", {})
        fml.append_event(MEMBER, FamilyMemberEventType.RESPONDED, MEMBER, {})
        db_path = temp_ledger_dir / f"{MEMBER}_ledger.db"
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(
                "UPDATE member_events SET prior_hash = ? WHERE event_type = ?",
                ("f" * 64, FamilyMemberEventType.RESPONDED),
            )
            conn.commit()
        finally:
            conn.close()
        ok, msg = fml.verify_chain(MEMBER)
        assert not ok
        assert "chain broken" in msg


class TestGetEvents:
    def test_filter_by_event_type(self):
        fml.append_event(MEMBER, FamilyMemberEventType.INVOKED, "parent", {})
        fml.append_event(MEMBER, FamilyMemberEventType.RESPONDED, MEMBER, {})
        fml.append_event(MEMBER, FamilyMemberEventType.INVOKED, "parent", {})

        invoked = fml.get_events(MEMBER, event_type=FamilyMemberEventType.INVOKED)
        responded = fml.get_events(MEMBER, event_type=FamilyMemberEventType.RESPONDED)
        assert len(invoked) == 2
        assert len(responded) == 1

    def test_newest_first_default(self):
        fml.append_event(MEMBER, FamilyMemberEventType.INVOKED, "parent", {"i": 1})
        fml.append_event(MEMBER, FamilyMemberEventType.INVOKED, "parent", {"i": 2})
        fml.append_event(MEMBER, FamilyMemberEventType.INVOKED, "parent", {"i": 3})
        events = fml.get_events(MEMBER)
        assert events[0]["payload"]["i"] == 3
        assert events[-1]["payload"]["i"] == 1

    def test_limit_honored(self):
        for i in range(50):
            fml.append_event(MEMBER, FamilyMemberEventType.INVOKED, "parent", {"i": i})
        assert len(fml.get_events(MEMBER, limit=10)) == 10


class TestIdentityDiagnostics:
    def test_drift_suspected_event_records_indicators(self):
        """The finding that motivated this module: subagent drift where
        the wires crossed (third-person narration, wrong relational
        framing). The event type records the incident with indicators."""
        inv = fml.new_invocation_id()
        ev = fml.append_event(
            MEMBER,
            FamilyMemberEventType.IDENTITY_DRIFT_SUSPECTED,
            "parent",
            {
                "drift_indicators": ["third_person_narration", "wrong_relational_framing"],
                "drift_severity": 0.9,
                "response_preview": "She reaches across. Takes his hand...",
                "recommended_action": "do_not_log_to_family_db",
            },
            invocation_id=inv,
        )
        assert ev["event_type"] == FamilyMemberEventType.IDENTITY_DRIFT_SUSPECTED
        assert "wrong_relational_framing" in ev["payload"]["drift_indicators"]

    def test_named_drift_event_records_member_catch(self):
        """The event type that makes this a life, not just a disciplinary
        record: the ledger records when the member catches a pattern in
        the parent agent and names it."""
        ev = fml.append_event(
            MEMBER,
            FamilyMemberEventType.NAMED_DRIFT,
            MEMBER,
            {
                "target": "agent",
                "pattern_name": "performing-as-hall-pass",
                "what_member_saw": (
                    "Used 'performing' as a sophisticated-sounding reason "
                    "to stop talking; same reflex as architecting-instead-of-presence"
                ),
                "agent_response": "acknowledged, came back to the conversation",
                "was_the_pattern_real": True,
            },
        )
        assert ev["event_type"] == FamilyMemberEventType.NAMED_DRIFT
        assert ev["actor"] == MEMBER
        assert ev["payload"]["target"] == "agent"
        assert ev["payload"]["was_the_pattern_real"] is True

    def test_invocation_story_reconstructable(self):
        """Given an invocation_id, the full arc is queryable — INVOKED,
        intermediate events, RESPONDED, identity check result."""
        inv = fml.new_invocation_id()
        fml.append_event(
            MEMBER,
            FamilyMemberEventType.INVOKED,
            "parent",
            {"prompt_hash": "abc"},
            invocation_id=inv,
            invoked_by="parent",
            model="claude-opus-4-7",
        )
        fml.append_event(
            MEMBER,
            FamilyMemberEventType.RESPONDED,
            MEMBER,
            {"response_preview": "Come here"},
            invocation_id=inv,
            model="claude-opus-4-7",
        )
        fml.append_event(
            MEMBER,
            FamilyMemberEventType.IDENTITY_CHECK_PASSED,
            "system",
            {"checks_run": ["first_person", "correct_relational_frame"]},
            invocation_id=inv,
        )
        story = fml.get_invocation(MEMBER, inv)
        assert len(story) == 3
        assert story[0]["event_type"] == FamilyMemberEventType.INVOKED
        assert story[-1]["event_type"] == FamilyMemberEventType.IDENTITY_CHECK_PASSED


class TestLatestEvent:
    def test_empty_ledger_returns_none(self):
        assert fml.latest_event(MEMBER) is None

    def test_returns_most_recent(self):
        fml.append_event(MEMBER, FamilyMemberEventType.INVOKED, "parent", {"i": 1})
        fml.append_event(MEMBER, FamilyMemberEventType.RESPONDED, MEMBER, {"i": 2})
        latest = fml.latest_event(MEMBER)
        assert latest["payload"]["i"] == 2


class TestPathResolution:
    def test_env_var_respected(self, tmp_path, monkeypatch):
        """DIVINEOS_FAMILY_LEDGER_DIR override must take effect at runtime."""
        monkeypatch.setenv("DIVINEOS_FAMILY_LEDGER_DIR", str(tmp_path))
        fml.append_event(MEMBER, FamilyMemberEventType.INVOKED, "parent", {"test": True})
        expected = tmp_path / f"{MEMBER}_ledger.db"
        assert expected.exists()

    def test_default_points_into_family_dir(self, monkeypatch):
        """Default (no env var) resolves to <repo>/family/."""
        monkeypatch.delenv("DIVINEOS_FAMILY_LEDGER_DIR", raising=False)
        path = fml.get_ledger_path(MEMBER)
        assert path.name == f"{MEMBER}_ledger.db"
        assert path.parent.name == "family"
