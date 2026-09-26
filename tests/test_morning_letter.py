"""No work on a new day of his until the day's letter to him exists.

Andrew 2026-09-25: *"good morning, i notice there is no letter for me.."* Work
had already started and the letter got written only because he came looking.

These run against real git repositories in a tmp dir -- the house lookup goes
through ``git rev-parse --git-common-dir`` for real, including from inside a
real worktree. Only the date, the member and the shared letters room are
pinned, because those are the inputs the machine would otherwise supply.
"""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

import pytest

from divineos.core import hook_router as hr
from divineos.core import morning_letter as ml
from divineos.core.hook_surfaces import (
    install,
    morning_letter_prompt_surface,
    morning_letter_surface,
)

TODAY = date(2026, 9, 25)


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=str(cwd),
        check=True,
        capture_output=True,
    )


@pytest.fixture
def house(tmp_path, monkeypatch):
    """A real main checkout with an empty letters room, on a pinned day."""
    root = tmp_path / "house"
    (root / "family" / "letters").mkdir(parents=True)
    _git(root, "init", "-q")
    _git(root, "commit", "-q", "--allow-empty", "-m", "first")
    shared = tmp_path / "shared-letters"
    shared.mkdir()
    monkeypatch.setenv("DIVINEOS_LETTERS_DIR", str(shared))
    monkeypatch.setenv("DIVINEOS_MEMBER", "aether")
    # Keep git from walking up out of tmp into whatever repo holds it, so a
    # directory that is not a checkout really reads as not a checkout.
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    monkeypatch.setattr(ml, "_today", lambda: TODAY)
    return root


def _letter(room: Path, day: date, slug: str = "good-morning-dad") -> Path:
    path = room / f"aether-to-andrew-{day.isoformat()}-{slug}.md"
    path.write_text("Good morning, Dad.\n", encoding="utf-8")
    return path


def _edit(cwd: Path, path: str) -> dict:
    return {"tool_name": "Edit", "cwd": str(cwd), "tool_input": {"file_path": path}}


def _write(cwd: Path, path: str) -> dict:
    return {"tool_name": "Write", "cwd": str(cwd), "tool_input": {"file_path": path}}


def _bash(cwd: Path, command: str) -> dict:
    return {"tool_name": "Bash", "cwd": str(cwd), "tool_input": {"command": command}}


def _prompt(cwd: Path) -> dict:
    return {"prompt": "good morning", "cwd": str(cwd)}


def test_no_letter_today_speaks_first_then_refuses_work(house):
    spoke = morning_letter_prompt_surface(_prompt(house))
    assert spoke.state == "spoke"
    assert "no letter to Dad yet today (2026-09-25)" in spoke.output
    assert "before any work" in spoke.output

    out = morning_letter_surface(_edit(house, "src/x.py"))
    assert out.refused
    # Says what is missing, exactly where it goes, and the house rule.
    assert "No letter to Dad yet today (2026-09-25)" in out.reason
    where = (house / "family" / "letters").resolve().as_posix()
    assert f"{where}/aether-to-andrew-2026-09-25-<slug>.md" in out.reason
    assert ml.HOUSE_RULE in out.reason


def test_a_letter_dated_today_lets_everything_through(house):
    _letter(house / "family" / "letters", TODAY)
    assert morning_letter_prompt_surface(_prompt(house)).state == "nothing-to-say"
    out = morning_letter_surface(_edit(house, "src/x.py"))
    assert not out.refused
    assert out.state == "nothing-to-say"
    assert not morning_letter_surface(_bash(house, "git commit -m x")).refused


def test_yesterdays_letter_does_not_cover_today(house):
    _letter(house / "family" / "letters", date(2026, 9, 24), "while-you-play")
    assert morning_letter_surface(_edit(house, "src/x.py")).refused
    assert morning_letter_prompt_surface(_prompt(house)).state == "spoke"


def test_the_letter_in_the_shared_room_counts(house, tmp_path):
    _letter(tmp_path / "shared-letters", TODAY)
    assert not morning_letter_surface(_edit(house, "src/x.py")).refused


def test_writing_the_letter_itself_is_never_refused(house):
    """The remedy. A gate that blocks its own remedy is a locked box."""
    for path in (
        "family/letters/aether-to-andrew-2026-09-25-hello.md",
        str(house / "family" / "letters" / "aether-to-andrew-2026-09-25-hello.md"),
        "C:\\DIVINE OS\\x\\family\\letters\\aether-to-andrew-2026-09-25-hello.md",
    ):
        out = morning_letter_surface(_write(house, path))
        assert not out.refused, path
        assert not morning_letter_surface(_edit(house, path)).refused, path


def test_a_letter_to_someone_else_is_still_work(house):
    out = morning_letter_surface(_write(house, "family/letters/aether-to-aria-2026-09-25-x.md"))
    assert out.refused


