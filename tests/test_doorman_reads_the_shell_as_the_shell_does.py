"""The doorman reads commands with the shared shell reader. 2026-09-23.

Every command below is real: taken from the transcript of the night the doorman
misread four of them, or from the replay of all 22,849 Bash commands in this
house's transcripts that was run before the reader was switched. Each test says
which way the old reader failed on it.
"""

from __future__ import annotations

import time
import uuid
from pathlib import Path

import pytest

from divineos.core import work_item_doorman as doorman
from divineos.core.command_parsing import shell_write_targets

ROOT = Path(__file__).resolve().parents[1]


def _writes(command: str) -> list[str]:
    return doorman.paths_from_tool_call("Bash", {"command": command})


# --- false holds: the old reader walked across a quote into the next command --


@pytest.mark.parametrize(
    ("named", "command"),
    [
        ("ls", 'cp "family/letters/a.md" "$HOME/.divineos-shared/letters/" && ls -la "$HOME/x"'),
        ("-c", 'cp "family/letters/a.md" "$HOME/.divineos-shared/letters/"\nwc -c "$HOME/x"'),
        (
            ".venv/Scripts/python.exe",
            '.venv/Scripts/python.exe "$S/reach.py" > "$S/reach.json"\n.venv/Scripts/python.exe - x',
        ),
        ("2", 'divineos mansion council "q" > "$S/council.txt" 2>&1; echo rc=$?'),
        ("-2", "sed -i 's/a/b/' README.md && grep -c x README.md | tail -2"),
        ("head", "sed -i 's/402/406/g' CLAUDE.md README.md && grep -c 406 CLAUDE.md | head -3"),
    ],
)
def test_the_next_command_is_never_read_as_a_file(named: str, command: str) -> None:
    """Each of these named a file nobody was writing. The first four were
    refusals on real work on 2026-09-22/23 -- the fourth while this repair's
    own council walk was being loaded."""
    assert named not in _writes(command)


# --- misses: real writes the old reader could not see -----------------------


@pytest.mark.parametrize(
    ("command", "target"),
    [
        ('cp a.txt "src/divineos/new.py"', "src/divineos/new.py"),
        ("sed -i 's/a/b/' README.md && grep -c x README.md", "README.md"),
        ("sed -i -e '5d' -e '4d' docs/ARCHITECTURE.md", "docs/ARCHITECTURE.md"),
        ('echo x > "src/divineos/y.py"', "src/divineos/y.py"),
        ("git mv docs/a.md docs/archive/a.md", "docs/archive/a.md"),
        ("curl http://h/p#frag > out.txt", "out.txt"),
    ],
)
def test_a_real_write_is_seen_however_it_is_quoted(command: str, target: str) -> None:
    """A quoted destination escaped the regexes by design -- named as an
    accepted trade -- and sed followed by another command escaped by accident.
    `git mv` is the one case the new reader first LOST and the replay caught."""
    assert target in _writes(command)


# --- quoted text is data -----------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        'until [ "$(free)" \'>\' "5.0" ]; do sleep 20; done',
        "echo \\> not-a-file",
        'git commit -m "fix > thing; and | more"',
        "python -c 'assert n >= 0'",
        "cat > /dev/null <<'X'\necho hi > src/divineos/inside_a_heredoc.py\nX",
    ],
)
def test_a_quoted_operator_is_a_word(command: str) -> None:
    """The one new false hold the replay found in the new reader: a quoted `>`
    in a test comparison, read as a redirect once the quotes were stripped."""
    assert _writes(command) == []


def test_a_descriptor_before_a_redirect_is_not_an_argument() -> None:
    """`2>` is one redirect written as two tokens; the `2` is not a file."""
    assert sorted(shell_write_targets("cp a b 2>/dev/null")) == ["/dev/null", "b"]
    assert _writes("cp a b 2>/dev/null") == ["b"]


def test_an_unquoted_heredoc_is_still_scanned() -> None:
    """Knuth, on the 2026-09-22 walk: the shell expands inside an unquoted
    heredoc, so its body is not inert. Kept from the old reader."""
    assert "out.txt" in _writes("cat <<EOF\n$(echo x > out.txt)\nEOF")


# --- the first knock ---------------------------------------------------------


def _new_item_decision(monkeypatch, marks_missing: tuple[str, ...]):
    session = f"test-first-knock-{uuid.uuid4().hex[:8]}"
    landed = time.time() - 600
    monkeypatch.setattr(doorman, "head_commit_time", lambda: landed)
    monkeypatch.setattr(doorman, "missing_marks", lambda item_id, since: marks_missing)
    decision = doorman.decide(
        "Write", {"file_path": str(ROOT / "src/divineos/core/_first_knock.py")}, session=session
    )
    found = doorman.open_item_for_branch(session=session)
    if found:
        doorman.close_item(found[0])
    return decision


