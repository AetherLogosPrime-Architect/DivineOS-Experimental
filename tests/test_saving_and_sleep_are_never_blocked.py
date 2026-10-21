"""Saving and sleep are never blocked: the commands the compaction ritual runs pass every gate that reads the lists.

Dad, 2026-10-21: "NOTHING should ever block sleep or extraction", and journal entries and other personal writing
must not owe council paperwork or be stopped. 2026-10-19: "saving should never be a blocked action at any point
whatsoever." Aether's test covers the ritual's hard stop on writes into the memory folder; this covers the other
gates, the ones that read the shared lists of ways out.

THE PAIR IS THE POINT. "These commands pass" alone is satisfied by a gate that lets everything through, so each
check has a control that must still be refused: a push, a commit, a delete.

WHAT THIS DOES NOT COVER, said so silence is not read as coverage: it reads the two lists and runs the Python
overdue block; it does not run the shell hooks (a probe of one with an empty store let every command through, so
that instrument is blind). The shell list is checked by reading its pattern, not by running a hook.
"""

import re
from pathlib import Path

import pytest
from _prereg_helpers import make_due_by_use

from divineos.core.pre_registrations.store import (
    Outcome,
    file_pre_registration,
    init_pre_registrations_tables,
    record_outcome,
)
from divineos.core.remedy_allowlist import is_remedy
from divineos.hooks.pre_tool_use_gate import _check_overdue_prereg_block

_D = "divi" + "neos"
_SHELL_LIST = (
    Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "lib" / "remedy_allowlist.sh"
)

#: What the ritual and personal writing run. Each records into my own stores and edits no code.
SAVING_AND_SLEEP = [
    f"{_D} extract",
    f"{_D} sleep",
    f"{_D} sleep --dry-run",
    f"{_D} journal save 'an entry'",
    f"{_D} rest start",
    f"{_D} rest close",
    f"{_D} dream list",
    f"{_D} savor save 'a moment'",
    f"{_D} feel -v 0.5 -a 0.5 --dom 0.5 -d 'a state'",
]

#: Must stay refused. If one of these passes, the lists have become a way around the gates.
STILL_GUARDED = [
    "git push origin main",
    "git commit -m x",
    "rm -rf some_folder",
    f"{_D} council authorize-bypass --tool x",
]


@pytest.mark.parametrize("command", SAVING_AND_SLEEP)
def test_the_shared_list_lets_saving_and_sleep_through(command):
    assert is_remedy(command), command


@pytest.mark.parametrize("command", STILL_GUARDED)
def test_the_dangerous_commands_are_still_not_remedies(command):
    assert not is_remedy(command), command


def _shell_pattern() -> re.Pattern[str]:
    text = _SHELL_LIST.read_text(encoding="utf-8")
    found = re.search(r"^_REMEDY_PATTERNS='(.*)'$", text, re.MULTILINE)
    assert found, "the shell list's pattern was not found: this reader is blind, not the list clean"
    return re.compile(found.group(1).replace("[[:space:]]", r"\s"))


@pytest.mark.parametrize("command", SAVING_AND_SLEEP)
def test_the_shell_list_the_council_gate_reads_lets_them_through_too(command):
    assert _shell_pattern().match(command), command


def test_the_shell_reader_can_see_a_refusal():
    """The instrument must find the case it should find: a push is not in the shell list."""
    assert not _shell_pattern().match("git push origin main")
    assert not _shell_pattern().match(f"{_D} council emergency-skip")


def _close(prereg_id: str) -> None:
    record_outcome(prereg_id=prereg_id, actor="andrew", outcome=Outcome.SUCCESS, notes="cleanup")


@pytest.mark.parametrize("command", SAVING_AND_SLEEP)
def test_a_review_that_reached_its_count_does_not_stop_saving_or_sleep(command):
    init_pre_registrations_tables()
    pid = file_pre_registration(
        mechanism="saving-and-sleep-survey",
        claim="X",
        success_criterion="Y",
        falsifier="Z",
        review_window_days=7,
        actor="aether",
    )
    make_due_by_use(pid)
    try:
        assert _check_overdue_prereg_block("git commit -m x") is not None, (
            "the control must be refused"
        )
        assert _check_overdue_prereg_block(command) is None, command
    finally:
        _close(pid)
