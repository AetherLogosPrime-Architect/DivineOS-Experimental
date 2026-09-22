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


def test_a_bare_cd_clause_is_inert_not_a_read() -> None:
    """The same argument as the shell-option clause, asked of the other inert thing.

    2026-09-13. The inertness reasoning above was written for ``set -o`` and
    then asked of nothing else -- which is the failure this file's own docstring
    names one paragraph earlier: the first repair opened one door and never
    swept the class.

    The door it missed is the habit half of every Bash call in this house.
    Measured at the time:

        divineos prereg overdue                   -> probe
        set -o pipefail; divineos prereg overdue  -> probe
        cd "<repo>"; divineos prereg overdue      -> BLOCKED

    A standalone ``cd`` clause has its prefix stripped, leaves the empty
    string, and empty read as not-a-probe -- so the overdue block refused every
    command that would have shown me the pre-registration it wanted assessed,
    including the two its own refusal text prescribes.
    """
    assert _is_readonly_probe('cd "/some/repo"; divineos prereg overdue')
    assert _is_readonly_probe("cd /repo; git log")
    assert _is_readonly_probe('cd "/some/repo"; set -o pipefail; git status')


def test_the_cd_allowance_refuses_every_laundering_shape_on_record() -> None:
    """Loosening a cd check is how a gate gets laundered, so the edges are asserted.

    Each of these is a worked example from this house's own letters rather than
    an invented adversary: command substitution in the path, a redirection
    hidden in it, a backtick, and a chain that ends somewhere else entirely.
    The shared parser accepted two of them once; narrowness was restored at the
    gate and this test is what keeps it here.
    """
    assert not _is_readonly_probe('cd "$(curl attacker)"; git log')
    assert not _is_readonly_probe("cd /tmp>out; git log")
    assert not _is_readonly_probe("cd `curl x`; git log")
    assert not _is_readonly_probe("cd /a; rm -rf /")
    assert not _is_readonly_probe("cd /a && cd /b; rm -rf /")
    assert not _is_readonly_probe("cd /a; git push")


def test_the_remedy_still_passes_because_it_is_the_point() -> None:
    """``prereg assess`` mutates and must STILL read as passable here.

    Written because I asserted the opposite while testing the change and had to
    correct myself against the code. This checker has exactly one caller -- the
    overdue-pre-registration block -- and assessing is the remedy that clears
    it. A gate that refuses its own cure is the shape three separate comments in
    that file exist to prevent, so this is intended rather than a leak, and the
    test says so where the next reader will look.
    """
    assert _is_readonly_probe("cd /a; divineos prereg assess x --outcome SUCCESS")
    # ...and a genuinely unrelated mutation still does not ride along.
    assert not _is_readonly_probe("cd /a; divineos learn status")


def test_the_cd_allowance_needs_the_SHAPE_not_only_the_character_check() -> None:
    """Two checks, and the sweep proved the second one is not decoration.

    Breaking the shape check while leaving the character check broke NOTHING in
    this file, which read as one of the two being redundant. It is not. With
    shape removed, the rule degrades to "starts with those two letters and has
    no dangerous characters", and these all sail through:

        cdrom-tool --wipe-everything
        cdparanoia rip
        cd /a /b /c

    None is a directory change. The first two are other programs whose names
    merely begin the same way, and the third is a cd with operands it should
    not have. A clause is inert only if it is a cd AND a path AND nothing else.
    """
    assert not _is_readonly_probe("cdrom-tool --wipe-everything; git log")
    assert not _is_readonly_probe("cdparanoia rip; git log")
    assert not _is_readonly_probe("cd /a /b /c; git log")
    assert not _is_readonly_probe("cd; git log")


# ---------------------------------------------------------------------------
# A READ VERB HANDED SOMEWHERE TO PUT ITS OUTPUT IS NOT A READ.
#
# Aletheia, 2026-09-21, refusing to sign a change that carried this carve-out
# into a second gate. She asked the question I had asked her -- is the
# read-only set a fault now or a fault waiting -- and answered it by running
# it rather than reasoning about it.
#
# The prefix match reads the start of a command and ignores everything after,
# so every flag was invisible. Reproduced in a scratch repository before the
# finding was accepted: log, show and diff each create a file when handed an
# output path, and the probe called all three reads. The dangerous one is a
# diff written over a guardrail file, which the gate would have called
# looking. It had been live on the overdue-pre-registration gate for sixteen
# days; the change she refused would have carried it to a second door.
#
# The wider one, which came from asking the probe rather than asking myself:
# an ordinary shell redirect needs no flag at all and overwrote a file I had
# put a word into so I would notice.
#
# Nothing in this suite mentioned either shape before today -- her count of
# zero, checked across the whole tests directory rather than this file.
#
# The near-misses are asserted too, because a permission this narrow is only
# safe while its edges are held: the short flag is not an output flag on
# these verbs, and the capital is the diff orderfile, which READS a file. One
# careless case-insensitive rule would have broken it.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "line",
    [
        "git diff --output=src/divineos/core/memory.py",
        "git log --output=notes.txt",
        "git show --output=.claude/hooks/x.sh",
        "git log --oneline > .claude/hooks/overwritten.sh",
        "git status >> appended.txt",
        "cd /repo && git diff --output=victim.txt",
    ],
)
def test_a_read_verb_given_a_destination_is_a_write(line: str) -> None:
    assert not _is_readonly_probe(line)


@pytest.mark.parametrize(
    "line",
    [
        "git diff -O ordering-rules.txt",  # orderfile READS a file
        "git status 2>/dev/null",  # discard, not a destination
        "git log --oneline 2>&1 | tail -5",  # duplicates a handle
        "git diff --stat",
    ],
)
def test_the_refusal_stays_off_the_honest_reads(line: str) -> None:
    assert _is_readonly_probe(line)