def test_work_done_before_the_first_edit_counts_on_the_first_knock(monkeypatch) -> None:
    """It used to refuse a new item on sight, listing all three stations
    without looking, and pass the same edit a moment later. Measured live
    2026-09-23: search, draft and walk all done, first knock said nothing had
    been searched."""
    decision = _new_item_decision(monkeypatch, marks_missing=())
    assert decision.allows, decision.message


def test_the_first_knock_still_holds_when_the_work_is_not_done(monkeypatch) -> None:
    """The control. Without it the test above passes on a door that stopped
    holding anything."""
    decision = _new_item_decision(monkeypatch, marks_missing=("rough draft",))
    assert not decision.allows
    assert "has landed" in decision.message, "a new item should say it is new"
    assert "rough draft" in decision.message or "draft" in decision.message


# --- work that continues across a landing (Aether's case 3) ---------------------


def _window_for(monkeypatch, trigger: str, changed: frozenset[str] | None) -> tuple[float, float]:
    """(window, previous landing) for an item opened just after a landing."""
    now = time.time()
    last, before = now - 100, now - 1000
    monkeypatch.setattr(doorman, "head_commit_time", lambda: last)
    monkeypatch.setattr(
        doorman, "_landings", lambda limit=2: [(last, "sha-last"), (before, "sha-before")]
    )
    monkeypatch.setattr(doorman, "_files_changed_by", lambda sha: changed)
    session = f"test-continue-{uuid.uuid4().hex[:8]}"
    branch = "test-branch-continuation"
    item_id = doorman.open_item(trigger=trigger, branch=branch, session=session)
    try:
        found = doorman.open_item_for_branch(branch=branch, session=session)
    finally:
        doorman.close_item(item_id)
    assert found is not None
    return found[1], before


def test_fixing_a_file_the_landing_changed_continues_that_work(monkeypatch) -> None:
    """Aether, 2026-09-23, from his store: the pre-push suite refused a push, he
    went to fix session-init-once.sh -- a file the landing had changed -- and the
    door refused him for missing marks that were sitting there from before it."""
    window, before = _window_for(
        monkeypatch,
        ".claude/hooks/session-init-once.sh",
        frozenset({".claude/hooks/session-init-once.sh"}),
    )
    assert window == before, "the window did not reach back to the landed work's own window"


def test_an_unrelated_file_does_not_inherit(monkeypatch) -> None:
    """The control, and September's propped door: a finished piece's marks must
    not pay for an edit the landing had nothing to do with."""
    window, before = _window_for(monkeypatch, "src/divineos/core/other.py", frozenset({"src/a.py"}))
    assert window > before


def test_unreadable_git_never_widens_the_window(monkeypatch) -> None:
    window, before = _window_for(monkeypatch, "src/a.py", None)
    assert window > before


# --- items stranded on another branch are named (Aether's case four) -----------


def _held_with(monkeypatch, other_branch: str | None):
    session = f"test-stranded-{uuid.uuid4().hex[:8]}"
    monkeypatch.setattr(doorman, "head_commit_time", lambda: time.time() - 600)
    monkeypatch.setattr(doorman, "missing_marks", lambda item_id, since: ("rough draft",))
    other = None
    if other_branch:
        other = doorman.open_item(
            trigger="src/divineos/core/hook_context_merge.py", branch=other_branch, session=session
        )
    try:
        decision = doorman.decide(
            "Write", {"file_path": str(ROOT / "src/divineos/core/_stranded.py")}, session=session
        )
    finally:
        if other:
            doorman.close_item(other)
        here = doorman.open_item_for_branch(session=session)
        if here:
            doorman.close_item(here[0])
    return decision


def test_an_item_left_open_on_another_branch_is_named(monkeypatch) -> None:
    """Aether's case four: his reach and walk sat on an item on the branch he
    left, and nothing said so. The refusal now does -- and still refuses."""
    decision = _held_with(monkeypatch, "fix/the-runway-meter-reads-the-real-trigger")
    assert not decision.allows, "naming the other item must never open the door"
    assert "fix/the-runway-meter-reads-the-real-trigger" in decision.message
    assert "hook_context_merge.py" in decision.message


def test_nothing_is_named_when_nothing_is_stranded(monkeypatch) -> None:
    decision = _held_with(monkeypatch, None)
    assert not decision.allows
    assert "ALSO OPEN" not in decision.message
