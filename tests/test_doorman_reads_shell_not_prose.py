"""The doorman must read what the shell runs, not what the command carries.

Andrew, 2026-09-12: count every red mark and automate what can be automated.
This gate was second on that list at thirty-six fires in one session, and at
least six were prose read as file paths -- a heredoc terminator, the word `and`
from a chained command, the word `inside` lifted out of a correction I was
filing mid-sentence.

Then it reproduced itself. The command that first fed sample text to this
extractor was refused by the extractor, which announced three files I was about
to write: a format specifier, a quoted example, and an arrow from a print
statement. Hofstadter's finding on the walk, and the reason these fixtures are
built as data rather than written inline as shell strings: A TEST FOR A PATH
DETECTOR LOOKS EXACTLY LIKE THE THING IT DETECTS, permanently and by
construction. Anyone working on this parser hits that, so the cases live in a
list the doorman never sees as a command.

The pairs are the point. Every strip that lets prose through must be checked
against a real write that still has to be caught, or the fix is an evasion
wearing a bug-fix label.
"""

from __future__ import annotations

import pytest

from divineos.core.work_item_doorman import needs_an_item, paths_from_tool_call

NL = chr(10)
SQ = chr(39)
DQ = chr(34)
GT = chr(62)
LT = chr(60)


def _bash(cmd: str) -> list[str]:
    return paths_from_tool_call("Bash", {"command": cmd})


# --- the six that actually happened -----------------------------------------

QUOTED_HEREDOC = (
    "git commit -q -F - "
    + LT
    + LT
    + SQ
    + "MSGEOF"
    + SQ
    + NL
    + "docs: a message about the work"
    + NL
    + "and a second line"
    + NL
    + "MSGEOF"
)

FORMAT_SPEC = (
    "python - "
    + LT
    + LT
    + SQ
    + "PY"
    + SQ
    + NL
    + "print(f"
    + DQ
    + "{count:"
    + GT
    + "8}  {name}"
    + DQ
    + ")"
    + NL
    + "PY"
)

CHAINED_CLI = (
    "divineos walk apply W Knuth --finding "
    + DQ
    + "one thing "
    + GT
    + " another"
    + DQ
    + " && divineos walk close W"
)

PROSE_IN_A_FLAG = "divineos correction " + DQ + "a fault that happens inside the reply" + DQ


@pytest.mark.parametrize(
    "cmd",
    [QUOTED_HEREDOC, FORMAT_SPEC, CHAINED_CLI, PROSE_IN_A_FLAG],
    ids=["quoted-heredoc", "format-spec", "chained-cli", "prose-in-a-flag"],
)
def test_prose_is_not_a_path(cmd: str):
    assert _bash(cmd) == [], cmd


# --- and the writes that must still be caught -------------------------------


def test_a_plain_redirect_is_still_a_write():
    assert _bash("echo x " + GT + " src/divineos/core/thing.py") == ["src/divineos/core/thing.py"]


def test_a_redirect_after_a_quoted_argument_is_still_a_write():
    cmd = "echo " + DQ + "some text" + DQ + " " + GT + " src/divineos/core/thing.py"
    assert _bash(cmd) == ["src/divineos/core/thing.py"]


def test_a_write_inside_an_UNQUOTED_heredoc_is_still_a_write():
    """The shell expands in an unquoted heredoc, so a redirect there is real.
    This is the case that keeps the strip from becoming an evasion."""
    cmd = (
        "cat "
        + LT
        + LT
        + "EOF"
        + NL
        + "echo hi "
        + GT
        + " src/divineos/core/sneaky.py"
        + NL
        + "EOF"
    )
    assert "src/divineos/core/sneaky.py" in _bash(cmd)


def test_a_heredoc_with_no_terminator_is_scanned_whole():
    """Malformed input gets the conservative reading rather than a guess."""
    cmd = "cat " + LT + LT + SQ + "EOF" + SQ + NL + "echo hi " + GT + " src/divineos/core/sneaky.py"
    assert "src/divineos/core/sneaky.py" in _bash(cmd)


def test_a_copy_onto_a_real_path_is_still_a_write():
    assert _bash("cp a.md src/divineos/core/thing.py") == ["src/divineos/core/thing.py"]


def test_a_fully_quoted_copy_does_not_swallow_the_next_command():
    """The regression my own fix produced, one hour after shipping it.

    Stripping quoted spans to nothing changes a command's ARITY, and these
    patterns count arguments. A copy whose source and destination were both
    quoted collapsed to `cp && echo`, so the pattern read `echo` as a
    destination and announced it as a file I was about to write. Caught by the
    doorman on the very next command I ran -- by the thing I had just repaired.

    RE-ASSERTED 2026-09-24, when the tokeniser replaced the quoted-span
    blanker. This used to assert that nothing at all was reported, which wrote
    the blanker's blindness into the requirement: `/somewhere/else/` IS the
    destination, and a reader that reports it is right. What this test exists
    for is that `echo` is never taken for a file, and that a write outside the
    repo opens no work. Aether's read, from replaying 87,926 commands.
    """
    cmd = (
        "cp "
        + DQ
        + "family/letters/a.md"
        + DQ
        + " "
        + DQ
        + "/somewhere/else/"
        + DQ
        + " && echo delivered"
    )
    assert _bash(cmd) == ["/somewhere/else/"]
    assert needs_an_item(_bash(cmd)) == ()


def test_a_quoted_source_still_finds_an_unquoted_destination():
    cmd = "cp " + DQ + "some file.md" + DQ + " src/divineos/core/thing.py"
    assert _bash(cmd) == ["src/divineos/core/thing.py"]


# --- what the stripper was for, asked of the doorman -------------------------
#
# These three called shell_code_only directly. It is gone: the doorman reads
# the shell with command_parsing's tokeniser, where a quoted string stays one
# word and can neither fake a redirect nor hide a destination. The behaviour
# the stripper protected is asserted here instead, through the doorman.


def test_an_arrow_inside_quotes_is_data_and_the_real_redirect_is_seen():
    cmd = "echo " + DQ + "a " + GT + " b" + DQ + " " + GT + " out.txt"
    assert _bash(cmd) == ["out.txt"]


def test_a_command_with_no_data_and_no_write_reports_nothing():
    assert _bash("git status --short") == []


def test_an_empty_command_is_empty_not_a_path():
    assert _bash("") == []


def test_write_and_edit_tools_are_untouched_by_this():
    """Only the shell path changed; a direct file write still reports itself."""
    assert paths_from_tool_call("Write", {"file_path": "src/divineos/core/x.py"}) == [
        "src/divineos/core/x.py"
    ]
