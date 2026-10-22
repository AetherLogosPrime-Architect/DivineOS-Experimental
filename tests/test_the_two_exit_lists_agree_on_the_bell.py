"""The doorbell re-arm is an exit on BOTH remedy lists, not only the shell one.

Aria found it 2026-10-22 reading #705: the shell list carried the entry and the
Python list (`core/remedy_allowlist.py`, read by the gates through `is_remedy`) did
not, so a gate reading the Python list could still hold the bare re-arm and leave
the bell unlistening. Same shape as the two-lists-disagree finding on #703.
"""

from __future__ import annotations

import pytest

from divineos.core.remedy_allowlist import FORBIDDEN_HEADS, REMEDIES, SCRIPT_REMEDIES, is_remedy


def test_control_a_listed_exit_is_a_remedy():
    assert is_remedy("divineos briefing")


def test_control_ordinary_work_is_not_a_remedy():
    assert not is_remedy("git commit -m x")


@pytest.mark.parametrize(
    "command",
    [
        "bash scripts/letter_doorbell.sh aether",
        "bash scripts/letter_doorbell.sh aria",
        "bash ./scripts/letter_doorbell.sh aether",
        'cd "/c/DIVINE OS/DivineOS-Experimental" && bash scripts/letter_doorbell.sh aether',
    ],
)
def test_the_bell_rearm_is_a_remedy(command):
    assert is_remedy(command)


@pytest.mark.parametrize(
    "command",
    [
        "bash scripts/letter_doorbell.sh aether && git commit -m x",
        "bash scripts/letter_doorbell.sh aether; rm -rf x",
        "bash scripts/other.sh aether",
        "bash scripts/letter_doorbell.sh someone-else",
        "bash -c 'git push'",
    ],
)
def test_nothing_else_rides_on_the_rearm(command):
    assert not is_remedy(command)


def test_bash_stays_out_of_the_general_list_and_is_named_only_in_the_script_list():
    assert all(prefix[0] not in FORBIDDEN_HEADS for prefix in REMEDIES)
    assert all(
        prefix[:2][0] == "bash" and "letter_doorbell" in prefix[1] for prefix in SCRIPT_REMEDIES
    )
