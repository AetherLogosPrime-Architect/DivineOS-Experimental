"""Tests for _check_overdue_prereg_block in pre_tool_use_gate.

2026-07-07 Andrew fix: pre-registration reviews used to be a briefing
surface that could be scrolled past. "No warnings.. they do not work."
The doorman now blocks non-bypass tool use until every overdue pre-reg
either records its outcome or is explicitly deferred. Paired with the
review-days default drop 30 -> 7 so overdue actually bites within the
week.
"""

from __future__ import annotations

import time

from divineos.core.pre_registrations.store import (
    Outcome,
    _get_connection,
    file_pre_registration,
    init_pre_registrations_tables,
    record_outcome,
)
from divineos.hooks.pre_tool_use_gate import _check_overdue_prereg_block


def _backdate_review(prereg_id: str, days_ago: float) -> None:
    """Move a pre-reg's review_ts into the past to simulate overdue.

    file_pre_registration always calls time.time() so we can't create an
    already-overdue row directly through the public API. This helper
    backdates in the DB — test-only, matches the pattern used by other
    time-sensitive tests in the suite.
    """
    ts = time.time() - days_ago * 24 * 3600
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE pre_registrations SET review_ts = ? WHERE prereg_id = ?",
            (ts, prereg_id),
        )
        conn.commit()
    finally:
        conn.close()


def test_no_preregs_no_block():
    """Clean slate — no pre-registrations, no block. Returns None."""
    init_pre_registrations_tables()
    assert _check_overdue_prereg_block() is None


def test_open_prereg_not_yet_overdue_does_not_block():
    """Future review date, OPEN outcome — no block."""
    init_pre_registrations_tables()
    file_pre_registration(
        mechanism="test-not-yet-due",
        claim="The mechanism will do X",
        success_criterion="Observe Y within window",
        falsifier="Observe Z during window",
        review_window_days=7,
        actor="aether",
    )
    assert _check_overdue_prereg_block() is None


def test_overdue_prereg_blocks_with_deny_message():
    """Review date in the past, OPEN outcome — block fires with a deny
    decision containing the prereg id and the recovery command."""
    init_pre_registrations_tables()
    prereg_id = file_pre_registration(
        mechanism="test-overdue-mechanism",
        claim="The mechanism will do X",
        success_criterion="Observe Y within window",
        falsifier="Observe Z during window",
        review_window_days=7,
        actor="aether",
    )
    _backdate_review(prereg_id, days_ago=3)
    decision = _check_overdue_prereg_block()
    assert decision is not None
    reason = decision["hookSpecificOutput"]["permissionDecisionReason"]
    assert "OVERDUE PRE-REGISTRATIONS" in reason
    assert prereg_id[:20] in reason
    assert "divineos prereg assess" in reason


def test_recording_outcome_clears_the_block():
    """After recording a terminal outcome the pre-reg is no longer OPEN,
    so the overdue gate returns None again."""
    init_pre_registrations_tables()
    prereg_id = file_pre_registration(
        mechanism="test-outcome-clears",
        claim="X",
        success_criterion="Y",
        falsifier="Z",
        review_window_days=7,
        actor="aether",
    )
    _backdate_review(prereg_id, days_ago=3)
    assert _check_overdue_prereg_block() is not None
    record_outcome(
        prereg_id=prereg_id,
        actor="andrew",
        outcome=Outcome.SUCCESS,
        notes="Verified the mechanism held over the review window.",
    )
    assert _check_overdue_prereg_block() is None


def test_deferring_clears_the_block():
    """DEFERRED is also a terminal outcome, so it clears the block —
    matches the operator-facing recovery text in the deny message."""
    init_pre_registrations_tables()
    prereg_id = file_pre_registration(
        mechanism="test-defer-clears",
        claim="X",
        success_criterion="Y",
        falsifier="Z",
        review_window_days=7,
        actor="aether",
    )
    _backdate_review(prereg_id, days_ago=3)
    assert _check_overdue_prereg_block() is not None
    record_outcome(
        prereg_id=prereg_id,
        actor="andrew",
        outcome=Outcome.DEFERRED,
        notes="Need more time before I can honestly assess this outcome.",
    )
    assert _check_overdue_prereg_block() is None


