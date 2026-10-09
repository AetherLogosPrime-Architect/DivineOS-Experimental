"""The bootstrap exemption was reading only the first line of a command.

Aria found the heredoc case, 2026-09-23, reading arc 4 of 519. Reproducing it
here found a larger one underneath it that needs no heredoc at all.

WHAT THE EXEMPTION IS FOR. The council gate blocks work until a walk exists,
and the walk is itself a command. So the filing commands any gate requires are
exempted from the gates -- otherwise recording the artifact a gate demands
requires the artifact. The exemption is therefore a hole ON PURPOSE, and its
only defence is that every act in the command must be a filing command.

THE HEREDOC CASE. The function cut the command at the first heredoc operator
and discarded the rest, with a comment saying the discarded part never
executes. True of the heredoc BODY. False of everything after the terminator
line, which is ordinary shell and runs. So a filing command with a heredoc,
followed by a commit or a write to a kiln file, came back exempt.

THE LARGER CASE, FOUND WHILE REPRODUCING THE FIRST. A newline was not a
segment separator, so two acts on two lines were tokenised into one segment
beginning with a filing command -- exempt, with no heredoc anywhere. The same
two acts joined by && were correctly refused. So the heredoc was never the
hole; it was one way of reaching a hole that a plain line break also reaches,
and more easily.

Fixing only what was reported would have closed the harder route and left the
easy one open.

WHY THE BODY MUST STILL BE IGNORED. Once newlines split segments, the contents
of a heredoc body would become segments of their own -- prose, typed English,
which is not a filing command, so every legitimate walk would be refused by its
own reflection text. Stripping the body is what makes splitting on newlines
safe. The two halves are one repair and neither works alone.

DIRECTION OF FAILURE: an unreadable command returns False, i.e. not exempt.
For an exemption the unreadable side is the side that keeps the gate SHUT.
"""

from __future__ import annotations

import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOK = REPO_ROOT / ".claude" / "hooks" / "check-council-required.sh"

NL = chr(10)
_END = "return all(' '.join(seg).startswith(_ARTIFACT_FILING_COMMANDS) for seg in acts)"


@pytest.fixture(scope="module")
def is_filing():
    """The REAL function, lifted out of the hook rather than copied.

    A copy here would test this file's idea of the rule and pass forever while
    the hook drifted. Aria lifted it the same way to find the defect; the test
    that pins the fix should read from the same place the finding did.
    """
    src = HOOK.read_text(encoding="utf-8")
    start = src.rindex(NL, 0, src.index("_ARTIFACT_FILING_COMMANDS = ("))
    namespace: dict = {}
    exec(compile(src[start : src.index(_END) + len(_END)], "hook", "exec"), namespace)
    return namespace["_is_artifact_filing"]


def test_a_plain_filing_command_is_still_exempt(is_filing) -> None:
    """CONTROL. Without this the whole file passes against a function that
    refuses everything, and refusing everything is the deadlock the exemption
    exists to prevent."""
    assert is_filing("divineos council walk --edit x") is True


def test_a_chained_non_filing_act_is_refused(is_filing) -> None:
    """CONTROL, the other side: the rule the exemption already enforced."""
    assert is_filing("divineos learn x && git commit -qm sneak") is False


def test_a_second_act_on_a_second_line_is_refused(is_filing) -> None:
    """THE LARGER HOLE, and no heredoc is involved.

    The same two acts joined by && were already refused. A line break was not a
    separator, so they tokenised into one segment starting with a filing
    command and the whole thing came back exempt.
    """
    assert is_filing("divineos council walk --edit x" + NL + "git commit -qm sneak") is False, (
        "a newline separates two acts exactly as && does; treating it as "
        "whitespace hides the second act inside the first segment"
    )


def test_a_kiln_write_on_a_second_line_is_refused(is_filing) -> None:
    """The same hole pointed at the file the house protects hardest."""
    command = "divineos council walk --edit x" + NL + "echo x > docs/foundational_truths.md"
    assert is_filing(command) is False


def test_an_act_after_a_heredoc_terminator_is_refused(is_filing) -> None:
    """Aria's case. Everything after the terminator is ordinary shell."""
    command = (
        "divineos council walk <<'EOF'" + NL + "prose" + NL + "EOF" + NL + "git commit -qm sneak"
    )
    assert is_filing(command) is False, (
        "the comment claiming the discarded remainder never executes is true "
        "of the body and false after the terminator"
    )


