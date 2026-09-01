"""Tests for the heredoc-escape doorman.

The must-NOT-fire cases matter as much as the must-fire ones. A gate that fires
constantly gets bypassed, and a bypassed gate catches nothing -- so the
narrowness is a load-bearing property, not a nicety.
"""

from __future__ import annotations

from divineos.core.heredoc_escape_check import (
    find_escapes,
    refusal_message,
    should_refuse,
)

# --- must fire: heredoc + escapes + a file comes out ----------------------


def test_fires_on_python_heredoc_writing_a_py_file():
    cmd = "python - <<'EOF'\nfrom pathlib import Path\nPath('out.py').write_text('a\\nb\\n')\nEOF"
    assert should_refuse(cmd)


def test_fires_on_redirect_to_a_file():
    cmd = "cat <<EOF > scripts/gen.sh\necho 'x\\ty'\nEOF"
    assert should_refuse(cmd)


def test_fires_on_open_for_write():
    cmd = "python - <<'PY'\nf = open('a.json', 'w')\nf.write('x\\n')\nPY"
    assert should_refuse(cmd)


def test_fires_on_write_bytes():
    """The setup-renormalize.sh shape: byte-literals with escapes in a heredoc."""
    cmd = "python - <<'PY'\np.write_bytes(b'x\\r\\n')\nPY"
    assert should_refuse(cmd)


def test_fires_on_unquoted_delimiter_too():
    """Unquoted is strictly worse -- bash expands as well. Must not slip past."""
    cmd = "python - <<PY\nopen('x.md','w').write('a\\nb')\nPY"
    assert should_refuse(cmd)


# --- must NOT fire: the narrowness ---------------------------------------


def test_silent_on_heredoc_with_no_escapes():
    cmd = "python - <<'PY'\nprint('hello')\nPY"
    assert not should_refuse(cmd)


def test_silent_on_escapes_with_no_heredoc():
    assert not should_refuse("grep -c 'a\\nb' file.py")


def test_silent_on_heredoc_that_produces_no_file():
    """SQL into a pipe: no third layer, nothing to lose."""
    cmd = "sqlite3 db <<'SQL'\nSELECT 'a\\nb';\nSQL"
    assert not should_refuse(cmd)


def test_silent_on_heredoc_piped_to_another_process():
    cmd = "cat <<'EOF' | wc -l\nline\\tone\nEOF"
    assert not should_refuse(cmd)


def test_silent_on_the_doorman_hooks_own_body_shape():
    """The hook itself uses `python -c` with a quoted body. It must pass."""
    cmd = 'echo "$INPUT" | "$PYTHON_BIN" -c \'\nimport json, sys\nsys.exit(0)\n\''
    assert not should_refuse(cmd)


def test_silent_when_a_heredoc_is_only_QUOTED_not_used():
    """The door's own first live fire, kept as a fixture because it was wrong.

    This is the harness written to exercise the door. Its DATA quotes a
    heredoc; the outer command is `python -c` and opens no heredoc at all. The
    opener regex matched text inside a string and the door blocked it.

    Mention is not use -- third instance of that class in this substrate, after
    the mechanism-claim marker counting a tool NAME as evidence and the
    boundary core/command_match.py exists for.
    """
    cmd = (
        'python -c "\n'
        "cases = [('x', 'Bash', {'command': \\\"python - <<'PY'\\\\nopen('x.py','w')"
        ".write('a\\\\\\\\nb')\\\\nPY\\\"})]\n\""
    )
    assert not should_refuse(cmd)


def test_silent_when_the_delimiter_never_closes():
    """No line holding the delimiter alone means no heredoc body was consumed."""
    cmd = "echo \"see <<'PY' for the shape\" > notes.md && printf 'a\\nb'"
    assert not should_refuse(cmd)


def test_silent_on_empty_and_none():
    assert not should_refuse("")
    assert not should_refuse(None)  # type: ignore[arg-type]


