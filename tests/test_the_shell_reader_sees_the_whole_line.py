"""Four writes the shared shell reader missed. 2026-09-24.

Aether replayed all 87,926 distinct Bash commands on this machine through both
doorman readers before I merged main into my seat, and found two shapes the
tokeniser lost that the old regexes caught. Checking his two, I found two more
that both readers lost, so no replay could see them. A disagreement between
two readers only finds the cases where they disagree.

Every test below failed before the fix it names.
"""

from __future__ import annotations

import pytest

from divineos.core import work_item_doorman as doorman
from divineos.core.command_parsing import shell_write_targets

Q = "'"
NL = "\n"
BS = "\\"


def _writes(command: str) -> list[str]:
    return doorman.paths_from_tool_call("Bash", {"command": command})


# --- a second heredoc that reuses the delimiter ------------------------------
#
# Real shape from the replay: two files written in one command, both closed by
# EOF. The stripper found every opener by searching for its TEXT from the top,
# so the second `<<'EOF'` resolved to the first one, and the second body was
# measured from there -- eating the second `cat > ...` line along with it.


def test_the_second_file_written_under_the_same_delimiter_is_seen() -> None:
    command = (
        f"cat > .claude/hooks/residuals/no_cliff.txt <<{Q}EOF{Q}{NL}one{NL}EOF{NL}"
        f"cat > tests/test_dogfood_probe_tmp.py <<{Q}EOF{Q}{NL}two{NL}EOF"
    )
    assert shell_write_targets(command) == [
        ".claude/hooks/residuals/no_cliff.txt",
        "tests/test_dogfood_probe_tmp.py",
    ]


def test_three_bodies_under_one_delimiter_all_stay_data() -> None:
    command = (
        f"cat > a.txt <<{Q}EOF{Q}{NL}echo > src/x.py{NL}EOF{NL}"
        f"cat > b.txt <<{Q}EOF{Q}{NL}echo > src/y.py{NL}EOF{NL}"
        f"cat > c.txt <<{Q}EOF{Q}{NL}echo > src/z.py{NL}EOF"
    )
    assert shell_write_targets(command) == ["a.txt", "b.txt", "c.txt"]


# --- a line continuation before a command word -------------------------------
#
# Backslash-newline is not an operator the user quoted; the shell deletes it and
# joins the lines. It was neutralised into a placeholder word glued to the next
# token, so `cp` arrived as `QUOTEDOPcp` and was no longer a command word.
# Redirects after a continuation were still caught, which is why it hid: only
# the writers that are command words (cp, mv, sed -i, tee) vanished.


def test_a_copy_after_a_line_continuation_is_seen() -> None:
    command = f"mkdir -p tests/_archive && {BS}{NL}cp tests/x.py tests/_archive/x_copy.py"
    assert shell_write_targets(command) == ["tests/_archive/x_copy.py"]


@pytest.mark.parametrize(
    ("command", "target"),
    [
        (f"true && {BS}{NL}mv a.py src/b.py", "src/b.py"),
        (f"true && {BS}{NL}sed -i s/a/b/ src/c.py", "src/c.py"),
        (f"echo x | {BS}{NL}tee src/d.py", "src/d.py"),
        (f"true && {BS}\r{NL}cp a src/e.py", "src/e.py"),
    ],
)
def test_every_command_word_writer_survives_a_continuation(command: str, target: str) -> None:
    assert shell_write_targets(command) == [target]


def test_an_escaped_operator_is_still_a_word() -> None:
    # The neutraliser exists for this, and the continuation fix must not undo it.
    assert shell_write_targets(f"echo {BS}> not_a_file") == []


# --- the rest of the opener's line is shell, not body ------------------------
#
# Both readers started the heredoc body immediately after `<<'EOF'`. The shell
# starts it on the NEXT line, and everything after the opener on its own line is
# ordinary command text. So `cat <<'EOF' > tests/x.py`, one of the most common
# ways a file gets written from a heredoc, reported nothing at all. The two
# readers agreed on this, which is why the replay could not find it.