def test_a_write_inside_a_heredoc_body_is_not_an_act(is_filing) -> None:
    """The other direction, and the reason the body must still be ignored.

    A heredoc body is data typed by a person. If splitting on newlines made its
    lines into segments, this legitimate filing command would be refused
    because its own reflection text mentions a redirect.
    """
    command = (
        "divineos council walk <<'EOF'" + NL + "echo x > docs/foundational_truths.md" + NL + "EOF"
    )
    assert is_filing(command) is True, (
        "prose inside a heredoc is input to the act, not another act; refusing "
        "it would make the gate's own remedy unreachable for anyone who writes "
        "about redirects"
    )


def test_prose_with_an_apostrophe_still_parses(is_filing) -> None:
    """A REGRESSION GUARD, not a new rule.

    The hook's own comment records that a heredoc containing one apostrophe
    used to fail to tokenise, so the gate's prescribed remedy was reachable
    only when written without contractions. English prose has apostrophes. Any
    change to this parser has to keep that fixed.
    """
    command = "divineos council walk <<'EOF'" + NL + "it doesn't tokenise" + NL + "EOF"
    assert is_filing(command) is True


# --- A walk or a log FED to the filing command through a pipe ---------------
#
# The walk command reads its reflection from stdin and its own help prescribes
# echo piped into it. The exemption demanded that EVERY segment be a filing
# command, so the feeder segment (cat, echo, printf) was an act that could never
# be exempt: the prescribed remedy was refused by the gate that prescribes it.
# The structural obligation for this stood open ten times with nothing built
# (psf-05479077) while each walk cost a detour through a file on stdin.
#
# The feeder carries text and has no act of its own PROVIDED it writes nothing,
# runs nothing, and pipes straight into a filing command. Every one of those
# conditions has a test below that fails if it is dropped.

FEEDER_HEREDOC = "cat <<'EOF' | divineos council walk --edit x" + NL + "prose" + NL + "EOF"


def test_a_cat_heredoc_piped_into_a_walk_is_exempt(is_filing) -> None:
    assert is_filing(FEEDER_HEREDOC) is True, (
        "the shape every walk was typed in today; the feeder only carries the prose"
    )


def test_the_form_the_walk_help_prescribes_is_exempt(is_filing) -> None:
    """echo piped into walk is literally the usage line in the walk command help."""
    assert is_filing('echo "a typed reflection" | divineos council walk --edit x') is True


def test_printf_piped_into_a_log_is_exempt(is_filing) -> None:
    assert is_filing("printf 'text' | divineos council log --edit x") is True


def test_a_feeder_that_writes_a_file_is_not_a_feeder(is_filing) -> None:
    """THE HOLE this must not open: a write to a protected file wearing a feeder's name."""
    assert is_filing("cat > docs/foundational_truths.md | divineos council walk --edit x") is False
    assert is_filing("echo x >> docs/foundational_truths.md | divineos council walk") is False


def test_a_feeder_running_a_command_substitution_is_not_a_feeder(is_filing) -> None:
    """echo with a substitution runs the substituted command, whatever the pipe feeds."""
    assert is_filing("echo " + chr(36) + "(git commit -qm sneak) | divineos council walk") is False
    assert (
        is_filing("echo " + chr(96) + "git commit -qm sneak" + chr(96) + " | divineos council walk")
        is False
    )


def test_a_feeder_piped_into_something_else_is_refused(is_filing) -> None:
    assert is_filing("cat notes.txt | git commit -qm sneak") is False


def test_a_feeder_not_piped_into_the_filing_command_is_refused(is_filing) -> None:
    assert is_filing("cat notes.txt ; divineos council walk --edit x") is False


def test_a_fed_walk_chained_to_another_act_is_refused(is_filing) -> None:
    assert is_filing("echo x | divineos council walk --edit x && git commit -qm sneak") is False


def test_a_feeder_with_nothing_after_it_is_refused(is_filing) -> None:
    """A trailing pipe feeds nothing; the feeder alone is no filing."""
    assert is_filing("cat notes.txt |") is False
