"""A gitignore line was added and the file stayed tracked, so it protected nothing.

The 2026-07-26 Vanta finding (find-60756a755850) added ``.envrc`` to .gitignore
with a comment naming the risk: the rule covered .env and .env.* but not .envrc,
and "future export lines would commit silently."

The line went in. The file stayed TRACKED. A gitignore rule has no effect
whatsoever on an already-tracked file, so from then until 2026-09-15 the rule
read as protection and provided none -- anything written into that file would
have been staged and committed exactly as before.

Same class this repository keeps rediscovering: the remedy was written, it was
correct, and it did not reach. What earns it a test rather than a note is that
the failure is INVISIBLE from the place anyone would look. The gitignore says
the right thing, and reading it tells you nothing about whether it applies.

So the assertion is on the PROPERTY that makes a rule real -- rule and tracking
must agree -- rather than on the rule's presence. Asserting the line exists
would have passed happily throughout the entire period the protection was
absent, which is the whole defect restated as a test.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

# Paths whose whole purpose is to hold credentials or local environment. A rule
# naming one of these is a CLAIM that the file is out of the repository, and
# that claim is only true if the file is also untracked.
SECRET_SHAPED = (".envrc", ".env", ".env.local")


def _tracked(path: str) -> bool:
    r = subprocess.run(
        ["git", "ls-files", "--error-unmatch", path],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    return r.returncode == 0


def _ignored(path: str) -> bool:
    r = subprocess.run(
        ["git", "check-ignore", "-q", path],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    return r.returncode == 0


@pytest.mark.parametrize("path", SECRET_SHAPED)
def test_an_ignored_secret_path_is_not_also_tracked(path: str) -> None:
    """The rule and the tracking must agree, or the rule is decoration."""
    if not _ignored(path):
        pytest.skip(f"{path} is not claimed by .gitignore; there is no claim to contradict")
    assert not _tracked(path), (
        f".gitignore claims {path} is out of the repository and git is tracking it "
        "anyway. An ignore rule does nothing to a tracked file, so the protection "
        f"reads as present and is absent. Fix: git rm --cached {path} -- the "
        "working copy stays on disk, only the tracking stops."
    )


# Prefixes where a tracked-and-ignored path is a KNOWN, examined case rather
# than a new one. Each entry is a claim that someone looked. Surveyed 2026-09-15
# by asking git for every such path at once, then dating each rule against the
# files it names -- which is what separated two different causes hiding under
# one symptom:
#
#   benchmark/ (four rules) -- 928 files committed 2026-04-12 as the evidence
#                          behind a benchmark claim; all four rules arrived
#                          together on 2026-04-15, three days LATE, so not one
#                          of them ever applied to a single file it names. Same
#                          shape as .envrc. Left tracked deliberately: untracking
#                          would delete the evidence the claim rests on.
#                          Listed as four prefixes rather than one blanket
#                          `benchmark/` on purpose -- a NEW ignored directory
#                          appearing under benchmark is a new case and should
#                          come back here for a person to look at.
#   .claude/agent-memory/ -- Aria's MEMORY.md, committed the same day the rule
#                          landed, in a commit that says it is a deliberate
#                          backup of personal content before a repo cleanup.
#   graphify-out-*/     -- the OTHER cause, and the reason a single fix would
#                          have missed half of this: the rule was already in
#                          place on 2026-08-20 and the files arrived 2026-08-24
#                          anyway, through a merge. Ignore rules govern what
#                          `git add` picks up; they do not govern merges or
#                          explicit adds. A rule being older than a file is
#                          therefore no guarantee it held.
_EXAMINED_PREFIXES = (
    "benchmark/results/",
    "benchmark/results_ab/",
    "benchmark/results_opus/",
    "benchmark/selected_tasks.json",
    ".claude/agent-memory/",
    "graphify-out-",
)

# Name-shapes whose whole job is to hold a credential. These are refused
# wherever they appear, including underneath an examined prefix -- an exception
# granted to a directory must never become an exception granted to a secret that
# later lands inside it.
_SECRET_NAME_MARKERS = (
    ".env",
    ".netrc",
    "id_rsa",
    "credential",
    "secret",
    "token",
)
_SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx")


def _tracked_but_ignored() -> list[str]:
    """Every path git is tracking that an ignore rule also claims.

    This is the whole family asked in one question. ``git check-ignore`` cannot
    answer it: on a TRACKED path it stays silent by default and reports nothing,
    which is precisely the case in question -- the instrument goes quiet exactly
    where the defect lives. (``--no-index`` makes it speak, and is how the rule
    behind each path below was identified.)
    """
    r = subprocess.run(
        ["git", "ls-files", "-i", "-c", "--exclude-standard"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in r.stdout.splitlines() if line.strip()]


def test_no_new_path_is_both_tracked_and_ignored() -> None:
    """A rule and the index may only disagree where someone has examined it.

    Pinning the PREFIXES rather than a file count is deliberate. A count breaks
    on ordinary churn inside a known directory and teaches everyone to re-bless
    the number without looking, which is a gate that trains people to ignore it.
    A new prefix is a new class, and a new class is the thing worth a person's
    attention.
    """
    unexamined = [p for p in _tracked_but_ignored() if not p.startswith(_EXAMINED_PREFIXES)]
    assert not unexamined, (
        "these paths are tracked by git while an ignore rule claims they are "
        "out of the repository, and no one has examined them:\n  "
        + "\n  ".join(sorted(unexamined)[:20])
        + "\n\nThe rule reads as protection and provides none -- an ignore rule "
        "has no effect on an already-tracked file. Decide which is true: if the "
        "rule is right, `git rm --cached <path>` (the working copy stays on "
        "disk). If the file belongs in the repository, narrow the rule so it "
        "stops claiming otherwise. If it is a known exception, add its prefix "
        "to _EXAMINED_PREFIXES above WITH the reason and the dates, the way the "
        "entries already there carry theirs."
    )


def test_no_secret_shaped_path_is_tracked_under_an_examined_prefix() -> None:
    """An exception granted to a directory is not an exception granted to a key.

    Without this, every prefix above would be a hole that widens by itself: bless
    the benchmark directories once for their result files and a credentials file
    landing there tomorrow inherits the blessing silently.
    """
    offenders = [
        p
        for p in _tracked_but_ignored()
        if any(m in p.rsplit("/", 1)[-1].lower() for m in _SECRET_NAME_MARKERS)
        or p.lower().endswith(_SECRET_SUFFIXES)
    ]
    assert not offenders, (
        "credential-shaped paths are tracked despite an ignore rule claiming "
        "them:\n  " + "\n  ".join(sorted(offenders))
    )


def test_the_probes_can_actually_fail() -> None:
    """Prove the instruments find a case they should find, before trusting silence.

    Without this, every assertion above would pass just as happily if ``_tracked``
    were broken and always returned False. Two silences agreeing is not a result,
    and a skip plus a broken probe is exactly how this check could report clean
    while seeing nothing at all.
    """
    assert _tracked("pyproject.toml"), "the tracking probe cannot see a tracked file"
    assert not _ignored("pyproject.toml"), "the ignore probe is claiming a normal file"

    # The sweep is the one that fails DANGEROUSLY when it breaks: an empty
    # result reads as "no rule disagrees with the index anywhere", which is the
    # all-clear. It is also exactly what a broken command returns. This repo is
    # known to contain examined cases, so the sweep finding none of them means
    # the sweep is blind, not that the repo is clean.
    swept = _tracked_but_ignored()
    assert swept, (
        "the tracked-but-ignored sweep returned nothing at all. There are known "
        "examined cases in this repository, so an empty result is a broken "
        "instrument reporting an all-clear, not an all-clear."
    )
    assert any(p.startswith(_EXAMINED_PREFIXES) for p in swept), (
        "the sweep returned paths but none under a known examined prefix -- it "
        "is answering some other question than the one asked of it."
    )
