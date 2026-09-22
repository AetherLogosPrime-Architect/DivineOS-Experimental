"""A heredoc body is data, and the doorman was reading it as shell.

FOUND BY BEING REFUSED, 2026-09-21. Writing a draft under ``docs/drafts``
through a heredoc, on a doorman whose refusal message asks for exactly that
draft. The draft quoted Andrew in markdown, and markdown marks a quotation
with the character the shell uses to redirect, so every quoted line named a
file after its own first word. Those names exist nowhere, match no exempt
prefix, and therefore always count as code.

The loop that makes this worth a test file of its own: the remedy the refusal
prescribes is a write, so no work item can clear it. A refusal that cannot be
satisfied by doing what it asks is not a gate, it is a wall.

The controls matter more than the fix here. Blanking a heredoc body would be a
bad trade if it hid a real write, so three of these five tests exist to prove
it does not: the redirection in a heredoc HEADER still reports its file, an
ordinary redirect outside any heredoc is untouched, and an unterminated
heredoc is left entirely alone rather than swallowing the rest of the command.
"""

from divineos.core.work_item_doorman import paths_from_tool_call


def _bash(command: str) -> list[str]:
    return paths_from_tool_call("Bash", {"command": command})


def test_a_markdown_quotation_inside_a_heredoc_names_no_file():
    """The exact shape that refused the draft."""
    command = "\n".join(
        [
            "cat > docs/drafts/a_draft.md <<'EOF'",
            "# The house can still hand me a retired rule",
            "",
            "Andrew, tonight:",
            "",
            "> he built this entire house without laying a brick of it",
            "> and the rule it taught me had been retired two weeks earlier",
            "EOF",
        ]
    )
    found = _bash(command)
    assert "he" not in found, found
    assert "and" not in found, found


def test_the_real_destination_in_the_header_is_still_reported():
    """The control that decides whether the fix is safe.

    If blanking the body also lost the header, the doorman would stop seeing
    the most common way a file gets written without touching the edit tools --
    which is the reason it watches Bash at all.
    """
    command = "\n".join(
        [
            "cat > src/divineos/core/something_real.py <<'EOF'",
            "print('hello')",
            "EOF",
        ]
    )
    assert "src/divineos/core/something_real.py" in _bash(command)


def test_a_redirect_outside_any_heredoc_is_untouched():
    assert "notes.txt" in _bash("echo hi > notes.txt")


def test_an_unterminated_heredoc_does_not_swallow_the_rest():
    """No terminator means the command is malformed.

    Blanking to the end of the string would be a guess with every later
    redirection riding on it, so the header is treated as ordinary text and
    the writes after it are still seen.
    """
    command = "\n".join(
        [
            "cat <<'NEVERCLOSED'",
            "some body text",
            "echo real > src/divineos/core/after_the_heredoc.py",
        ]
    )
    assert "src/divineos/core/after_the_heredoc.py" in _bash(command)


def test_a_body_holding_an_unbalanced_quote_does_not_derail_the_quote_scan():
    """Why heredoc blanking runs BEFORE quoted-span blanking.

    An apostrophe inside the body would otherwise pair with a quote outside
    it, blanking the span between them -- which could erase a real redirection
    sitting after the heredoc.
    """
    command = "\n".join(
        [
            "cat > docs/drafts/b_draft.md <<'EOF'",
            "Andrew's words, and the rule didn't survive them",
            "EOF",
            "echo done > src/divineos/core/written_after.py",
        ]
    )
    found = _bash(command)
    assert "src/divineos/core/written_after.py" in found, found


# ---------------------------------------------------------------------------
# THE SECOND MISFIRE, found an hour after the first, in the same function.
#
# The scope gate refused a push and required the branch be rebuilt. Moving one
# file out of the way first, a copy to a path OUTSIDE the repo was followed by
# two more commands on the same line. With the quoted arguments blanked, the
# copy pattern's filler -- a plain run of non-space, which matches a semicolon
# as happily as a filename -- stepped over the separator and captured the next
# command's name. The doorman refused a command that touches nothing in the
# tree, naming a file that has never existed.
#
# Every CAPTURE group here already refused separators. Only the fillers were
# loose, which is what an invariant looks like when it is honoured by habit at
# each site instead of declared once.
# ---------------------------------------------------------------------------


def test_a_copy_does_not_reach_past_a_semicolon_for_its_destination():
    command = 'cp "family/letters/a.md" "C:/outside/the/repo/" ; git stash push -u'
    found = _bash(command)
    assert "git" not in found, found
    assert "stash" not in found, found


def test_a_copy_does_not_reach_past_an_ampersand_either():
    """The exact shape that fired: copy, then two more commands."""
    command = 'cp "one.md" "C:/elsewhere/" && ls -la "C:/elsewhere/one.md" && echo ok'
    found = _bash(command)
    assert "ls" not in found, found
    assert "echo" not in found, found


def test_a_real_copy_into_the_tree_is_still_caught():
    """The control. Narrowing the filler must not blind the pattern."""
    assert "src/divineos/core/target.py" in _bash(
        "cp scratch/source.py src/divineos/core/target.py"
    )


def test_a_real_copy_with_flags_is_still_caught():
    assert "src/divineos/core/target.py" in _bash(
        "cp -r --preserve scratch/source.py src/divineos/core/target.py"
    )


def test_an_in_place_edit_is_still_caught():
    assert "src/divineos/core/target.py" in _bash("sed -i s/a/b/ src/divineos/core/target.py")
