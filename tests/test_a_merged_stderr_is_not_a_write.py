"""`2>&1` and a redirect to /dev/null write nothing, so they do not make a look heavy.

2026-10-13 (the GATE-GATE). The overdue-review block prescribes `prereg reviewing` and `prereg
assess`; the council gate exempts both as remedies. I typed them with `2>&1 | tail -4` tacked on,
the council gate read the bare `>` as a file write, and the exit from one lock was shut by the
other. The bare commands passed; the decoration is what deadlocked me, and the refusal never said so.

The two redirects below are the two I add to nearly every command: merge the error stream into the
output, or throw it away. Neither touches a file. Every redirect that DOES name a file stays heavy,
and the existing tests in test_a_remedy_is_not_a_write.py pin that side.
"""

from __future__ import annotations

import pytest

from divineos.core.gravity_classifier import _runs_divineos_verb

_VERBS = ("audit", "claim", "learn", "prereg", "decide", "feel", "compass-ops", "journal")
_D = "divineos"


def _heavy(command: str) -> bool:
    return _runs_divineos_verb(command, _VERBS)


@pytest.mark.parametrize(
    "command",
    [
        f"{_D} prereg show prereg-x 2>&1",
        f'{_D} prereg reviewing prereg-x --purpose "p" 2>&1 | tail -4',
        f"{_D} prereg show prereg-x 2>&1 | head -30",
        f'{_D} prereg reviewing prereg-x --purpose "p" 2>&1 | grep -v noise | tail -4',
        f"{_D} prereg show prereg-x 2>/dev/null",
        f"{_D} prereg show prereg-x > /dev/null",
        f"{_D} prereg show prereg-x >/dev/null 2>&1",
        f"{_D} prereg show prereg-x &>/dev/null",
        f"{_D} prereg show prereg-x 1>&2",
        f"{_D} prereg show prereg-x 2>NUL",
        f'{_D} prereg assess prereg-x --outcome INCONCLUSIVE --actor a --notes "n" 2>&1',
    ],
)
def test_a_harmless_redirect_leaves_a_look_or_a_remedy_light(command: str) -> None:
    assert not _heavy(command), f"a harmless redirect made this heavy: {command}"


@pytest.mark.parametrize(
    "command",
    [
        f"{_D} prereg show prereg-x > out.txt",
        f"{_D} prereg show prereg-x >> out.txt",
        f"{_D} prereg show prereg-x 2> err.txt",
        f"{_D} prereg show prereg-x >&out.txt",
        f"{_D} prereg show prereg-x &>out.txt",
        f"{_D} prereg show prereg-x 2>&1 > out.txt",
        f"{_D} prereg show prereg-x 2>&1 | tee out.txt",
        f"{_D} prereg show prereg-x >| out.txt",
        f"{_D} prereg show prereg-x > /dev/nullfile",
    ],
)
def test_a_redirect_to_a_real_file_still_makes_it_heavy(command: str) -> None:
    assert _heavy(command), f"a redirect that writes a file went unnoticed: {command}"


def test_control_the_filing_verb_is_heavy_and_the_bare_remedy_is_light() -> None:
    # If the classifier were blind in one direction, the two lists above could pass for the wrong reason.
    assert _heavy(f'{_D} prereg file "m" --claim c')
    assert not _heavy(f'{_D} prereg reviewing prereg-x --purpose "p"')


def test_the_refusal_for_a_shell_command_says_what_makes_a_look_heavy() -> None:
    from divineos.core.game_walk_required import format_missing_message

    text = format_missing_message(["council", "game-walk"], "bash:divineos prereg")
    assert "2>&1" in text and "redirect" in text.lower()
    # ...and an ordinary file edit's refusal does not carry a shell-specific hint.
    assert "redirect" not in format_missing_message(["council"], "Edit:src/x.py").lower()
