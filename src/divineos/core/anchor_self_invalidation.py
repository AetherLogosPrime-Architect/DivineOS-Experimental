"""A letter carrying an anchor must not be committed onto the branch it anchors.

## The failure, twice

2026-08-22. I wrote to Aria with a tree-hash for a branch, the letter landed on
that branch, and the hash was wrong before she read it. I diagnosed it, named
the rule -- *a letter carrying an anchor must not live on the branch it anchors*
-- and delivered the next one to the shared directory only, deliberately.

2026-08-25. I asked Aletheia to audit a pull request, gave her the tip and the
tree-hash, and told her to recompute rather than trust me. She did. It had
already moved:

    cited   tip 52976160   tree 5576d4aa40a8
    actual  tip 59c2a920   tree 48fb6bbfdc97

**The only thing that moved the branch was the letter asking her to audit it.**
It went into ``family/letters/`` inside the tree, and ``auto_commit``'s
``git add -A`` swept it in.

Her ruling, and the reason this module exists rather than another resolution:
*"You resolved it three days ago and the machinery reproduced the failure
anyway. The rule needs to be a mechanism, not a resolution."*

## What is checked

A file is self-invalidating when it BOTH names the current branch AND carries a
commit-ish anchor -- a tree-hash, a tip, or a bare forty- or seven-plus-hex
token in anchor position. Naming a branch is fine. Quoting a hash is fine.
Doing both, on that branch, is the thing that cannot be true after the commit
lands.

## What it does NOT do

It does not refuse the letter. The letter is correct and should be delivered --
to the shared directory, which is outside every tree and is where the crossing
actually happens. What it refuses is *committing that file onto the branch it
describes*, which is the single act that makes its own contents false.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

# A hash in anchor position: preceded by a word that means "this is the state I
# am pointing you at". A bare hex string in prose is not an anchor.
#
# THE GAP CLAUSE, AND WHY IT IS THERE (2026-09-01). This required the keyword to
# sit directly against the hash, separated by at most a colon and whitespace. So
# "tip: 1a2b3c4" was caught and "its tip is 1a2b3c4" was not -- and the second is
# how a person actually writes the sentence. I found it by writing a test in my
# own natural phrasing and watching it fail, which is the only reason it turned
# up at all.
#
# It is the same fault as the reserved-name guard repaired hours earlier and by
# the same hand: matching the TYPOGRAPHY around a word instead of the word doing
# the work. A rule I wrote to catch a letter falsifying itself could be walked
# past by putting the verb "is" where a colon had been.
#
# The gap is small on purpose. Widening it to "any hash anywhere near the branch
# name" would turn this into a hash-detector, and then a letter quoting some
# unrelated commit would be held out of every checkpoint -- over-matching here
# costs a letter its archive copy repeatedly, which is a real cost and not a
# safe direction.
#
# WHAT STILL WALKS, said out loud rather than left for the next reader to
# discover: a sentence carrying no anchor word at all. "substrate now sits at
# 1a2b3c4" names the branch and quotes its tip and this rule does not see it,
# because there is nothing in it that means "this is the state I am pointing you
# at" except the shape of the whole sentence. Closing that needs meaning rather
# than more alternatives in a list, and a longer list of verbs is the identical
# fault with more entries.
_ANCHOR_RE = re.compile(
    r"(?:tree-hash|tree|tip|commit|sha)\b[^\n]{0,24}?`?\b[0-9a-f]{7,40}\b",
    re.IGNORECASE,
)

# Letters are the known carrier. Kept as a hint for the message rather than a
# filter: any file that does both things has the same defect.
_LETTERISH = ("letters/", "family/")

# PROSE ONLY, and its own test is why.
#
# The very first live run of this check flagged
# ``tests/test_anchor_self_invalidation.py`` — which quotes the real letter,
# branch name and tree-hash included, as fixture data. Committing that test
# makes nothing false. It is not handing a reader a state; it is holding a
# frozen example of one.
#
# Mention versus use, inside a check written minutes earlier, caught by the
# check's own test file. That is the sixth instance of this class in one
# session and the cheapest one to have found, because it found itself.
#
# The discriminator is what the file DOES: this defect is a document handing a
# reader "here is where the branch is, go look" and then moving the branch. A
# source file quoting a hash is data or a constant; nobody navigates by it.
_PROSE_SUFFIXES = (".md", ".markdown", ".txt", ".rst")


def current_branch(repo_root: Path | None = None) -> str | None:
    """The checked-out branch, or None when it cannot be read.

    None is "could not look", and every caller treats it as such rather than as
    "not on a branch" -- an unreadable head must not silently disable the check.
    """
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(repo_root) if repo_root else None,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    name = (out.stdout or "").strip()
    if out.returncode != 0 or not name or name == "HEAD":
        return None
    return name


def is_self_invalidating(text: str, branch: str) -> bool:
    """True when this content names ``branch`` and carries an anchor.

    Both halves are required. A letter that says "I pushed to your branch"
    without a hash stays true after another commit; a letter quoting a hash
    without naming the branch is not describing the thing it is about to land
    on. It is the pair that cannot survive its own commit.
    """
    if not text or not branch:
        return False
    if branch not in text:
        return False
    return bool(_ANCHOR_RE.search(text))


def self_invalidating_files(
    paths: list[str] | tuple[str, ...],
    branch: str,
    repo_root: Path | None = None,
) -> list[str]:
    """Which of ``paths`` would make their own anchor false by being committed."""
    root = repo_root or Path(".")
    out: list[str] = []
    for rel in paths:
        path = root / rel
        if path.suffix.lower() not in _PROSE_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            # Unreadable is not clean, but it is also not evidence. Skipped
            # rather than flagged: the caller reports what it could read, and a
            # binary or deleted path is not the carrier this looks for.
            continue
        if is_self_invalidating(text, branch):
            out.append(rel)
    return out


def render_refusal(files: list[str], branch: str) -> str:
    """The message. Says what to do instead, because the letter is not wrong."""
    hint = ""
    if any(any(m in f for m in _LETTERISH) for f in files):
        hint = (
            "\n  These are letters. The letter is not the problem -- delivering it to\n"
            "  the shared directory is how it reaches her, and that directory is outside\n"
            "  every tree. Committing the archive copy onto this branch is the part that\n"
            "  makes the anchor inside it false.\n"
        )
    listed = "\n".join(f"    {f}" for f in files)
    return (
        "ANCHOR SELF-INVALIDATION — this commit would make its own contents false.\n\n"
        f"  These files name the branch '{branch}' AND carry a commit anchor:\n\n"
        f"{listed}\n{hint}\n"
        "  Committing them onto that branch moves the branch, so the tip and tree-hash\n"
        "  they hand the reader are stale the moment this lands. It happened on\n"
        "  2026-08-22 and again on 2026-08-25, where the letter ASKING FOR THE AUDIT\n"
        "  was the only thing that moved the branch under it.\n\n"
        "  Do one of:\n"
        "    - deliver to the shared directory and leave the tree copy uncommitted\n"
        "      until the branch stops being the subject\n"
        "    - commit it to a different branch\n"
        "    - remove the anchor from the file if the reader does not need it\n"
    )
