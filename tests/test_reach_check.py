"""The doorman must refuse a disposition made without opening the artifact.

Andrew 2026-08-06: *"a forced thinking stage that asks you what you know and
if you have reached for it or applied it, with its own doorman to prove you
did."*

The load-bearing test in this file is `test_not_relevant_is_not_exempt`.
Every other refusal path is ordinary validation; that one is the design
decision, and if it ever gets relaxed the whole mechanism reverts to a report
that can be scrolled past.
"""

from __future__ import annotations

import pytest

from divineos.core import reach_check
from divineos.core.reach_check import ReachCheckError

GOOD_REASON = "read it end to end; it covers the case and I applied it here"


@pytest.fixture(autouse=True)
def _tables():
    reach_check.init_reach_tables()


def _item(artifact: str = "src/divineos/core/prior_art.py") -> reach_check.ReachItem:
    """One undisposed item, written directly so the test does not depend on
    what prior_art happens to find in this checkout."""
    import time
    import uuid

    from divineos.core.knowledge import _get_connection

    check_id = f"reach-test-{uuid.uuid4().hex[:8]}"
    item_id = f"ri-test-{uuid.uuid4().hex[:8]}"
    conn = _get_connection()
    conn.execute(
        "INSERT INTO reach_checks (check_id, symptom, opened_at) VALUES (?, ?, ?)",
        (check_id, "test symptom", time.time()),
    )
    conn.execute(
        "INSERT INTO reach_items (item_id, check_id, artifact, origin) VALUES (?, ?, ?, ?)",
        (item_id, check_id, artifact, "branch:test@abc123"),
    )
    conn.commit()
    return reach_check.ReachItem(item_id, check_id, artifact, "branch:test@abc123")


def test_disposition_refused_when_artifact_never_opened():
    item = _item()
    with pytest.raises(ReachCheckError) as exc:
        reach_check.dispose(item.item_id, reach_check.APPLIED, GOOD_REASON)
    assert "never opened" in str(exc.value)


def test_not_relevant_is_not_exempt():
    """The design decision. Judging relevance unread IS the failure mode.

    If this test is ever changed to allow not_relevant through without
    evidence, the mechanism no longer catches the class it was built for --
    every historical miss would have been waved off as not-relevant by
    someone who had not opened the file.
    """
    item = _item()
    with pytest.raises(ReachCheckError) as exc:
        reach_check.dispose(item.item_id, reach_check.NOT_RELEVANT, GOOD_REASON)
    assert "never opened" in str(exc.value)
    assert "not_relevant" in str(exc.value)


def test_read_tool_on_the_artifact_clears_the_doorman():
    item = _item()
    result = reach_check.dispose(
        item.item_id,
        reach_check.APPLIED,
        GOOD_REASON,
        tool_calls_in_turn=(("Read", "C:/repo/src/divineos/core/prior_art.py"),),
    )
    assert result.disposition == reach_check.APPLIED
    assert result.evidence == "tool:Read:prior_art.py"


def test_git_show_counts_as_reading():
    """Friction register G6: a file on an unmerged branch is read via git show,
    and a gate blind to that route demands a consult it cannot see."""
    item = _item()
    result = reach_check.dispose(
        item.item_id,
        reach_check.SUPERSEDED,
        GOOD_REASON,
        command_texts=("git show 1e260bab:src/divineos/core/prior_art.py",),
    )
    assert result.evidence == "cmd:prior_art.py"


def test_reading_a_different_file_does_not_clear_it():
    """Any-consult-counts is the shape of the verify-before-build gate. Here
    the evidence must name THIS artifact, or the check would pass on unrelated
    reading."""
    item = _item()
    with pytest.raises(ReachCheckError):
        reach_check.dispose(
            item.item_id,
            reach_check.APPLIED,
            GOOD_REASON,
            tool_calls_in_turn=(("Read", "C:/repo/src/divineos/core/holding.py"),),
        )


def test_cli_artifact_needs_the_command_run_not_a_file_read():
    item = _item(artifact="cli:reach")
    with pytest.raises(ReachCheckError):
        reach_check.dispose(item.item_id, reach_check.APPLIED, GOOD_REASON)
    result = reach_check.dispose(
        item.item_id,
        reach_check.APPLIED,
        GOOD_REASON,
        command_texts=("divineos reach status",),
    )
    assert result.evidence == "cmd:reach"


def test_empty_reason_refused():
    item = _item()
    with pytest.raises(ReachCheckError) as exc:
        reach_check.dispose(
            item.item_id,
            reach_check.APPLIED,
            "read it",
            tool_calls_in_turn=(("Read", "src/divineos/core/prior_art.py"),),
        )
    assert "at least" in str(exc.value)


def test_unknown_disposition_refused():
    item = _item()
    with pytest.raises(ReachCheckError):
        reach_check.dispose(
            item.item_id,
            "maybe_later",
            GOOD_REASON,
            tool_calls_in_turn=(("Read", "src/divineos/core/prior_art.py"),),
        )


def test_disposition_is_append_only():
    item = _item()
    evidence = (("Read", "src/divineos/core/prior_art.py"),)
    reach_check.dispose(item.item_id, reach_check.APPLIED, GOOD_REASON, tool_calls_in_turn=evidence)
    with pytest.raises(ReachCheckError) as exc:
        reach_check.dispose(
            item.item_id, reach_check.SUPERSEDED, GOOD_REASON, tool_calls_in_turn=evidence
        )
    assert "already disposed" in str(exc.value)


def test_gate_blocks_while_an_item_is_undisposed_and_names_it():
    item = _item(artifact="src/divineos/core/gate_test_artifact.py")
    blocked, message = reach_check.gate_status()
    assert blocked
    assert item.artifact in message

    reach_check.dispose(
        item.item_id,
        reach_check.NOT_RELEVANT,
        GOOD_REASON,
        tool_calls_in_turn=(("Read", item.artifact),),
    )
    _, after = reach_check.gate_status()
    assert item.artifact not in after


def test_check_with_no_prior_art_is_clear_not_blocking():
    """NOT FOUND is a real outcome. A symptom with no prior art must not
    manufacture a block -- that would train the gate into noise."""
    check = reach_check.open_check("zzqqxx-no-such-artifact-anywhere-zzqqxx")
    assert check.items == []
    assert check.clear