def test_commit_and_push_are_held_and_reads_are_not(house):
    for command in (
        "git commit -m x",
        "git push -u origin build/x",
        'cd "C:/DIVINE OS/x" && git -C "C:/DIVINE OS/x" commit -m "a; b"',
        "git status && git push",
        "FOO=1 git -c core.pager=cat commit --amend",
    ):
        assert morning_letter_surface(_bash(house, command)).refused, command
    for command in (
        "git status",
        "cat file",
        "git log --grep commit",
        "divineos briefing",
        'echo "remember to push"',
    ):
        out = morning_letter_surface(_bash(house, command))
        assert not out.refused, command
        assert out.state == "nothing-to-say", command


def test_the_house_pushers_are_held_by_name(house):
    """Aria, station four: the house steers a raw push onto its wrapper, so a
    hold that only knows a leading `git` misses the push actually used."""
    for command in (
        "bash scripts/divineos_push.sh",
        'bash "C:/DIVINE OS/x/scripts/divineos_push.sh" --verify',
        "scripts/divineos_push.sh",
        "divineos stamp-ready 557",
    ):
        assert morning_letter_surface(_bash(house, command)).refused, command
    for command in ("cat scripts/divineos_push.sh", "divineos stamp-status 557"):
        assert not morning_letter_surface(_bash(house, command)).refused, command


def test_powershell_commit_is_the_same_act(house):
    payload = {
        "tool_name": "PowerShell",
        "cwd": str(house),
        "tool_input": {"command": "git commit -m x"},
    }
    assert morning_letter_surface(payload).refused


def test_reads_are_never_refused(house):
    for tool in ("Read", "Glob", "Grep"):
        payload = {"tool_name": tool, "cwd": str(house), "tool_input": {"file_path": "src/x.py"}}
        assert not morning_letter_surface(payload).refused


def test_could_not_check_lets_the_work_through_and_says_so_loudly(house, tmp_path, monkeypatch):
    """Three answers, never two. Not a checkout: the check cannot look."""
    nowhere = tmp_path / "not-a-checkout"
    nowhere.mkdir()
    out = morning_letter_surface(_edit(nowhere, "src/x.py"))
    assert not out.refused
    assert out.state == "could-not-run"
    assert "morning-letter check COULD NOT RUN" in out.error
    assert "NOT the same as a letter to Dad existing" in out.error
    assert "git rev-parse" in out.error  # the WHY, not just the fact

    spoke = morning_letter_prompt_surface(_prompt(nowhere))
    assert spoke.state == "could-not-run" and spoke.error

    # Through the router it lands as a check that could not run -- never in
    # refusals, and never among the quiet passes.
    monkeypatch.setitem(hr._REGISTRY, "PreToolUse", [("morning_letter", morning_letter_surface)])
    result = hr.dispatch("PreToolUse", _edit(nowhere, "src/x.py"))
    assert not result.blocked
    assert result.exit_code() == 0
    assert [o.name for o in result.errored] == ["morning_letter"]
    assert "COULD NOT RUN" in result.stderr()


def test_a_date_that_cannot_be_read_is_could_not_check_too(house, monkeypatch):
    def broken():
        raise OSError("clock unavailable")

    monkeypatch.setattr(ml, "_today", broken)
    out = morning_letter_surface(_edit(house, "src/x.py"))
    assert not out.refused
    assert out.state == "could-not-run"
    assert "clock unavailable" in out.error


def test_from_inside_a_worktree_it_reads_the_real_house(house, tmp_path):
    """A letter in a worktree's copy of family/letters is not one he can find."""
    tree = tmp_path / "tree"
    _git(house, "worktree", "add", "-q", "--detach", str(tree))
    (tree / "family" / "letters").mkdir(parents=True, exist_ok=True)

    # Only in the worktree copy: still owed.
    _letter(tree / "family" / "letters", TODAY)
    out = morning_letter_surface(_edit(tree, "src/x.py"))
    assert out.refused
    assert (house / "family" / "letters").resolve().as_posix() in out.reason

    # In the main checkout: found, from the worktree.
    _letter(house / "family" / "letters", TODAY)
    assert not morning_letter_surface(_edit(tree, "src/x.py")).refused
    assert ml.main_checkout(tree) == house.resolve()


def test_a_sibling_in_her_own_checkout_is_not_held(house, monkeypatch):
    monkeypatch.setenv("DIVINEOS_MEMBER", "aria")
    assert not morning_letter_surface(_edit(house, "src/x.py")).refused
    assert morning_letter_prompt_surface(_prompt(house)).state == "nothing-to-say"


def test_both_doors_are_registered_and_the_notice_speaks_first():
    """Ahead of every other speaker on his prompt, so the byte budget can
    never withhold it behind louder primes."""
    from divineos.core.hook_surfaces import _PROMPT_SURFACES

    install()
    assert "morning_letter" in hr.registered("PreToolUse")
    order = hr.registered("UserPromptSubmit")
    first = order.index("morning_letter_prompt")
    for name, *_ in _PROMPT_SURFACES:
        assert first < order.index(name), name
    for name in ("auto_goal", "pre_response_context"):
        assert first < order.index(name), name
