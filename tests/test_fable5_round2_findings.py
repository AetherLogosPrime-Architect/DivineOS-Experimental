"""Regression-pins for Fable 5 audit Round 2 findings (2026-06-09).

Finding 4 (CRITICAL): divineos verify cannot detect event deletion or
truncation because it calls verify_all_events (per-event content_hash
only) and never walks the chain. verify_chain exists, works, and is
now wired in — these tests pin that wiring.

Finding 5 (MEDIUM): _is_low_friction_write uses unanchored substring
matching, so exploration/../core/ledger.py and data/mansion/config.py
bypass the soft discipline gates. These tests pin the audit's exact
adversarial cases — they must NOT qualify for the exemption.
"""

from __future__ import annotations

import pytest

from divineos.core.ledger import init_db, log_event, verify_all_events, verify_chain
from divineos.hooks import pre_tool_use_gate as pre_hook


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
    init_db()


def _seed_chain(n: int = 5) -> None:
    for i in range(n):
        log_event("TEST_EVENT", actor="test", payload={"i": i})


def _delete_event_by_index(db_path: str, index: int) -> None:
    """Delete the Nth row from system_events to simulate tampering."""
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        rows = list(
            conn.execute("SELECT event_id FROM system_events ORDER BY timestamp ASC, rowid ASC")
        )
        target_id = rows[index][0]
        conn.execute("DELETE FROM system_events WHERE event_id = ?", (target_id,))
        conn.commit()
    finally:
        conn.close()


def _truncate_tail(db_path: str, keep_n: int) -> None:
    """Delete all events past the keep_n-th, simulating truncation."""
    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        rows = list(
            conn.execute("SELECT event_id FROM system_events ORDER BY timestamp ASC, rowid ASC")
        )
        for row in rows[keep_n:]:
            conn.execute("DELETE FROM system_events WHERE event_id = ?", (row[0],))
        conn.commit()
    finally:
        conn.close()


class TestFinding4VerifyChainCatchesDeletion:
    """Finding 4: chain-walk must catch deletion and truncation that
    per-event content-hash verification cannot."""

    def test_verify_all_events_passes_on_clean_chain(self):
        _seed_chain(5)
        result = verify_all_events()
        assert result["integrity"] == "PASS"

    def test_verify_chain_passes_on_clean_chain(self):
        _seed_chain(5)
        result = verify_chain()
        assert result["ok"] is True
        assert result["total"] == 5
        assert result["broken_at"] is None

    def test_verify_chain_catches_middle_deletion(self, tmp_path):
        """The exact attack the audit ran: delete a middle event,
        verify_chain must report ok=False with prior_hash mismatch."""
        _seed_chain(5)
        db_path = str(tmp_path / "test.db")
        _delete_event_by_index(db_path, 2)

        chain_result = verify_chain()
        assert chain_result["ok"] is False, (
            f"verify_chain must catch middle deletion. Got: {chain_result}"
        )
        assert chain_result["broken_at"] is not None
        assert "prior_hash mismatch" in (chain_result.get("broken_reason") or "")

    def test_verify_chain_catches_tail_truncation(self, tmp_path):
        """The audit's second attack: truncate the tail.

        UPDATED 2026-07-02 for Fable audit finding #1: the previous
        pin ("truncation is survivable — a chain-prefix is still a
        valid chain") was pinning the exact gap the Fable auditor
        confirmed with runnable repro. That gap was the CRITICAL
        finding — the ledger's non-repudiation promise defeated by
        the most natural attack.

        Fix landed via external head anchor in ledger_head_anchor
        table, atomic-updated with each event write. verify_chain
        now cross-checks the walked tip against the anchor; the
        anchor says "5 events ended at X" and the truncated ledger
        walks to "3 events ending at Y" → mismatch caught.

        This test now pins the CORRECT behavior: tail truncation
        must fail verify_chain with an anchor-mismatch reason.
        """
        _seed_chain(5)
        db_path = str(tmp_path / "test.db")
        _truncate_tail(db_path, keep_n=3)

        chain_result = verify_chain()
        assert chain_result["ok"] is False, (
            f"verify_chain must catch tail truncation (Fable finding #1). Got: {chain_result}"
        )
        # Reason should reference the anchor mismatch or tail truncation.
        reason = (chain_result.get("broken_reason") or "").lower()
        assert "anchor" in reason or "truncation" in reason, (
            f"expected anchor/truncation reason, got: {reason}"
        )

    def test_per_event_check_misses_deletion(self, tmp_path):
        """Critical: the OLD behavior. verify_all_events on a
        deletion-tampered ledger still reports PASS because every
        remaining event's content_hash is internally consistent —
        nothing checks the inter-event link. This pins WHY the audit
        finding was real."""
        _seed_chain(5)
        db_path = str(tmp_path / "test.db")
        _delete_event_by_index(db_path, 2)

        per_event = verify_all_events()
        assert per_event["integrity"] == "PASS", (
            "Per-event hash check passes after deletion — exactly the "
            "gap Finding 4 names. Chain verification is the protective "
            "layer."
        )


