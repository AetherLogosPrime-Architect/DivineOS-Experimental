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


def test_find_escapes_is_deduped_and_sorted():
    cmd = "x <<'E'\n'a\\nb\\nc\\t'\nE"
    found = find_escapes(cmd)
    assert found == sorted(set(found))
    assert "\\n" in found