# --- the refusal itself ---------------------------------------------------


def test_refusal_names_the_escapes_it_found():
    cmd = "python - <<'PY'\nopen('a.py','w').write('x\\n')\nPY"
    msg = refusal_message(cmd)
    assert "\\n" in msg
    assert "Write" in msg and "Edit" in msg


def test_refusal_says_why_it_blocks_rather_than_labels():
    cmd = "python - <<'PY'\nopen('a.py','w').write('x\\n')\nPY"
    assert "mechanical" in refusal_message(cmd).lower()


def test_refusal_invites_a_false_positive_report():
    """A door that cannot be told it is wrong becomes a door people route around."""
    cmd = "python - <<'PY'\nopen('a.py','w').write('x\\n')\nPY"
    assert "false" in refusal_message(cmd).lower()


# --- the false fire, pinned ------------------------------------------------
#
# 2026-08-27, hours after this door merged. It refused the commit carrying the
# map-freshness work. That command held a heredoc -- a commit message, no
# escapes, no file target -- and, elsewhere on the same line, a `python -c`
# doing a newline replacement.
#
# The old predicate searched the WHOLE command for escapes and the WHOLE command
# for a file-producing shape. Two unrelated fragments satisfied the two
# conditions BETWEEN them, and neither fragment was the thing this door exists
# to catch.
#
# Its refusal text asks to be told when that happens, and names the SHAPE as the
# thing to fix rather than the door as the thing to route around.
#
# Both tests below were checked against the PRE-FIX predicate and both refuse
# there, so they pin something rather than merely passing. A third was written
# and removed: it fired identically before and after, guarding a line the
# must-fire cases above already hold.
#
# The first repair also OVERSHOT -- it scoped file-production to the opener line
# as well as the escapes, which broke three must-fire cases, because the
# commonest real shape is `python - <<PY` with the write inside the script.
# Escapes are body-scoped; file-production is either place. That direction is
# guarded by test_fires_on_open_for_write and test_fires_on_write_bytes.


def _commit_msg_beside_an_escaping_python_c() -> str:
    """The real false fire, recovered from the transcript rather than recalled.

    This matters: the first version of this fixture was written from memory and
    dropped ``write_bytes`` -- so the old predicate did NOT refuse it either,
    and the test passed before and after the fix. It pinned nothing while
    looking exactly like a regression test. Found by running the pre-fix
    predicate over all 945 Bash calls in the session and reading what actually
    got refused.

    Assembled from chr() rather than spelled out, because the whole bug is about
    WHICH FRAGMENT the backslashes live in, and a later tidy-up of escaping in
    this file would silently retarget the test.
    """
    nl, bs = chr(10), chr(92)
    crlf, lf = "b'" + bs + "r" + bs + "n'", "b'" + bs + "n'"
    # One python -c carrying BOTH conditions: the escapes and the file-producing
    # shape. Neither has anything to do with the heredoc beside it.
    normalize = "p.write_bytes(p.read_bytes().replace(" + crlf + "," + lf + "))"
    return (
        'python -c "' + normalize + '"'
        " && git commit -F - <<'MSG'" + nl + "a commit message" + nl + "MSG" + nl
    )


def test_does_not_fire_on_a_clean_heredoc_beside_an_escaping_fragment():
    assert not should_refuse(_commit_msg_beside_an_escaping_python_c())


def test_escapes_outside_the_heredoc_do_not_convict_the_heredoc():
    """Escapes are judged in the BODY. Elsewhere on the line is a different call."""
    cmd = "printf 'a\\nb' && cat <<'PY' > out.py\nplain text\nPY"
    assert not should_refuse(cmd)


def test_find_escapes_is_deduped_and_sorted():
    cmd = "x <<'E'\n'a\\nb\\nc\\t'\nE"
    found = find_escapes(cmd)
    assert found == sorted(set(found))
    assert "\\n" in found