def test_a_redirect_after_the_opener_is_seen() -> None:
    command = f"cat <<{Q}EOF{Q} > tests/x.py{NL}body{NL}EOF"
    assert shell_write_targets(command) == ["tests/x.py"]


def test_a_command_chained_after_the_opener_is_seen() -> None:
    command = f"cat > a.txt <<{Q}EOF{Q} && cp a.txt tests/b.txt{NL}body{NL}EOF"
    assert shell_write_targets(command) == ["a.txt", "tests/b.txt"]


def test_a_quoted_body_is_still_data() -> None:
    command = f"cat > a.txt <<{Q}EOF{Q}{NL}echo hi > src/evil.py{NL}EOF"
    assert shell_write_targets(command) == ["a.txt"]


def test_a_continuation_on_the_opener_line_keeps_the_chained_command() -> None:
    # The fifth, found by Dijkstra on the walk (walk-6bc5491434b2) and by none
    # of the pins above: the body starts after the LOGICAL line.
    command = f"cat > a.txt <<{Q}EOF{Q} && {BS}{NL}cp a.txt tests/b.txt{NL}body{NL}EOF"
    assert shell_write_targets(command) == ["a.txt", "tests/b.txt"]


def test_a_here_string_is_not_a_heredoc_opener() -> None:
    # Aether's station four on 722d00a3. `<<<` feeds one word to stdin and
    # claims no following lines, but the opener pattern matched its last two
    # `<` and swallowed everything down to a line reading EOF.
    command = f"cat <<< {Q}EOF{Q}{NL}cp a tests/c.py{NL}EOF"
    assert shell_write_targets(command) == ["tests/c.py"]


# --- every writer, inside every wrapper (Wayne on the walk) ------------------
#
# All five holes lived in a COMBINATION, not in a single shape. So the space is
# crossed rather than sampled: each way of writing a file, placed inside each
# way a command can be wrapped. Any cell that loses its target is a hole.

WRITERS = [
    ("echo x > tests/w.py", "tests/w.py"),
    ("echo x >> tests/w.py", "tests/w.py"),
    ("cp a tests/w.py", "tests/w.py"),
    ("mv a tests/w.py", "tests/w.py"),
    ("sed -i s/a/b/ tests/w.py", "tests/w.py"),
    ("echo x | tee tests/w.py", "tests/w.py"),
]

WRAPPERS = {
    "alone": "{w}",
    "after a continuation": f"true && {BS}{NL}{{w}}",
    "on the opener line": f"cat <<{Q}EOF{Q} && {{w}}{NL}body{NL}EOF",
    "after a quoted heredoc": f"cat > a.txt <<{Q}EOF{Q}{NL}body{NL}EOF{NL}{{w}}",
    "after two heredocs sharing a delimiter": (
        f"cat > a.txt <<{Q}EOF{Q}{NL}one{NL}EOF{NL}cat > b.txt <<{Q}EOF{Q}{NL}two{NL}EOF{NL}{{w}}"
    ),
    "continued onto the opener line": f"cat <<{Q}EOF{Q} && {BS}{NL}{{w}}{NL}body{NL}EOF",
}


@pytest.mark.parametrize("wrapper", list(WRAPPERS), ids=list(WRAPPERS))
@pytest.mark.parametrize(("writer", "target"), WRITERS, ids=[w for w, _ in WRITERS])
def test_every_writer_is_seen_inside_every_wrapper(writer: str, target: str, wrapper: str) -> None:
    command = WRAPPERS[wrapper].format(w=writer)
    assert target in shell_write_targets(command), command


# --- through the doorman, not just the reader --------------------------------


def test_the_doorman_sees_what_the_reader_sees() -> None:
    command = f"cat <<{Q}EOF{Q} > tests/x.py{NL}body{NL}EOF"
    assert _writes(command) == ["tests/x.py"]
