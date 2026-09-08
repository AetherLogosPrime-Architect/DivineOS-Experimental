"""The doorman holds the front of the build flow. See core/work_item_doorman.py.

These pin the properties the fifteen-lens walk said the design turns on, and
each one names the finding it came from. A test whose reason is not written
down is a test the next person deletes when it goes red.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from divineos.core import work_item_doorman as doorman

ROOT = Path(__file__).resolve().parents[1]


def test_the_exempt_list_is_the_one_the_merge_check_reads() -> None:
    """One list, two consumers.

    A second copy would drift, and the drift would be invisible until a
    guardrail file slipped through one of them. This is the whole reason the
    doorman does not carry its own idea of what counts as prose.
    """
    assert doorman.EXEMPT_LIST == ROOT / "scripts" / "review_exempt_paths.txt"
    prefixes = doorman.load_exempt_prefixes()
    assert prefixes is not None, "the exempt list did not read"
    assert "family/letters/" in prefixes


def test_an_unreadable_exempt_list_holds_rather_than_guesses(monkeypatch) -> None:
    """Three states, never two.

    An unreadable list is not an empty one. Treating unknown as permissive is
    the exact collapse that produced a 404 being read as 'not protected'.
    """
    monkeypatch.setattr(doorman, "load_exempt_prefixes", lambda: None)
    decision = doorman.decide("Write", {"file_path": "src/divineos/core/x.py"})
    assert decision.state is doorman.State.CANNOT_CHECK
    assert not decision.allows
    assert "could not read" in decision.message


def test_prose_does_not_open_work() -> None:
    """If letters were held, the first thing refused would be the letter
    telling Aether the doorman exists."""
    for path in ("family/letters/a.md", "exploration/aether/1.md", "dreams/aria/2.md"):
        assert not doorman.needs_an_item([str(ROOT / path)]), path


def test_code_paths_do_open_work() -> None:
    for path in ("src/divineos/core/x.py", "scripts/check_thing.sh", "tests/test_x.py"):
        assert doorman.needs_an_item([str(ROOT / path)]), path


def test_paths_outside_the_repo_are_not_this_gates_business() -> None:
    assert not doorman.needs_an_item(["C:/Users/aethe/.divineos-shared/letters/x.md"])


# --- Schneier finding 4: the two cheapest routes around the door -------------


@pytest.mark.parametrize(
    "command",
    [
        "cat > src/divineos/core/sneaky.py <<EOF\nx=1\nEOF",
        "echo hi >> src/divineos/core/sneaky.py",
        "sed -i s/a/b/ src/divineos/core/sneaky.py",
        "tee src/divineos/core/sneaky.py",
        "cp /tmp/x.py src/divineos/core/sneaky.py",
    ],
)
def test_the_shell_is_not_a_side_door(command: str) -> None:
    """The cheapest route in the attack tree, and it is not hypothetical.

    I wrote this module's own design draft through a heredoc an hour before
    writing the function that catches heredocs. A gate that watches only the
    edit tools holds the front door with the side door standing open.
    """
    paths = doorman.paths_from_tool_call("Bash", {"command": command})
    assert any("sneaky.py" in p for p in paths), f"missed the write in: {command}"


def test_a_read_only_command_is_not_a_write() -> None:
    """A gate that fires on everything is noise, and noise gets removed."""
    assert not doorman.paths_from_tool_call("Bash", {"command": "git status --short"})
    assert not doorman.paths_from_tool_call("Bash", {"command": "grep -rn foo src/"})


def test_the_doorman_can_be_asked_about_its_own_source() -> None:
    """Route 2 in the tree: turn off the gate and the whole thing collapses to
    one leaf. Its own files are code and are held like anything else."""
    assert doorman.needs_an_item([str(ROOT / "src/divineos/core/work_item_doorman.py")])
    assert doorman.needs_an_item([str(ROOT / ".claude/hooks/work-item-doorman.sh")])


# --- the shape of the refusal ------------------------------------------------


def test_the_refusal_speaks_in_sentences_not_station_numbers() -> None:
    """Aether's constraint from his walk, and the reason is the reader.

    Whoever meets this message is tired and has spent six months being talked
    past. 'no rough draft has been written' is a thing a person can picture.
    'station 1 MISSING' is not.
    """
    text = doorman._refusal_text(
        "wi-test", ("src/divineos/core/x.py",), list(doorman.REQUIRED_BEFORE_BUILD), opened_now=True
    )
    assert "no rough draft has been written" in text
    assert "MISSING" not in text
    assert "station 1" not in text.lower()
    # And the escape is named in the refusal itself, because an escape you have
    # to go looking for is an escape that turns into a silent workaround.
    assert "work-item bypass" in text


def test_malformed_hook_input_stands_aside() -> None:
    """A gate that refuses on its own parse errors teaches that it is noise."""
    assert doorman.gate_from_stdin("not json at all").allows
    assert doorman.gate_from_stdin("").allows


# --- Lamport finding 7: happens-before, not wall clock -----------------------


def test_marks_must_belong_to_this_item_not_an_older_one(tmp_path, monkeypatch) -> None:
    """A walk from last week does not pay for this week's build.

    The comparison is against the item's own opening, which is only
    well-defined because the row opens at the reach.
    """
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    # Both fixtures clear the content floor: this test is about WHEN a draft
    # was written, not how much of it there is.
    stale = drafts / "old_draft.md"
    stale.write_text("written before this item existed. " * 4, encoding="utf-8")
    monkeypatch.setattr(doorman, "DRAFTS_DIR", drafts)

    opened_after_the_draft = time.time() + 1
    assert not doorman._draft_mark(opened_after_the_draft)

    fresh = drafts / "new_draft.md"
    fresh.write_text("written after the item opened. " * 4, encoding="utf-8")
    assert doorman._draft_mark(opened_after_the_draft - 60)


# --- the three defects wiring found in its first minute alive ---------------


def test_the_doorman_does_not_refuse_the_draft_it_demands() -> None:
    """The closed loop, and the worst thing dogfooding found.

    It asked for a rough draft and held every write to the place drafts live,
    so the only way to satisfy it was to escape it. A gate whose own
    instruction cannot be followed teaches that its instructions are decoration.
    """
    assert not doorman.needs_an_item([str(ROOT / "docs/drafts/anything.md")])


def test_a_recorded_bypass_actually_opens_the_door() -> None:
    """It did not, at first: the command wrote a row and the gate never read
    it, so the escape was a receipt for a door that stayed shut."""
    item_id = doorman.open_item(trigger="tests")
    try:
        assert not doorman.has_bypass(item_id)
        doorman.record_bypass(item_id, "a reason long enough to be a real sentence")
        assert doorman.has_bypass(item_id)
    finally:
        doorman.close_item(item_id)


@pytest.mark.parametrize(
    "command",
    ["mv a $HOME/scratch/b", "cp x ~/y", "cat > $TMPDIR/out.txt"],
)
def test_an_unexpanded_variable_is_not_a_repo_path(command: str) -> None:
    """Resolving `$HOME/...` relative to the working directory turned an
    outside-the-repo write into a false hold. Found by being refused on a
    scratchpad path one minute after wiring."""
    assert not doorman.paths_from_tool_call("Bash", {"command": command})


# --- the two real holes Aether game-walked, and their closures ---------------


def test_a_change_on_disk_is_seen_even_when_the_command_was_not(monkeypatch) -> None:
    """The worst route: a script writes the file, so the command the door reads
    carries one path and it is outside the tree.

    The claim here is deliberately the small one -- the write is not prevented,
    it is made impossible to hide. One gets through; nothing after it does.
    """
    monkeypatch.setattr(doorman, "dirty_code_paths", lambda: frozenset({"src/divineos/core/x.py"}))
    assert doorman._files_written_unseen(frozenset()) == ("src/divineos/core/x.py",)
    # Already-dirty files at opening are not a walk-around; only new ones are.
    assert doorman._files_written_unseen(frozenset({"src/divineos/core/x.py"})) == ()
    # And an unreadable tree yields no accusation, because unknown is not guilt.
    monkeypatch.setattr(doorman, "dirty_code_paths", lambda: None)
    assert doorman._files_written_unseen(frozenset()) == ()


def test_the_walkaround_message_is_a_different_register(monkeypatch) -> None:
    """Two states need two messages. A hold says 'this has not happened yet';
    a walk-around says 'something already changed that I never saw', and that
    is the graver of the two. One message for both teaches one mood."""
    text = doorman._walkaround_text("wi-x", ("src/divineos/core/x.py",), ["rough draft"])
    assert "came in through a window" in text
    assert "work-item bypass" in text
    hold = doorman._refusal_text("wi-x", ("a.py",), ["rough draft"], opened_now=False)
    assert "came in through a window" not in hold


def test_an_item_does_not_prop_the_door_for_another_session() -> None:
    """One item satisfied once at the top of a branch used to buy every edit
    afterwards. A commit is not the natural end -- the build runs through many
    -- but the propped door matters most where the person who opened it is
    gone, and that is a session boundary."""
    branch = "test-branch-for-session-scope"
    item_id = doorman.open_item(trigger="t", branch=branch, session="session-one")
    try:
        assert doorman.open_item_for_branch(branch=branch, session="session-one") is not None
        assert doorman.open_item_for_branch(branch=branch, session="session-two") is None
    finally:
        doorman.close_item(item_id)


def test_an_empty_draft_is_not_a_draft(tmp_path, monkeypatch) -> None:
    """The two halves of this build disagreed about the same file: an empty
    draft passed my door and was refused by Aether's checker. One build giving
    two answers about one file is worse than either answer."""
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    monkeypatch.setattr(doorman, "DRAFTS_DIR", drafts)
    thin = drafts / "thin.md"
    thin.write_text("idea", encoding="utf-8")
    assert not doorman._draft_mark(0)
    thin.write_text("x" * (doorman._DRAFT_FLOOR_BYTES + 1), encoding="utf-8")
    assert doorman._draft_mark(0)


def test_an_item_does_not_survive_the_commit_that_ends_its_work(monkeypatch) -> None:
    """Session-scoping was too loose and Andrew proved it inside one turn.

    Minutes after the doorman shipped I edited an unrelated hook with no
    search, draft or walk, and the door stood aside because the item satisfied
    for the doorman's own build was still open and still carrying its marks.
    A commit is where a piece of work ends, so that is where the item ends.
    """
    branch = "test-branch-for-commit-close"
    item_id = doorman.open_item(trigger="t", branch=branch, session="s")
    try:
        monkeypatch.setattr(doorman, "head_commit_time", lambda: time.time() - 3600)
        assert doorman.open_item_for_branch(branch=branch, session="s") is not None
        monkeypatch.setattr(doorman, "head_commit_time", lambda: time.time() + 1)
        assert doorman.open_item_for_branch(branch=branch, session="s") is None
    finally:
        doorman.close_item(item_id)


def test_an_unreadable_commit_time_does_not_close_anything(monkeypatch) -> None:
    """Unknown is not a landing. Closing on a failed lookup would refuse work
    for no reason, which is the two-valued collapse in its permissive-looking
    costume: here the harm is a false hold rather than a false pass."""
    branch = "test-branch-for-unknown-commit"
    item_id = doorman.open_item(trigger="t", branch=branch, session="s")
    try:
        monkeypatch.setattr(doorman, "head_commit_time", lambda: None)
        assert doorman.open_item_for_branch(branch=branch, session="s") is not None
    finally:
        doorman.close_item(item_id)


def test_the_marks_window_reaches_back_to_the_last_commit(monkeypatch) -> None:
    """A replacement item inherits the work-in-progress's artifacts.

    Commit-closing fired on the edit that added it, correctly, and then the
    fresh item refused work whose search, draft and walk had been done minutes
    earlier for that same piece. The artifacts were real; the window was wrong.
    Everything since the last commit belongs to the work in progress -- and a
    walk done BEFORE that commit still does not count, which is the protection
    the window exists for.
    """
    branch = "test-branch-for-marks-window"
    item_id = doorman.open_item(trigger="t", branch=branch, session="s")
    try:
        earlier_commit = time.time() - 600
        monkeypatch.setattr(doorman, "head_commit_time", lambda: earlier_commit)
        found = doorman.open_item_for_branch(branch=branch, session="s")
        assert found is not None
        assert found[1] == earlier_commit, "the window did not reach back to the commit"
    finally:
        doorman.close_item(item_id)


def test_a_bypass_needs_a_real_reason() -> None:
    """Truth #12: a bypass is a tool, and the guard is that it is counted and
    named. A one-word reason is an unrecorded bypass wearing a record."""
    from click.testing import CliRunner

    from divineos.cli import cli

    result = CliRunner().invoke(cli, ["work-item", "bypass", "wi-x", "--reason", "later"])
    assert result.exit_code != 0
    assert "the whole point of the escape" in result.output


def test_the_gate_command_exits_two_when_it_holds() -> None:
    """The hook contract: exit 2 puts the text in front of me. Exit 0 is a pass,
    and a gate that cannot say no in the language the harness reads is a gate
    that never fires."""
    from click.testing import CliRunner

    from divineos.cli import cli

    payload = json.dumps(
        {"tool_name": "Write", "tool_input": {"file_path": "src/divineos/core/anything.py"}}
    )
    result = CliRunner().invoke(cli, ["work-item", "gate"], input=payload)
    assert result.exit_code == 2
