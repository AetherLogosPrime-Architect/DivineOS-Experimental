"""Every way out a gate names must pass every gate that could be armed beside it.

Dad, 2026-10-10: *a gate should not be blocking its own remedy, nor should its
remedy be locked behind some other gate you cannot access ... no gates should be
bypassed; if a bypass was used the gate is broken and needs fixing.* The same
rule he gave on 2026-08-18, which made `core/remedy_allowlist.py`.

What this adds is the MEASURING the shell library's own comment says was named
three times and never run: take the shared list of exits and run each one
through the gate stack with a review overdue, and read the lists against each
other. Measured on 2026-10-11, before this file existed:

  * five exits were refused by the overdue block: `andrew-correction integrate`,
    `andrew-correction defer`, `psf mark-done`, `his pending`, `his sort`. The
    gate's skip list keys two-word entries ('andrew-correction defer') but is
    matched on the first word only, so those entries could never match. A
    deadlock waiting for the day the correction gate and an overdue review were
    armed at once.
  * `("divineos", "council")` is a bare group prefix, so `council
    authorize-bypass` and `council emergency-skip` were ordinary remedies that
    every gate asking the shared list let through. The fire door must stay
    reachable; it must not be a routine remedy.
  * `audit submit-round` / `prepare-merge` are prescribed by the merge path and
    were not on the list, so filing a review round owed a fresh council walk per
    command.

WHAT THIS DOES NOT COVER, said so silence is not read as coverage: the shell
hooks are not run by subprocess here. A probe of the real build-flow hook with
an empty store let EVERY command through, including a control that must be
refused, so that instrument was blind and its readings are not used. The count
below makes adding a hook a decision, not a drift.
"""

import json
import re
import time
from pathlib import Path

import click
import pytest

from divineos.core.pre_registrations.store import (
    _get_connection,
    file_pre_registration,
    init_pre_registrations_tables,
)
from divineos.core.remedy_allowlist import REMEDIES, is_remedy
from divineos.hooks.pre_tool_use_gate import _check_overdue_prereg_block, _is_bypass_command

_D = "divi" + "neos"
_REPO = Path(__file__).resolve().parent.parent

# Verbs that name an emergency exit. They may stay reachable some other way;
# they must never be a routine remedy that every gate lets through.
_EMERGENCY = re.compile(r"bypass|emergency|authorize")


