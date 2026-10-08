"""The checks `divineos ship` runs in order, each one a yes or a named no.

Dad, 2026-10-02: "if you are forgetting rules then those are rife for
automation so they cannot be forgotten". Merging four confirmed PRs took three
or four tries each because the rules were chained by hand. This module holds
the two checks that decide whether a merge may happen at all.

Draft: docs/drafts/one_command_from_confirm_to_main_draft_2026-10-02.md.
Walks: council-85a8c91b7b18 (the design), council-bca63f12fe32 (this file).
Prior art read: scripts/merge_preview.py also runs `git merge-tree`, but it
answers "would this merge delete anything", not "is this head only the
confirmed commit plus main", so it is not reused here.

Two rules from Aletheia's reading of the draft (2026-10-02) shape it:

1. A confirm counts only from her own letter as it lands, never from a CONFIRMS
   line quoted inside someone else's letter. So a finding is not enough on its
   own -- findings are transcribed by me, and anything I type as her would be
   trusted. The finding must name its source letter, the letter must be hers
   (aletheia-to-*) and must itself contain the exact CONFIRMS line.
2. "Floor-only" counts only when proven by the three-way check, never on a
   PR's or a letter's say-so: the landed tree must equal merge(confirmed head,
   main), with only the generated register tolerated.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

# Regenerated from the tree on every catch-up, so both sides are stale
# renderings and a difference there is not an authored change.
GENERATED = frozenset({"docs/AUTOMATION_REGISTER.md"})

_LETTER_NAME = re.compile(r"(aletheia-to-[A-Za-z0-9._-]+\.md)")


def _confirm_line(pr: int) -> re.Pattern[str]:
    # The head may be quoted at any length from 7 characters up.
    return re.compile(rf"CONFIRMS:\s*#{pr}\s+at\s+`?([0-9a-f]{{7,40}})`?", re.IGNORECASE)


def _names_head(found: str, head_sha: str) -> bool:
    return len(found) >= 7 and head_sha.lower().startswith(found.lower())


def _signed_heads(text: str, verb: str, pr: int) -> list[str]:
    """Every head named by a line of hers in her signed shape, for this pr.

    Her real lines, all fifteen observed in family/letters on 2026-10-03:
    `> CONFIRMS: #578 at 9a02f8353. <optional sentence> — Aletheia Sophia
    Risner, 2026-10-02`. Only that shape counts -- a confirm quoted inside a
    withdrawal, or mentioned in prose, is the same words in a different game
    (Aletheia, 2026-10-03: her withdrawn #554 confirm returned True). From
    that day she writes withdrawals in the same shape with WITHDRAWN. Every
    matching line is returned, not the first.
    """
    line = re.compile(
        rf"^>\s*{verb}:\s*#{pr}\s+at\s+`?([0-9a-f]{{7,40}})`?\.[^\n]*—\s*Aletheia Sophia Risner\b",
        re.IGNORECASE | re.MULTILINE,
    )
    return [m.group(1) for m in line.finditer(text)]


def _withdrawn_in(letters_dir: Path, pr: int, head_sha: str) -> str | None:
    """The name of a letter of hers that withdraws this pr at this head."""
    for letter in sorted(letters_dir.glob("aletheia-to-*.md")):
        try:
            text = letter.read_text(encoding="utf-8")
        except OSError:
            continue
        if any(_names_head(h, head_sha) for h in _signed_heads(text, "WITHDRAWN", pr)):
            return letter.name
    return None


@dataclass(frozen=True)
class Confirm:
    round_id: str
    letter: str


@dataclass(frozen=True)
class Verdict:
    ok: bool
    reason: str
    confirm: Confirm | None = None


def confirm_in(findings, pr: int, head_sha: str, letters_dir: Path) -> Verdict:
    """Find Aletheia's confirm of THIS pr at THIS head, proven by her letter.

    `findings` is any iterable of objects with round_id, actor, title and
    description. A round that confirms a different PR never counts and is
    never offered: one approval quietly standing in for another is the fault
    she ranked most serious (#555, 2026-09-29 and again 2026-10-02).

    KNOWN LIMIT: this trusts that a file named aletheia-to-*.md in the letters
    folder is hers. Dad carries her letters into that folder; nothing here can
    tell a letter he carried from one written into the folder by someone else.
    """
    pattern = _confirm_line(pr)
    claimed_by = []
    for f in findings:
        if str(getattr(f, "actor", "")).lower() != "aletheia":
            continue
        m = pattern.search(str(getattr(f, "title", "") or ""))
        if not m or not _names_head(m.group(1), head_sha):
            continue
        round_id = str(getattr(f, "round_id", ""))
        claimed_by.append(round_id)
        letter_m = _LETTER_NAME.search(str(getattr(f, "description", "") or ""))
        if not letter_m:
            continue
        letter = letters_dir / letter_m.group(1)
        try:
            text = letter.read_text(encoding="utf-8")
        except OSError:
            continue
        if any(_names_head(h, head_sha) for h in _signed_heads(text, "CONFIRMS", pr)):
            withdrawn = _withdrawn_in(letters_dir, pr, head_sha)
            if withdrawn:
                return Verdict(
                    False,
                    f"{withdrawn} withdraws her confirm of #{pr} at {head_sha[:9]}",
                )
            return Verdict(
                True,
                f"{letter.name} confirms #{pr} at {head_sha[:9]}",
                Confirm(round_id, letter.name),
            )
    if claimed_by:
        return Verdict(
            False,
            f"round {claimed_by[0]} records her confirm of #{pr} at {head_sha[:9]}, "
            "but no letter of hers in the letters folder carries that line",
        )
    return Verdict(False, f"no confirm from Aletheia names #{pr} at {head_sha[:9]}")


def _git(repo: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


def floor_proven(repo: Path, confirmed_sha: str, head_sha: str) -> Verdict:
    """Is head only the confirmed commit plus main, proven three-way?

    True when head IS the confirmed commit, or head is a merge whose first
    parent is the confirmed commit and whose tree equals
    `git merge-tree --write-tree <confirmed> <main parent>`, ignoring only the
    generated register. Anything else is an authored change and goes back to
    the reviewer.
    """
    # Refuse to judge a state that is not what will be pushed. Mid-merge, HEAD
    # still points at the confirmed commit, and this once answered "head is the
    # confirmed commit" -- a confident wrong answer (Aletheia, 2026-10-02:
    # refusing mid-merge "matters most"). Walk council-132839c81397.
    # The marker list is the house's one list (auto_commit._MID_OP_MARKERS);
    # the git dir is asked of git, because in a worktree .git is a pointer
    # file, not a folder, and a fixed repo/".git" path never sees the markers.
    from divineos.core.auto_commit import _MID_OP_MARKERS

    git_dir = Path(_git(repo, "rev-parse", "--absolute-git-dir"))
    for marker in _MID_OP_MARKERS:
        if (git_dir / marker).exists():
            return Verdict(
                False, f"a git operation is in progress ({marker}); finish or abort it first"
            )
    if _git(repo, "status", "--porcelain", "--untracked-files=no"):
        return Verdict(False, "the working tree has uncommitted changes; commit them before asking")
    return head_is_only(repo, confirmed_sha, head_sha)


SHORTEST_SHA = 7


def _commit(repo: Path, sha: str) -> str | None:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}"],
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip() if proc.returncode == 0 else None


def head_is_only(
    repo: Path, confirmed_sha: str, head_sha: str, main_ref: str = "origin/main"
) -> Verdict:
    """Is head only the confirmed commit plus floor from main? Graph only.

    Pure: reads commits, never the working tree, so the merge gate can ask it of
    a PR without some other window's state refusing the PR (Dijkstra, room two,
    docs/drafts/an_approval_names_the_version_it_saw_draft_2026-10-05.md).
    Only the final tree lands, so one check against the newest floor stands in
    for any number of catch-ups (Dijkstra, room three): the confirmed commit is
    an ancestor of head, head's newest main parent is on main, and head's tree
    equals the clean three-way merge of the two, the regenerated register aside.
    Every refusal names both versions and the check that failed (Norman).
    Dad's standing permission for floor-only moves: 09-03, 09-05, 09-24, 10-05.
    """
    # A hand-typed version from an approval ("CONFIRMS: #N at abc1234") is hex;
    # a short one matches too much. Named refs come only from the house's own
    # callers and must still resolve. An approval naming a ref ("at main") is a
    # door, closed where approvals are read: the merge gate takes only hex.
    typed = confirmed_sha.strip()
    if re.fullmatch(r"[0-9a-fA-F]+", typed) and len(typed) < SHORTEST_SHA:
        return Verdict(
            False,
            f"'{confirmed_sha}' is shorter than {SHORTEST_SHA} characters: a guess, not a version",
        )
    confirmed = _commit(repo, confirmed_sha)
    head = _commit(repo, head_sha)
    if confirmed is None or head is None:
        missing = confirmed_sha if confirmed is None else head_sha
        return Verdict(False, f"could not see commit {missing} here; fetch it first (never a pass)")
    if head == confirmed:
        return Verdict(True, "head is the confirmed commit")
    is_ancestor = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", confirmed, head],
        capture_output=True,
    )
    if is_ancestor.returncode != 0:
        return Verdict(False, f"the confirmed {confirmed[:9]} is not in head {head[:9]}'s history")
    parents = _git(repo, "log", "-1", "--format=%P", head).split()
    if len(parents) != 2:
        return Verdict(
            False,
            f"head {head[:9]} is not a catch-up merge, so something was authored after "
            f"{confirmed[:9]} was confirmed; that goes back to the reviewer",
        )
    newest_floor = parents[1]
    # Ancestry, not equality: main may move after the catch-up (walk-d028b6a2d5f3).
    # And it refuses a merge of anything that is not main (Aria, 2026-10-04).
    on_main = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", newest_floor, main_ref],
        capture_output=True,
    )
    if on_main.returncode != 0:
        return Verdict(
            False,
            f"the merged-in parent {newest_floor[:9]} is not on this computer's copy of main "
            f"({main_ref}). If main moved recently that copy may be stale: fetch it and run "
            "again. If it is current, something other than main was merged in.",
        )
    proc = subprocess.run(
        ["git", "-C", str(repo), "merge-tree", "--write-tree", confirmed, newest_floor],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return Verdict(
            False,
            f"the confirmed {confirmed[:9]} and main at {newest_floor[:9]} do not merge cleanly, "
            "so a resolution was authored",
        )
    expected = proc.stdout.splitlines()[0].strip()
    differing = _git(repo, "diff", "--name-only", expected, head).splitlines()
    authored = [p for p in differing if p not in GENERATED]
    if authored:
        return Verdict(
            False,
            f"head {head[:9]} changed beyond confirmed {confirmed[:9]} plus main: "
            + ", ".join(authored),
        )
    tail = " apart from the regenerated register" if differing else ""
    return Verdict(True, f"tree equals merge({confirmed[:9]}, {newest_floor[:9]}){tail}")
