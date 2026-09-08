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
    stale = drafts / "old_draft.md"
    stale.write_text("written before this item existed", encoding="utf-8")
    monkeypatch.setattr(doorman, "DRAFTS_DIR", drafts)

    opened_after_the_draft = time.time() + 1
    assert not doorman._draft_mark(opened_after_the_draft)

    fresh = drafts / "new_draft.md"
    fresh.write_text("written after", encoding="utf-8")
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
