"""Both controls for the bash-trap lint (Aria 2026-08-10).

The false-positive half matters more than the true-positive half. Bash is my
most-used tool; a lint that fires on correct commands is a lint I will
disable, and then the traps are back with a disabled guard in front of them.
Angelou's finding on walk-eba3cfa75aa4, and the reason every case below is a
command actually issued during this session rather than an invented string.
"""

from __future__ import annotations

import pytest

from divineos.hooks.bash_trap_lint import check, should_block

# --- commands that MUST fire (all real, all from 2026-08-10) ---

FIRES = [
    ('python -c "import divineos"', "wrong-python-tree"),
    ('cd "C:/repo" && python -c "from divineos.core.council_walk import x"', "wrong-python-tree"),
    ('grep -c "aether" letters.jsonl', "grep-c-counts-lines"),
    ("git push -u origin branch | tail -3", "exit-code-lost-in-pipe"),
    ('divineos mansion council "problem" --audit | tail -60', "truncating-a-surface-i-must-read"),
    ("printf 'echo hi\\n' >> .git/hooks/commit-msg", "append-may-land-below-exit"),
]

# --- commands that MUST NOT fire (also all real, all correct) ---

QUIET = [
    'PYTHONPATH=src python -c "import divineos; print(divineos.__file__)"',
    "python -m pytest tests/test_andrew_given.py -q --tb=short",
    'grep -n "andrew_correction_commands" src/divineos/cli/__init__.py',
    'grep -rln "prereg-required-before-infra" --include=*.sh .',
    "git log --oneline -2 | head -3",
    "divineos walk status walk-eba3cfa75aa4",
    "divineos briefing",
    "ls src/divineos/core/ | grep -i council",
]


@pytest.mark.parametrize(("command", "expected"), FIRES, ids=[t for _, t in FIRES])
def test_known_traps_fire(command: str, expected: str) -> None:
    names = {f.trap.name for f in check(command)}
    assert expected in names, f"{expected} did not fire on: {command}"


@pytest.mark.parametrize("command", QUIET, ids=range(len(QUIET)))
def test_correct_commands_stay_quiet(command: str) -> None:
    fires = check(command)
    assert not fires, f"false positive {[f.trap.name for f in fires]} on: {command}"


def test_every_rule_blocks() -> None:
    """Andrew 2026-08-10: "YOU CANNOT WARN THE OPTIMIZER."

    The warn tier is gone. It was wallpaper twice over -- once by design
    (text without consequence is invisible to the optimizer) and once by
    accident (a PreToolUse hook's exit-0 output never reaches the composer,
    verified by probe rather than assumed).
    """
    assert should_block(check('python -c "x"')) is True
    assert should_block(check('grep -c "x" f')) is True
    assert should_block(check("git push origin main | tail")) is True


def test_ack_token_buys_the_exception() -> None:
    """Lamport's objection survives, structurally instead of verbally.

    grep -c IS right when you want lines, so the escape exists -- but it
    costs one act of naming intent rather than nothing, which is the whole
    difference between this and a warning.
    """
    assert check('grep -c "x" f') != []
    assert check('grep -c "x" f  #lines-ok') == []
    assert check('python -c "x"  #tree-ok') == []


def test_ack_tokens_are_all_distinct() -> None:
    """A shared token would let one exception silently buy another rule."""
    from divineos.hooks.bash_trap_lint import TRAPS

    acks = [trap.ack for trap in TRAPS]
    assert len(acks) == len(set(acks))


def test_empty_is_not_a_safety_claim() -> None:
    """An empty result means no KNOWN pattern matched — nothing more."""
    assert check("") == []
    assert check("some novel trap nobody has hit yet") == []


def test_every_trap_carries_its_incident() -> None:
    """Knuth: a rule without provenance gets deleted by a future reader."""
    from divineos.hooks.bash_trap_lint import TRAPS

    for trap in TRAPS:
        assert len(trap.why) > 60, f"{trap.name} has no real incident recorded"
        assert len(trap.instead) > 15, f"{trap.name} forbids without supplying the correct form"
