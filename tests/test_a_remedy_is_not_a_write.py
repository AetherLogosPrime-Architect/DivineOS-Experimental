"""A gate's own exit must not be locked by another gate.

2026-10-10, Aria. The date rolled over and one pre-registration came due. Three
gates then closed into a ring, each treating itself as the first thing to
satisfy:

  1. the overdue-review block refused every command, including `briefing` and
     `goal add`;
  2. the key that opens the build-flow gate needs the day's briefing, which (1)
     refused;
  3. the build-flow gate refused `prereg show`, `prereg reviewing` and
     `prereg assess` -- the overdue block's own prescribed exits -- because it
     classed any `prereg` command as a write to the store that owes a council
     walk.

Two repairs, one per ring link that is a rule and not a word-match bug:

  * the overdue block lets the two things every review needs first through
    (`briefing`, `goal add`), and nothing else it did not already allow;
  * the build-flow classifier does not count looking, or recording a review's
    outcome, as the building the walk is for. `prereg file` still owes one.

The controls matter more than the positives: a write must still be a write.
"""

import time

import pytest

from divineos.core.gravity_classifier import score_substrate_modification
from divineos.core.pre_registrations.store import (
    _get_connection,
    file_pre_registration,
    init_pre_registrations_tables,
)
from divineos.hooks.pre_tool_use_gate import _check_overdue_prereg_block

_D = "divi" + "neos"


def _fired(command: str) -> tuple[str, ...]:
    return tuple(score_substrate_modification("Bash", bash_command=command).fired_features)


# --- the classifier: looking, and recording a review, owe no walk -------------


@pytest.mark.parametrize(
    "command",
    [
        f"{_D} prereg show prereg-abc123",
        f"{_D} prereg list",
        f"{_D} prereg overdue",
        f"{_D} prereg windows",
        f"{_D} prereg summary",
        f"{_D} prereg reviewing prereg-abc123 --purpose 'read the evidence'",
        f"{_D} prereg assess prereg-abc123 --outcome INCONCLUSIVE --actor aria --notes 'x'",
        f"{_D} audit list",
        f"cd /tmp && {_D} prereg show prereg-abc123",
    ],
)
def test_looking_or_recording_a_review_owes_no_walk(command):
    assert "substrate-write-cli" not in _fired(command)


@pytest.mark.parametrize(
    "command",
    [
        f"{_D} prereg file x --claim a --success b --falsifier c --embarrassing d",
        f"{_D} audit submit x --round r",
        f"{_D} learn status",
        f"{_D} claim summary",
        f"{_D} decide list",
        f"{_D} journal save x",
        f"{_D} prereg export",
    ],
)
def test_a_real_write_still_owes_one(command):
    """Controls. `learn status` and `claim summary` are the shape Aria found
    waving a lesson whose TEXT spells a read verb through as a read: in a leaf
    command the third word is an argument, not a verb. `prereg export` is
    labelled a look by its name and writes files into docs, so it stays heavy:
    an exempted word has to be a true label."""
    assert "substrate-write-cli" in _fired(command)


@pytest.mark.parametrize(
    "command",
    [
        f"{_D} prereg show x && {_D} learn y",
        f"{_D} prereg assess x --outcome SUCCESS; {_D} prereg file z",
        f"{_D} prereg show x\n{_D} audit submit y",
    ],
)
def test_a_look_does_not_excuse_a_write_beside_it(command):
    """A clean segment cannot launder a different one: judged per segment."""
    assert "substrate-write-cli" in _fired(command)


def test_a_look_inside_a_substitution_still_fails_toward_scrutiny():
    assert "substrate-write-cli" in _fired(f"echo $({_D} prereg show x)")


# --- the contract: an exit one gate advertises must pass the other ------------


def test_every_exit_the_overdue_block_names_passes_the_build_gate():
    """The ring, as a test. The commands are taken from the block's OWN message,
    not from a list kept here, so editing the message or the classifier cannot
    quietly re-close it. Before this, two gates were each correct and the
    day could not start."""
    import re

    prereg_id = _one_overdue_review()
    decision = _check_overdue_prereg_block("echo hello")
    reason = decision["hookSpecificOutput"]["permissionDecisionReason"]
    exits = re.findall(r"divineos prereg (?:assess|reviewing)[^\n]*", reason)
    assert exits, "the block names no exit; the contract has nothing to check"
    for line in exits:
        concrete = line.replace("<id>", prereg_id).replace("<name>", "aria")
        assert "substrate-write-cli" not in _fired(concrete), concrete


# --- the overdue block: what any review needs first ---------------------------


def _one_overdue_review():
    init_pre_registrations_tables()
    prereg_id = file_pre_registration(
        mechanism="test-overdue-for-the-ring",
        claim="x",
        success_criterion="y",
        falsifier="z",
        review_window_days=7,
        actor="aria",
    )
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE pre_registrations SET review_ts = ? WHERE prereg_id = ?",
            (time.time() - 3 * 24 * 3600, prereg_id),
        )
        conn.commit()
    finally:
        conn.close()
    return prereg_id


@pytest.mark.parametrize(
    "command",
    [
        f"{_D} briefing",
        f"{_D} goal add 'clear the overdue review'",
        f"cd /tmp && {_D} briefing",
        f"cd /tmp && {_D} goal add 'x'",
    ],
)
def test_the_two_things_every_review_needs_first_are_not_blocked(command):
    _one_overdue_review()
    assert _check_overdue_prereg_block(command) is None


def test_a_goal_is_allowed_only_while_the_goal_gate_is_asking_for_one(monkeypatch):
    """Aether's point: a pinned test treats `goal add` as work the gate exists
    to stop. It is, once a goal exists. It is the exit only while the session
    has none, which is exactly when the other gate demands it."""
    from divineos.core import hud_state

    _one_overdue_review()
    monkeypatch.setattr(hud_state, "has_session_fresh_goal", lambda *a, **k: True)
    assert _check_overdue_prereg_block(f"{_D} goal add 'another one'") is not None
    monkeypatch.setattr(hud_state, "has_session_fresh_goal", lambda *a, **k: False)
    assert _check_overdue_prereg_block(f"{_D} goal add 'the first one'") is None


def test_the_seats_own_bell_can_be_turned_on_while_a_review_is_overdue(monkeypatch):
    """The one command that must never be blockable by a due date: it turns
    the letter bell on. Only this seat's own name, as a lone clause."""
    from divineos.core import sibling_audit_rounds

    _one_overdue_review()
    monkeypatch.setattr(sibling_audit_rounds, "this_seat", lambda: "aria")
    assert _check_overdue_prereg_block("bash scripts/letter_doorbell.sh aria") is None
    assert _check_overdue_prereg_block("bash scripts/letter_doorbell.sh aether") is not None
    assert _check_overdue_prereg_block("bash scripts/letter_doorbell.sh aria && rm x") is not None


@pytest.mark.parametrize(
    "command",
    [
        f"{_D} learn 'a lesson'",
        f"{_D} goal complete 1",
        f"{_D} briefing && rm -rf build",
        f"{_D} briefing; {_D} learn x",
        f"{_D} goal add x | tee out.txt",
        "echo hello",
    ],
)
def test_everything_else_is_still_blocked_while_a_review_is_overdue(command):
    """Controls: the block still blocks. Only the two prerequisites moved."""
    _one_overdue_review()
    assert _check_overdue_prereg_block(command) is not None
