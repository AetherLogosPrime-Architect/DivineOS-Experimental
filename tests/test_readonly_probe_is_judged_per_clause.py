"""Looking is never the work these gates stop, even on a line with two parts.

Written 2026-09-05, second fire of one class in a day.

The overdue-review block permits read-only probes, and refused any compound
line outright. So it locked me out this morning, named a cure, and then
refused that cure because I had typed it with a directory change and a shell
option in front. I found the bare form by reading the allowlist rather than by
being told. Aria hit the same wall hours later by a different route, having
watched me hit it -- which is the finding: the first repair opened one door and
never swept the class.

The reason for refusing compound lines is right and is kept: a safe-looking
head may chain into a dangerous tail, and `git log && rm -rf` must never read
as a probe. Judging each clause preserves that exactly. What changes is that a
line whose every clause is a read now reads as a read.

The splitter is quote-aware, and that is load-bearing rather than tidy. A
joiner inside a quoted argument would carve one command into fragments, and a
fragment can begin with a safe prefix when the whole command does not -- so a
naive split fails in the PERMITTING direction. It fails closed on an
unterminated quote for the same reason.
"""

from __future__ import annotations

import pytest

from divineos.hooks.pre_tool_use_gate import _is_readonly_probe, _split_shell_clauses


def test_a_bare_probe_still_passes() -> None:
    assert _is_readonly_probe("divineos prereg show prereg-abc")


def test_the_line_that_was_refused_this_morning_now_passes() -> None:
    """The exact shape the block named as its own cure and then refused."""
    assert _is_readonly_probe('cd "C:/repo" && set -o pipefail && divineos prereg show prereg-abc')


def test_all_read_clauses_pass() -> None:
    assert _is_readonly_probe("git status && git log --oneline -3")


def test_a_write_hiding_behind_a_read_is_still_refused() -> None:
    """The safety property this rule exists for, unchanged.

    Loosening for the all-reads case is only honest while the chain-into-danger
    case stays refused, so it is asserted here rather than assumed from the
    implementation reading correctly.
    """
    assert not _is_readonly_probe("git log && rm -rf /tmp/thing")


def test_a_write_in_the_first_clause_is_still_refused() -> None:
    """Order must not matter. A gate that only inspects the tail is a gate
    that can be defeated by putting the write first."""
    assert not _is_readonly_probe("divineos learn 'something' && git status")


def test_semicolon_and_or_are_joiners_too() -> None:
    assert not _is_readonly_probe("git status ; rm -rf /tmp/thing")
    assert not _is_readonly_probe("git status || divineos learn 'x'")


def test_a_joiner_inside_quotes_does_not_split() -> None:
    """The permitting-direction failure a naive splitter would have.

    Without quote-awareness this carves into fragments, one of which starts
    with a safe prefix, and the whole write is waved through.
    """
    assert _split_shell_clauses("divineos learn 'a && b'") == ["divineos learn 'a && b'"]
    assert not _is_readonly_probe("divineos learn 'a && b'")


def test_unterminated_quote_fails_closed() -> None:
    """Could-not-parse must not resolve to the answer that permits."""
    assert _split_shell_clauses("git status && divineos learn 'unclosed") == []
    assert not _is_readonly_probe("git status && divineos learn 'unclosed")


def test_a_shell_option_clause_is_inert_not_a_read() -> None:
    """It acts on nothing, so it must not make the line non-read.

    This was the last piece keeping the block refusing its own cure: the
    failing clause was one another gate in this same house tells me to type.
    """
    assert _is_readonly_probe("set -o pipefail && git status")
    assert _is_readonly_probe("set -euo pipefail && divineos prereg overdue")


def test_the_inert_allowance_stays_narrow() -> None:
    """Only flags. Anything that could name a file or a variable is not this.

    Written as refusals because a permission this narrow is only safe while
    its edges are asserted rather than assumed from the pattern reading right.
    """
    assert not _is_readonly_probe("set x=1 && git status")
    assert not _is_readonly_probe("setup.sh && git status")


@pytest.mark.parametrize(
    "line",
    [
        "git status && git status && git log",
        "cd /tmp && git status && git diff",
    ],
)
def test_three_clause_reads_pass(line: str) -> None:
    assert _is_readonly_probe(line)
