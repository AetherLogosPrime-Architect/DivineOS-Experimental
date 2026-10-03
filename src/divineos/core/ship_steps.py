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
        in_letter = pattern.search(text)
        if in_letter and _names_head(in_letter.group(1), head_sha):
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
    head = _git(repo, "rev-parse", head_sha)
    confirmed = _git(repo, "rev-parse", confirmed_sha)
    if head == confirmed:
        return Verdict(True, "head is the confirmed commit")
    parents = _git(repo, "log", "-1", "--format=%P", head).split()
    if len(parents) != 2 or parents[0] != confirmed:
        return Verdict(
            False, f"head {head[:9]} is not a merge of the confirmed {confirmed[:9]} with main"
        )
    proc = subprocess.run(
        ["git", "-C", str(repo), "merge-tree", "--write-tree", confirmed, parents[1]],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return Verdict(
            False, "the confirmed head and main do not merge cleanly, so a resolution was authored"
        )
    expected = proc.stdout.splitlines()[0].strip()
    differing = _git(repo, "diff", "--name-only", expected, head).splitlines()
    authored = [p for p in differing if p not in GENERATED]
    if authored:
        return Verdict(False, "changed beyond the three-way merge: " + ", ".join(authored))
    tail = " apart from the regenerated register" if differing else ""
    return Verdict(True, f"tree equals merge({confirmed[:9]}, {parents[1][:9]}){tail}")
