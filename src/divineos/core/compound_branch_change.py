"""Refuse a branch change and a destructive op on the same shell line.

WHY THIS EXISTS. On 2026-09-04 I typed one line meaning two things: switch to
the code branch, and then remove thirty letters from it. A gate refused the
line -- correctly, the paths came from a file so it could not see what was
being deleted. It refused the WHOLE line, including the switch, which had not
run yet.

I read the refusal as being about the removal, because the removal was the part
I had been reaching for. So I re-issued only that half, with the paths named so
the gate could see them, and it executed on the branch I was still standing on:
the letters branch, whose entire purpose is to carry those thirty files. I
pushed it.

The branch was then adding nothing and deleting nothing. The addition and the
removal cancelled exactly, so a pull request from it would have shown an empty
diff, merged without a single complaint, and delivered no letters at all.
Nothing would have failed.

WHY A DISCIPLINE WOULD NOT HAVE HELD, and I want this written down rather than
promised. "Re-read the branch after a refusal" is a rule I would have agreed
with before, during, and after making this mistake. The reach does not feel like
skipping a check; it feels like answering the objection the gate raised. The
objection was about deletion, so deletion is what I fixed. The half that had
silently dropped out was never in my attention to begin with.

So the option is taken away instead (foundational truth #11, remediation (a)):
the two clauses have to be separate calls. Then there is no compound line for a
refusal to bisect, and a re-issued fragment cannot inherit the wrong branch.

WHAT THIS DELIBERATELY DOES NOT COVER. `&&` short-circuits, so at RUNTIME the
chain was never the danger -- a failing checkout stops the removal by itself.
The hazard is entirely in the human re-issue after a BLOCK, where the shell
never ran at all. Blocking the compound form is the cheapest way to make that
re-issue impossible; catching the re-issue itself would need memory of the
refused line, which this does not have.

Nor does it inspect quoting. A destructive verb inside a quoted string counts,
which can misfire on a line that merely prints one. Refusing to split a line
that did not need splitting costs one extra call; missing one costs what is
described above. Named here so the asymmetry is a choice rather than an
oversight.
"""

from __future__ import annotations

import re

# A branch change: anything that moves HEAD to a different branch.
#
# JUDGED PER CLAUSE, not across the whole line, and the first version was not.
# It used a lookahead pinned just after the verb, which excluded
# `git checkout -- <paths>` but not `git checkout <ref> -- <paths>` -- so a
# path-restore chained with a removal read as a branch change and got refused.
# A gate that blocks the SAFE form of the operation it protects is worse than
# no gate, because it teaches me to route around it. Caught by the test written
# for exactly that case, before this shipped.
#
# The rule is simply: within one clause, a `--` separator means paths are being
# named, and naming paths means HEAD is not moving.
_BRANCH_CHANGE = re.compile(r"\bgit\s+(?:switch|checkout)\b", re.IGNORECASE)
_PATH_SEPARATOR = re.compile(r"\s--(?:\s|$)")

# Destructive or state-moving operations whose meaning depends entirely on which
# branch is checked out.
_BRANCH_SENSITIVE = (
    (re.compile(r"\bgit\s+rm\b", re.IGNORECASE), "git rm"),
    (re.compile(r"\bgit\s+clean\b", re.IGNORECASE), "git clean"),
    (re.compile(r"\bgit\s+reset\s+.*--hard\b", re.IGNORECASE), "git reset --hard"),
    (re.compile(r"\bgit\s+restore\b", re.IGNORECASE), "git restore"),
    (re.compile(r"\bgit\s+checkout\s+(?:\S+\s+)?--\s", re.IGNORECASE), "git checkout -- <paths>"),
)

# Only lines that actually JOIN clauses. A single command cannot be bisected by
# a refusal, so there is nothing here to protect.
_JOINER = re.compile(r"(?:&&|\|\||;)")


def block_reason(command: str) -> str | None:
    """Return why this line must be split, or None if it is fine as it stands.

    Returns None rather than raising on anything unexpected -- but note that
    None here means "nothing to say", so any future failure path must be given
    its own state rather than borrowing this one.
    """
    if not command or not command.strip():
        return None
    if not _JOINER.search(command):
        return None

    clauses = [c.strip() for c in _JOINER.split(command) if c.strip()]

    moves_head = any(
        _BRANCH_CHANGE.search(clause) and not _PATH_SEPARATOR.search(clause) for clause in clauses
    )
    if not moves_head:
        return None

    hits = [
        label
        for pattern, label in _BRANCH_SENSITIVE
        if any(pattern.search(clause) for clause in clauses)
    ]
    if not hits:
        return None

    named = ", ".join(hits)
    return (
        "COMPOUND LINE: this changes branch AND runs "
        f"{named} in one call. Split it into two.\n\n"
        "  1. change the branch\n"
        "  2. read back which branch you are actually on\n"
        "  3. then run the destructive part\n\n"
        "WHY. On 2026-09-04 a gate refused exactly this shape. It refused the "
        "whole line, so the branch change never ran, and I re-issued only the "
        "destructive half -- which then executed on the branch I had not left. "
        "It stripped thirty letters off the branch that exists to carry them, "
        "and left that branch adding nothing and deleting nothing, so the "
        "resulting pull request would have merged clean and delivered nothing.\n\n"
        "A refusal of a compound line is a refusal of the WHOLE line, not of "
        "the clause you were reaching for. The precondition drops silently "
        "because it was never in your attention. Splitting the call is what "
        "makes that impossible, rather than merely resolved to avoid."
    )
