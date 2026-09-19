"""The doorman that refuses a branch change and a destructive op on one line.

THE FIXTURE IS COPIED FROM THE RECORD, NOT FROM MEMORY OF IT. The first test
below carries the shape of the actual command from 2026-09-04, because the
known way to write a hollow regression test is to reconstruct its fixture from
recollection -- a true statement about a command that never existed. The real
one used a path list read from a file, which is why the deletion gate could not
see the targets and refused the whole line.
"""

from __future__ import annotations

from divineos.core.compound_branch_change import block_reason
from divineos.core.hook_surfaces import compound_branch_change_surface

# The shape of the line that caused the damage: switch branch, then remove.
THE_LINE_THAT_DID_IT = (
    'git checkout -q integration/code-2026-09-04 && echo "ON=$(git branch --show-current)" '
    "&& git diff --name-only origin/main...HEAD > /tmp/strip.txt "
    "&& xargs -a /tmp/strip.txt -d '\\n' git rm -q --cached --"
)


def test_the_line_that_stripped_the_letters_is_refused():
    reason = block_reason(THE_LINE_THAT_DID_IT)
    assert reason is not None, "the doorman does not fire on the command it was built from"
    assert "git rm" in reason
    assert "Split it into two" in reason


def test_the_reason_says_to_read_the_branch_back_not_merely_to_be_careful():
    """A refusal that only says 'be careful' is the discipline I already had.

    The whole finding is that resolving to check harder does not work, because
    the dropped clause was never in my attention. The refusal has to name the
    read-back as a step.
    """
    reason = block_reason(THE_LINE_THAT_DID_IT)
    assert reason is not None
    assert "read back which branch" in reason


def test_a_branch_change_on_its_own_is_fine():
    assert block_reason("git checkout -q integration/letters-2026-09-04") is None


def test_a_destructive_op_on_its_own_is_fine():
    assert block_reason("git rm -q -- family/letters/old.md") is None


def test_a_branch_change_chained_with_harmless_reads_is_fine():
    """The gate must not tax ordinary work, or it becomes wallpaper."""
    cmd = 'git checkout -q main && echo "ON=$(git branch --show-current)" && git status --porcelain'
    assert block_reason(cmd) is None


def test_two_destructive_ops_chained_without_a_branch_change_are_fine():
    assert block_reason("git rm -q -- a.md && git rm -q -- b.md") is None


def test_restoring_paths_is_not_a_branch_change():
    """`git checkout <ref> -- <paths>` moves files, not HEAD.

    Written because the naive pattern for "git checkout" catches this too, and
    a gate that refuses path-restores would be refusing the safe form of the
    very operation it is protecting.
    """
    assert block_reason("git checkout origin/main -- docs/ && git rm -q -- old.md") is None
    assert block_reason("git checkout -- family/ && git clean -fd") is None


def test_switch_counts_as_a_branch_change_too():
    assert block_reason("git switch main && git reset --hard origin/main") is not None


def test_a_hard_reset_after_a_branch_change_is_refused():
    reason = block_reason("git checkout -q main && git reset --hard origin/main")
    assert reason is not None
    assert "git reset --hard" in reason


def test_restore_staged_after_a_branch_change_is_refused():
    """The second half of the same incident.

    Unstaging by pathspec after a checkout is the same hazard wearing a
    non-destructive-sounding verb: it silently rewrites the index of whichever
    branch is actually checked out.
    """
    reason = block_reason("git checkout -q clean-branch && git restore --staged -- family/")
    assert reason is not None
    assert "git restore" in reason


def test_every_named_op_appears_in_the_reason():
    """The reason names what it found, so the refusal is checkable rather than
    a category assertion the reader has to take on trust."""
    reason = block_reason("git switch x && git rm a && git clean -fd")
    assert reason is not None
    assert "git rm" in reason
    assert "git clean" in reason


def test_a_single_clause_with_no_joiner_is_never_refused():
    """No joiner means nothing for a refusal to bisect, which is the whole
    mechanism. A one-clause command cannot lose a precondition it never had."""
    assert block_reason("git rm -q -- a.md") is None
    assert block_reason("git checkout main") is None


def test_empty_and_blank_commands_say_nothing():
    assert block_reason("") is None
    assert block_reason("   ") is None


def test_the_surface_refuses_with_a_json_deny():
    outcome = compound_branch_change_surface(
        {"tool_name": "Bash", "tool_input": {"command": THE_LINE_THAT_DID_IT}}
    )
    assert outcome is not None
    assert outcome.refused is True
    assert outcome.json_deny is True
    assert outcome.state == "spoke"


def test_the_surface_is_silent_on_a_clean_command():
    outcome = compound_branch_change_surface(
        {"tool_name": "Bash", "tool_input": {"command": "git status"}}
    )
    assert outcome is not None
    assert outcome.state == "nothing-to-say"
    assert not outcome.refused


def test_the_surface_ignores_tools_that_are_not_bash():
    outcome = compound_branch_change_surface(
        {"tool_name": "Edit", "tool_input": {"command": THE_LINE_THAT_DID_IT}}
    )
    assert outcome is not None
    assert outcome.state == "nothing-to-say"


def test_the_surface_is_registered_and_not_merely_written():
    """A surface nobody dispatches is the alarm in the box with the cable
    coiled beside it -- the exact shape this whole family of faults takes.

    Pinned here because the sibling surface shipped once with the function
    present and the registration absent, and nothing said so.
    """
    from divineos.core.hook_router import registered
    from divineos.core.hook_surfaces import install

    install()
    assert "compound_branch_change" in registered("PreToolUse")
