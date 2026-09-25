"""A prefix one gate prescribes made every other gate's remedy unrecognisable.

The pipeline-exit-ambiguity gate refuses a mutating pipeline that lacks
``pipefail`` and names ``set -o pipefail && `` as the way to satisfy it. The
remedy allowlist strips ``cd X && `` and ``NAME=value `` prefixes so a gate's
own prescribed exit is still recognised when it arrives wearing ordinary shell.
It did not know about ``set``.

So taking the first gate's advice made every remedy invisible to the second,
and the compass marker then refused BOTH of its own named exits -- observe and
dismiss -- and with them every Bash call, including the edit that would have
repaired it. Confirmed by experiment rather than by reading: the identical
command with the prefix removed passed immediately.

THIS IS THE FOURTH INSTANCE and the module's own header predicted it in terms:
"every legal prefix shell permits is a fresh hole -- cd x &&, VAR=1, and
whatever turns up next." What is new is the cause. The first three were holes
nobody had thought of. This one was dug by a sibling gate's instruction, which
means the hazard is not merely unenumerated prefixes -- it is that any gate
teaching a shell habit can silently close another gate's door.

The tests below pin the fix and, more importantly, pin the SHAPE: a remedy must
survive the prefix that another gate tells me to type.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from divineos.core.command_parsing import (  # noqa: E402
    resolve_command_head,
    strip_prefixes_raw,
    stripped_command,
)

REMEDY = 'divineos compass-ops observe TRUTHFULNESS -p 0.1 -e "some evidence"'


@pytest.mark.parametrize(
    "prefix",
    [
        "set -o pipefail && ",
        "set -e && ",
        "set -eu && ",
        "set -o pipefail && cd /tmp && ",
        'cd "/some dir" && set -o pipefail && ',
        "set -o pipefail && VAR=1 ",
    ],
)
def test_a_remedy_survives_the_prefix_another_gate_prescribes(prefix: str) -> None:
    """The exact shape that deadlocked: pipefail advice hiding a compass remedy."""
    assert stripped_command(prefix + REMEDY) == stripped_command(REMEDY)
    assert resolve_command_head(prefix + REMEDY) == "divineos compass-ops"


def test_the_raw_path_strips_it_too() -> None:
    """The quote-aware chain check reads raw text and needs the same blindness cured."""
    assert strip_prefixes_raw("set -o pipefail && " + REMEDY) == REMEDY


def test_a_chain_after_the_prefix_still_survives_into_the_remainder() -> None:
    """Stripping must never swallow something that can execute.

    ``set`` runs no external command, so removing it is safe -- but only if
    everything chained AFTER it is still visible to whatever inspects the
    remainder. A stripper that ate the whole line would turn this check into
    the reassurance-shaped hazard the rest of this repository keeps finding.
    """
    raw = strip_prefixes_raw('set -o pipefail && divineos correction "x" && rm -rf ~')
    assert "&& rm -rf ~" in raw


def test_set_without_a_chain_is_not_a_prefix_on_anything() -> None:
    """``set -e`` alone has no command behind it, so there is nothing to find."""
    assert stripped_command("set -e") == ""
    assert resolve_command_head("set -e") == ""


def test_a_set_carrying_more_than_options_is_left_alone() -> None:
    """Only option flags may sit between ``set`` and the ``&&``.

    Anything else is not a shell-option prefix, and guessing at it is how the
    cd pattern originally let a command substitution through as benign. The
    conservative direction is to decline to strip.
    """
    odd = 'set -- foo && divineos correction "x"'
    assert stripped_command(odd) != stripped_command('divineos correction "x"')


def test_the_probe_can_actually_fail() -> None:
    """Prove the stripper discriminates rather than passing everything.

    Every assertion above is satisfied by a stripper that returns its input
    unchanged, or by one that strips indiscriminately. Pinning both directions
    is what makes the agreements above mean something.
    """
    assert stripped_command("git status") == "git status"
    assert stripped_command("cd /tmp && git status") == "git status"
    assert strip_prefixes_raw("git status") == "git status"
