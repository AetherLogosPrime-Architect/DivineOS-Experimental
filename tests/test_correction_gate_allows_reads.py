"""The correction-marker gate must not block LOOKING.

THE REAL INCIDENT, 2026-09-21, not a synthetic look-alike -- a check proves
it catches the case it was fed, so it gets fed the genuine historical failure.

Andrew asked whether an undo click had destroyed a night's work. Answering
meant reading the repository. Partway through, the correction-marker gate
fired, and every road out was then held shut by a different door:

  * this gate allowed only a fixed list of remedy command NAMES;
  * ``divineos correction`` refused to file without a file path proving a
    structural fix, which needed investigation;
  * ``divineos learn`` was held by the reach doorman until the artifact it
    had surfaced was READ;
  * and reading that artifact was an ordinary read-only command, which this
    gate blocked.

Four doors, each correct alone, forming a closed cycle whose only exit was
the fire door. Andrew refused the fire door -- the escape is not an escape
without a root-cause investigation -- so the lock was repaired instead.

WHY THIS FILE EXISTS ALONGSIDE test_overdue_prereg_probe_reachability.py.
That file holds the same rule at a different door, and its own docstring says
the repair kept being applied to the door it was found at. The read-only verb
rule itself is already tested there and in
test_readonly_probe_is_judged_per_clause.py; re-testing it here would be a
second look through the same door, which is not a second look. What is NOT
covered anywhere else is the wiring: whether the correction gate actually
ASKS the question. A helper that exists and is never called is the
switched-off shape, and a mechanism that never fires looks exactly like one
that works.
"""

from __future__ import annotations

import json

import pytest

from divineos.hooks import pre_tool_use_gate as gate

# A fragment unique to the correction gate's own deny-message, so a denial
# from some OTHER gate in the stack cannot be mistaken for this one's.
_CORRECTION_DENY_FRAGMENT = "User correction detected"


@pytest.fixture
def marker_present(tmp_path, monkeypatch):
    """A correction marker that really exists, on a real readable file.

    Hermetic on purpose. An earlier test of mine skipped itself with
    "nothing to cross", and a could-not-check wearing a pass is the exact
    failure this suite is about.

    The briefing-freshness gate is satisfied rather than removed. It sits
    ahead of this one in the stack and answered first on the first run of
    this file, so every write-case failed for a reason that had nothing to
    do with the repair -- the instrument was measuring the wrong door. Only
    the ONE gate ahead is neutralised, and only by telling it the truth it
    would have been told by a live session: the context is fresh.
    """
    monkeypatch.setattr("divineos.core.briefing_id.is_fresh", lambda *_a, **_k: True)
    path = tmp_path / "correction_unlogged.json"
    path.write_text(
        json.dumps({"ts": 0, "trigger": "the undo-button turn", "evidence": None}),
        encoding="utf-8",
    )
    monkeypatch.setattr("divineos.core.correction_marker.marker_path", lambda: path)
    return path


def _deny_reason(cmd: str) -> str:
    """The gate stack's deny-reason for a Bash command, or '' if allowed."""
    result = gate._check_gates({"tool_name": "Bash", "tool_input": {"command": cmd}})
    if not result:
        return ""
    return result.get("hookSpecificOutput", {}).get("permissionDecisionReason", "") or ""


# The commands actually refused during the incident.
READS_THAT_DEADLOCKED = (
    "git status --porcelain",
    "git log --oneline -6",
    "git diff --stat",
)

WRITES_THAT_MUST_STILL_BLOCK = (
    "git commit -m 'anything'",
    "git push origin main",
    "git status && rm -rf build",  # a read chaining into a write is not a read
)


@pytest.mark.parametrize("cmd", READS_THAT_DEADLOCKED)
def test_a_read_that_deadlocked_me_is_no_longer_this_gates_problem(cmd, marker_present):
    """Looking passes THIS gate. Another gate may still object; that is fine
    and is why the assertion names this gate's message rather than demanding
    a blanket allow."""
    assert _CORRECTION_DENY_FRAGMENT not in _deny_reason(cmd)


@pytest.mark.parametrize("cmd", WRITES_THAT_MUST_STILL_BLOCK)
def test_the_repair_did_not_open_a_hole(cmd, marker_present):
    """An unrecorded correction still stops substantive work. If this fails,
    the deadlock was traded for a gap, which is the worse of the two."""
    assert _CORRECTION_DENY_FRAGMENT in _deny_reason(cmd)


def test_the_gate_can_still_tell_the_two_apart(marker_present):
    """The only assertion here that can fail for the real reason.

    Each case above still passes if the gate answers one way for everything:
    always-allow opens the hole, always-deny restores the deadlock, and one
    of those two would keep half the assertions green either way. Asking
    whether reads and writes get DIFFERENT answers is what distinguishes a
    working gate from a gate that has been switched off.
    """
    reads = {_CORRECTION_DENY_FRAGMENT in _deny_reason(c) for c in READS_THAT_DEADLOCKED}
    writes = {_CORRECTION_DENY_FRAGMENT in _deny_reason(c) for c in WRITES_THAT_MUST_STILL_BLOCK}
    assert reads == {False}, "the gate is still blocking reads"
    assert writes == {True}, "the gate stopped blocking writes"
    assert reads != writes