class TestFinding5PathExemption:
    """Finding 5: _is_low_friction_write must use directory-component
    matching with ..-resolution and code-file rejection, not unanchored
    substring matching."""

    def _write(self, file_path: str) -> dict:
        return {"tool_name": "Write", "tool_input": {"file_path": file_path}}

    def test_legitimate_exploration_markdown_is_exempt(self):
        assert (
            pre_hook._is_low_friction_write(self._write("exploration/aether/155_notes.md")) is True
        )

    def test_legitimate_family_letter_is_exempt(self):
        assert (
            pre_hook._is_low_friction_write(
                self._write("family/letters/aria-to-aether-2026-06-09.md")
            )
            is True
        )

    def test_legitimate_mansion_markdown_is_exempt(self):
        assert pre_hook._is_low_friction_write(self._write("mansion/study/notes.md")) is True

    def test_python_under_exploration_is_NOT_exempt(self):
        """Audit's concrete case: src/divineos/exploration/gates.py
        is code, not leisure writing, must not get the exemption."""
        assert (
            pre_hook._is_low_friction_write(self._write("src/divineos/exploration/gates.py"))
            is False
        )

    def test_python_under_mansion_is_NOT_exempt(self):
        """Audit's case: data/mansion/config.py is code."""
        assert pre_hook._is_low_friction_write(self._write("data/mansion/config.py")) is False

    def test_python_under_family_letters_is_NOT_exempt(self):
        """Audit's case: ~/work/family/letters/deploy_secrets.py is code."""
        assert (
            pre_hook._is_low_friction_write(
                self._write("home/user/work/family/letters/deploy_secrets.py")
            )
            is False
        )

    def test_path_traversal_to_core_is_NOT_exempt(self):
        """Audit's hardest case: exploration/../core/ledger.py resolves
        to core/ledger.py and must not get the exemption."""
        assert (
            pre_hook._is_low_friction_write(self._write("exploration/../core/ledger.py")) is False
        )

    def test_path_traversal_to_innocent_md_resolves_correctly(self):
        """exploration/../family/letters/x.md resolves to
        family/letters/x.md which IS a real letter location — should
        still exempt after path resolution."""
        assert (
            pre_hook._is_low_friction_write(self._write("exploration/../family/letters/x.md"))
            is True
        )

    def test_yml_under_mansion_is_NOT_exempt(self):
        """A YAML config under mansion is code-like configuration."""
        assert pre_hook._is_low_friction_write(self._write("mansion/config.yml")) is False

    def test_non_write_tool_returns_false(self):
        assert (
            pre_hook._is_low_friction_write(
                {"tool_name": "Bash", "tool_input": {"file_path": "exploration/x.md"}}
            )
            is False
        )

    def test_empty_file_path_returns_false(self):
        assert pre_hook._is_low_friction_write({"tool_name": "Write", "tool_input": {}}) is False

    def test_substring_match_in_filename_is_NOT_exempt(self):
        """A file whose NAME contains 'exploration' but lives in a
        non-exempt directory must not match — the old substring matcher
        would have matched on any path containing the string."""
        assert pre_hook._is_low_friction_write(self._write("docs/exploration_overview.md")) is False
