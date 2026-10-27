"""Filing a review round, a finding or a relayed confirm is not an edit of the house.

2026-10-12: the merge path prints `audit submit-round`, `audit submit` (the operator's
finding) and `audit file-external-confirm` as its own steps. The build-flow gate counted
each as a substrate edit and asked for a council walk and a game-walk first: six filings in
one night, each recording what another person had already said. The python exit list and the
merge gate already treated them as exits; this gate's own list did not.

The real function is lifted out of the hook, never copied, as the neighbouring tests do.
"""

import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
HOOK = REPO / ".claude" / "hooks" / "check-council-required.sh"
NL = chr(10)
_END = "return all(_is_freed(seg) for seg in acts)"
_D = "divi" + "neos"


@pytest.fixture(scope="module")
def is_filing():
    src = HOOK.read_text(encoding="utf-8")
    start = src.rindex(NL, 0, src.index("_ARTIFACT_FILING_COMMANDS = ("))
    namespace: dict = {}
    exec(compile(src[start : src.index(_END) + len(_END)], "hook", "exec"), namespace)
    return namespace["_is_artifact_filing"]


@pytest.mark.parametrize(
    "command",
    [
        f"{_D} audit submit-round 'focus' --actor aria",
        f"{_D} audit submit 'title' --round round-x --actor user --severity LOW",
        f"{_D} audit file-external-confirm --round round-x --actor aletheia --branch b",
    ],
)
def test_the_merge_path_filings_are_not_edits(command, is_filing):
    assert is_filing(command) is True


# The narrowing (Aether's question on 631, 2026-10-24, and Aria's grep): a CONFIRMS filed with --actor user puts words in
# Dad's voice, and the only deliberate pause on that path was this gate's paperwork. The one check that his quoted words
# were really typed by him lives in `file-confirm --andrew-said`, not in `audit submit`. So a user-actor CONFIRMS still
# owes the paperwork until `audit submit` runs that same check. Actor and title are matched TOGETHER: a title alone
# is easy to phrase around, and an actor alone would stop freeing his plain findings.
@pytest.mark.parametrize(
    "command",
    [
        f"{_D} audit submit 'CONFIRMS: this is fine' --round round-x --actor user --severity LOW",
        f"{_D} audit submit 'confirms: lower case' --round round-x --actor user",
        f"{_D} audit submit --actor user --round round-x 'CONFIRMS: actor first'",
        f"{_D} audit submit 'CONFIRMS: equals form' --round round-x --actor=user",
    ],
)
def test_a_confirms_filed_in_his_name_still_owes_the_paperwork(command, is_filing):
    assert is_filing(command) is False


@pytest.mark.parametrize(
    "command",
    [
        f"{_D} audit submit 'CONFIRMS: relayed' --round round-x --actor aletheia --severity LOW",
        f"{_D} audit submit 'a plain finding' --round round-x --actor user --severity LOW",
        f"{_D} audit submit 'a finding that mentions confirms later' --round round-x --actor user",
    ],
)
def test_control_a_relayed_confirm_and_his_plain_findings_stay_freed(command, is_filing):
    assert is_filing(command) is True


# 2026-10-27 (walk-969a822af7fd): the three commands every merge path prints as its next step.
# Aether paid five council walks to land two fixes, and these were the commands that cost them.
@pytest.mark.parametrize(
    "command",
    [
        f"{_D} audit patch-id --branch aria/x",
        f"{_D} audit prepare-merge round-x",
        f"{_D} audit prepare-merge round-x --pr-title 'A title'",
        f"{_D} audit list",
        f"{_D} audit list --tag surprise",
    ],
)
def test_the_printing_commands_every_merge_path_names_are_freed(command, is_filing):
    assert is_filing(command) is True


# They only PRINT, so the one way they can write is a redirect. The older entries are matched on
# the prefix alone and a trailing redirect rides along with them; these three do not widen that.
@pytest.mark.parametrize(
    "command",
    [
        f"{_D} audit prepare-merge round-x > body.md",
        f"{_D} audit prepare-merge round-x >> docs/ARCHITECTURE.md",
        f"{_D} audit list > docs/ARCHITECTURE.md",
        f"{_D} audit patch-id --branch b 2> out.txt",
        f"{_D} audit list &> out.txt",
    ],
)
def test_a_redirect_on_a_printing_command_still_owes_the_paperwork(command, is_filing):
    assert is_filing(command) is False


@pytest.mark.parametrize(
    "command",
    [
        f"{_D} audit prepare-merge round-x && git commit -qm sneak",
        f"{_D} audit list; git commit -qm sneak",
        f"{_D} audit patch-id --branch b | tee kiln.md",
    ],
)
def test_a_printing_command_does_not_free_what_is_chained_behind_it(command, is_filing):
    assert is_filing(command) is False


@pytest.mark.parametrize(
    "command",
    [
        f"{_D} audit prepare-artifact",
        f"{_D} audit resolve find-x --status RESOLVED",
        f"{_D} audit summary",
        f"{_D} audit pr-merge-check 631",
    ],
)
def test_the_neighbouring_audit_commands_are_not_freed_by_accident(command, is_filing):
    assert is_filing(command) is False


# Aether RAN these two strings against the first version (2026-10-27) and both came back freed: the
# shell runs what is inside a command substitution before the freed command starts, so a printing
# command could carry any other command. The $ and the backtick are built with chr() so this file
# does not itself contain a live substitution.
_DOLLAR, _TICK = chr(36), chr(96)


@pytest.mark.parametrize(
    "command",
    [
        f'{_D} audit list --round "{_DOLLAR}(touch made_by_substitution)"',
        f"{_D} audit list --round {_TICK}touch made_by_backtick{_TICK}",
        f"{_D} audit prepare-merge {_DOLLAR}(git commit -qm sneak)",
        f"{_D} audit patch-id --branch {_TICK}rm x{_TICK}",
    ],
)
def test_a_substitution_inside_a_printing_command_still_owes_the_paperwork(command, is_filing):
    assert is_filing(command) is False


@pytest.mark.parametrize(
    "command",
    [
        f"{_D} audit list <(touch made_by_procsub)",
        f"{_D} audit list --round <(touch x)",
        f"{_D} audit prepare-merge round-x < /etc/hostname",
        f"{_D} audit patch-id --branch ( touch x )",
    ],
)
def test_a_process_substitution_or_subshell_on_a_printing_command_owes_the_paperwork(
    command, is_filing
):
    """Found by me running shapes through the real function before the walk, not by reading it:
    Aether tested the output form (a greater-than parenthesis) and it was refused, but the
    input form came back freed, and it runs the command inside the parentheses."""
    assert is_filing(command) is False


@pytest.mark.parametrize(
    "command",
    [
        f"{_D} audit patch-idx --branch b",
        f"{_D} audit list-clean",
        f"{_D} audit prepare-merges round-x",
    ],
)
def test_a_neighbour_that_only_starts_with_the_same_letters_is_not_freed(command, is_filing):
    """Whole words only: a bare prefix freed audit list-clean and any later name that began the
    same way. (Aether, 2026-10-27.)"""
    assert is_filing(command) is False


def test_control_the_check_can_still_say_no(is_filing):
    """CONTROL: refusing ordinary work is what makes the passes above mean something."""
    assert is_filing("git commit -qm sneak") is False
    assert is_filing(f"{_D} audit file-external-confirm --round r && git commit -qm sneak") is False
    assert is_filing(f"{_D} audit summary") is False