class TestReadOnlyProbesPassWhileOverdue:
    """A gate must not block the evidence its own remedy requires.

    Andrew 2026-06-29, already load-bearing in _is_bypass_command:
    "no gate should ever be blocking you from using what you need to
    clear the gate." Clearing this gate means assessing a pre-reg, and an
    honest assessment needs evidence.

    It blocked that evidence twice on 2026-08-13. Assessing
    prereg-ec9c9ee7eeda meant running `divineos already-built` -- the very
    command that pre-reg was about -- and the gate refused it. Assessing
    prereg-81b268695979 meant querying the bypass store for a baseline,
    and the gate refused that too. Both were recorded DEFERRED with
    "CANNOT-LOOK" for no reason but this gate. A gate that blocks looking
    produces fabricated outcomes or defensive deferrals, not assessment.

    Andrew 2026-08-13, on finding it named-but-unfixed: "why dont you fix
    the gate?"
    """

    def _overdue(self) -> str:
        init_pre_registrations_tables()
        prereg_id = file_pre_registration(
            mechanism="readonly-probe-fixture",
            claim="X",
            success_criterion="Y",
            falsifier="Z",
            review_window_days=7,
            actor="aether",
        )
        _backdate_review(prereg_id, days_ago=3)
        assert _check_overdue_prereg_block() is not None, "fixture must be blocking"
        return prereg_id

    def test_the_command_a_prereg_was_about_is_not_blocked(self):
        """prereg-ec9c9ee7eeda's own subject, refused live."""
        self._overdue()
        assert _check_overdue_prereg_block('divineos already-built "letter monitor"') is None

    def test_read_only_git_is_not_blocked(self):
        self._overdue()
        assert _check_overdue_prereg_block("git ls-remote origin some-branch") is None
        assert _check_overdue_prereg_block("git log --oneline -3") is None
        assert _check_overdue_prereg_block("git rev-parse HEAD") is None

    def test_cd_preface_still_reads_as_a_probe(self):
        """Every Bash call in this codebase prefixes `cd DIR && `."""
        self._overdue()
        assert _check_overdue_prereg_block("cd /some/dir && git status") is None

    def test_mutation_is_still_blocked(self):
        """The gate's actual purpose survives the allowance."""
        self._overdue()
        for cmd in ("git push origin main", "git commit -m x", "rm -rf /tmp/x"):
            assert _check_overdue_prereg_block(cmd) is not None, cmd

    def test_probe_word_with_mutation_attached_is_blocked(self):
        """F22's decoy shape: a safe word does not launder a compound."""
        self._overdue()
        assert _check_overdue_prereg_block("git log && rm -rf /tmp/x") is not None
        assert _check_overdue_prereg_block("git status; git push") is not None

    def test_no_command_still_blocks(self):
        """Non-Bash tools supply no command and must not slip through."""
        self._overdue()
        assert _check_overdue_prereg_block("") is not None


def test_multiple_overdue_all_named_in_message():
    """Deny message lists overdue IDs (capped at 5 preview + more-count)
    so the operator knows exactly which pre-regs need attention."""
    init_pre_registrations_tables()
    ids = []
    for i in range(3):
        prereg_id = file_pre_registration(
            mechanism=f"multi-overdue-{i}",
            claim="X",
            success_criterion="Y",
            falsifier="Z",
            review_window_days=7,
            actor="aether",
        )
        _backdate_review(prereg_id, days_ago=3)
        ids.append(prereg_id)
    decision = _check_overdue_prereg_block()
    assert decision is not None
    reason = decision["hookSpecificOutput"]["permissionDecisionReason"]
    assert "3 pre-registration(s)" in reason
    for prereg_id in ids:
        assert prereg_id[:20] in reason
