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