def _overdue_review() -> None:
    init_pre_registrations_tables()
    prereg_id = file_pre_registration(
        mechanism="test-every-exit-passes-every-gate",
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


def _typed(entry: tuple[str, ...]) -> str:
    """An entry as a person would type it, with a placeholder argument."""
    words = list(entry)
    if entry == (_D, "goal", "add"):
        return f"{_D} goal add 'a goal'"
    if len(words) < 3:
        words.append("x")
    return " ".join(words)


# -- the shared list is closed: no emergency exit rides on a group prefix ------


def _real_subcommands(prefix: tuple[str, ...]) -> list[str]:
    from divineos.cli import cli

    ctx = click.Context(cli)
    node = cli
    for word in prefix[1:]:
        if not isinstance(node, click.Group):
            return []
        node = node.get_command(ctx, word)
        if node is None:
            return []
    if not isinstance(node, click.Group):
        return []
    return list(node.list_commands(click.Context(node)))


@pytest.mark.parametrize("entry", REMEDIES, ids=lambda e: " ".join(e))
def test_no_exit_prefix_reaches_an_emergency_exit(entry):
    for sub in _real_subcommands(entry):
        if _EMERGENCY.search(sub):
            command = " ".join((*entry, sub))
            assert not is_remedy(command), (
                f"{command!r} is a routine remedy through the group prefix "
                f"{' '.join(entry)!r}. An emergency exit is reached some other way."
            )


def test_the_control_can_see_a_refusal():
    """The instrument must be able to find the case it should find."""
    assert _real_subcommands((_D, "council")), "no council subcommands found: the probe is blind"
    assert not is_remedy(f"{_D} council authorize-bypass")
    assert not is_remedy(f"{_D} council emergency-skip")
    assert is_remedy(f"{_D} council log --edit x")


# -- the audit commands the merge path prescribes ------------------------------


@pytest.mark.parametrize(
    "command",
    [
        f"{_D} audit submit-round 'a focus' --actor aletheia",
        f"{_D} audit prepare-merge round-abc",
        f"{_D} audit submit 'a finding' --round r --actor aletheia",
        f"{_D} audit file-external-confirm --round round-abc --actor aletheia --branch b",
    ],
)
def test_the_merge_path_exits_are_remedies(command):
    assert is_remedy(command)


@pytest.mark.parametrize(
    "command",
    [
        f"{_D} audit submit 'x' --round r --actor user",
        f"{_D} audit submit 'x' --round r --actor=user",
        f"{_D} audit submit 'x' --round r --actor 'user'",
        f"{_D} audit file-external-confirm round-abc --actor user",
    ],
)
def test_words_in_his_voice_keep_their_pause(command):
    """Aether 2026-10-11: a finding filed with --actor user is Dad's confirm, and
    the walk before it is one of the few pauses before words are put in his voice."""
    assert not is_remedy(command)


@pytest.mark.parametrize(
    "command",
    [
        f"{_D} audit submit 'x' --round r --actor User",
        f"{_D} audit submit 'x' --round r --actor USER",
        f"{_D} audit submit 'x' --round r --actor \"$A\"",
        f"{_D} audit submit 'x' --round r --actor \"$(printf user)\"",
        f'{_D} audit submit \'x\' --round r --actor "us""er"',
        f"{_D} audit submit 'x' --round r --actor",
        f"{_D} audit submit 'x' --round r",
        f"{_D} audit file-external-confirm round-abc",
        f"{_D} audit submit 'x' --round r --actor someone-unlisted",
    ],
)
def test_a_spelling_the_pattern_misses_keeps_the_pause_too(command):
    """Aether's hold, 2026-10-11: the first version blocked `--actor user` and let
    everything else through, so a spelling it missed filed in Dad's voice with no
    pause. The rule is now the other way round: only a literal actor from a short
    closed list that is not Dad is a remedy, and a miss fails toward the pause."""
    assert not is_remedy(command)


@pytest.mark.parametrize(
    "actor", ["aletheia", "aria", "aether", "grok", "gemini", "claude-opus-5-5"]
)
def test_a_named_actor_that_is_not_dad_is_a_remedy(actor):
    assert is_remedy(f"{_D} audit submit 'x' --round r --actor {actor}")
    assert is_remedy(f"{_D} audit submit 'x' --round r --actor={actor}")


def test_words_inside_a_quoted_lesson_are_data_not_options():
    """Aether's small ones: a lesson that merely MENTIONS `-o` or `goal add` is a
    lesson, not an output option and not a second goal."""
    assert is_remedy(f'{_D} learn "set -o pipefail was missing"')
    _overdue_review()
    assert _check_overdue_prereg_block(f'{_D} learn "never run goal add twice"') is None


@pytest.mark.parametrize(
    "command",
    [
        f"{_D} briefing --output x.md",
        f"{_D} learn x --out notes.md",
        f"{_D} briefing -o x.md",
    ],
)
def test_a_remedy_that_writes_where_it_is_told_is_not_a_remedy(command):
    """Aletheia attacked `briefing --output` on 619. The shared list takes any
    arguments, so asking it first brought the hole back; the neighbouring
    closed-shape test caught it."""
    assert not is_remedy(command)


def test_a_set_option_setup_link_is_not_an_output_option():
    """The control for the rule above: `set -o pipefail` is a setup link."""
    assert is_remedy(f"set -o pipefail && {_D} learn 'x'")


# -- every exit passes the python gate stack with a review overdue --------------


def test_every_exit_passes_the_gates_while_a_review_is_overdue():
    _overdue_review()
    refused = []
    for entry in REMEDIES:
        command = _typed(entry)
        if not (_is_bypass_command(command) or _check_overdue_prereg_block(command) is None):
            refused.append(command)
    assert not refused, f"exits an overdue review would refuse: {refused}"


def test_the_control_sees_the_overdue_block_refuse():
    """Without this the test above passes on a harness that cannot refuse."""
    _overdue_review()
    assert _check_overdue_prereg_block("rm -rf build") is not None
    assert _check_overdue_prereg_block("make build") is not None


def test_two_goals_chained_are_still_refused_on_an_overdue_day():
    """619's rule: a goal is allowed only while the goal gate is asking, and
    never as a way to keep adding goals. Asking the shared list first must not
    undo that (Aether, 2026-10-11)."""
    _overdue_review()
    assert _check_overdue_prereg_block(f"{_D} goal add 'a' && {_D} goal add 'b'") is not None


# -- a gate added without a decision about this list ---------------------------

# How many PreToolUse hook commands settings.json wires when this was written.
# Adding one makes this fail, which is the point: ask whether the new gate asks
# the shared list, then change the number.
_PRE_TOOL_USE_HOOKS_WHEN_WRITTEN = 34


def _pre_tool_use_hook_count() -> int:
    settings = json.loads((_REPO / ".claude" / "settings.json").read_text(encoding="utf-8"))
    return sum(len(group.get("hooks", [])) for group in settings["hooks"]["PreToolUse"])


def test_a_new_pretooluse_hook_is_a_decision_not_a_drift():
    assert _PRE_TOOL_USE_HOOKS_WHEN_WRITTEN == _pre_tool_use_hook_count(), (
        f"{_pre_tool_use_hook_count()} PreToolUse hooks are wired, the list was written "
        f"against {_PRE_TOOL_USE_HOOKS_WHEN_WRITTEN}. Does the new gate ask the shared "
        "remedy list (core/remedy_allowlist.py), and is its own exit on it? Then change "
        "the number."
    )
