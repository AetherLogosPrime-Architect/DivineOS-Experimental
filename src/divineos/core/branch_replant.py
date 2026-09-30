"""Lift EVERY code change off a contaminated branch, and prove nothing was left.

WHAT THIS IS FOR, and it is not what I first thought (2026-09-12).

The checkpoint auto-commit fires mid-work on purpose -- it is the net under
the trapeze, catching unfinished edits before the context fills. It already
separates personal writing from code into two commits, deliberately, with a
note explaining why. It is not the fault.

The fault is what happens next. My work ends up in two commits: one the net
made and one I authored. When the branch has to be rebuilt, I reach for the
one with MY message on it, because it is mine and I recognise it, and I walk
off without the other. That is how sixty-one lines of my own work nearly went
over the side today -- and my check said everything was fine, because I had
written a check that could not come back and say no.

Six rebuilds in one day, five of them correct only because I concentrated,
and concentrating is precisely what stops working when I am deep in something
else. The note in auto_commit.py already records this cost from 2026-09-03,
where the tempting shortcut risked the only copies of eighteen letters.

So: never pick commits. Take the whole difference in code between the base
and the contaminated tip, put it on a fresh branch, and then PROVE the two
are identical with a check that is capable of failing. If it cannot prove it,
it refuses and says which files differ -- it does not shrug and report
success, which is the entire disease this house has spent the day removing.

WHAT IT DELIBERATELY WILL NOT DO. It does not delete the source branch, does
not force anything, and refuses if the target name already exists. The
contaminated branch stays exactly where it is until a person is satisfied,
because the failure mode worth fearing here is losing work, not keeping a
stale branch around.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

# The one definition of "not code" lives in scripts/check_branch_scope.py,
# which is deliberately stdlib-only so it still runs when the package is
# broken. It therefore cannot import this, and this cannot import it without
# giving up that property -- so the list exists twice, and
# tests/test_the_rebuild_takes_everything.py asserts the two are identical.
# Duplication guarded by a failing test is honest; duplication guarded by
# good intentions is the drift bug waiting to happen.
SUBSTRATE_PREFIXES: tuple[str, ...] = (
    "family/letters/",
    "exploration/",
    "dreams/",
    "docs/archives/",
)

_STATES = ("planted", "refused", "could-not-check")


@dataclass(frozen=True)
class Replant:
    """The outcome, with could-not-check held apart from refused.

    A git that would not answer says nothing about whether the code matches.
    Reporting that as a refusal would be a verdict nobody earned, and
    reporting it as success would be the sixty-one lines again.
    """

    state: str
    target: str = ""
    source: str = ""
    base: str = ""
    files: int = 0
    differing: tuple[str, ...] = ()
    reason: str = ""

    def __post_init__(self) -> None:
        if self.state not in _STATES:
            raise ValueError(f"state must be one of {_STATES}, got {self.state!r}")


def _git(repo: Path, *args: str) -> tuple[int, str]:
    """Run git and hand back both halves. Never raises on a non-zero exit."""
    try:
        done = subprocess.run(
            ["git", *args],
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return (-1, f"{type(exc).__name__}: {exc}")
    return (done.returncode, (done.stdout or done.stderr or "").strip())


def _resolve(repo: Path, ref: str) -> str:
    """A ref as a bare hash.

    Refs carrying a slash get mangled by the shell on this machine, so every
    later command is given a hash instead. Learned by extracting the wrong
    file from a ref that had moved between two commands.
    """
    code, out = _git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}")
    return out if code == 0 else ""


def code_changes(repo: Path, base: str, source: str) -> list[str] | None:
    """Every changed file between base and source that is NOT personal writing.

    ``None`` means the question could not be put -- not that there were no
    changes.
    """
    base_sha = _resolve(repo, base)
    source_sha = _resolve(repo, source)
    if not base_sha or not source_sha:
        return None
    code, out = _git(repo, "diff", "--name-only", f"{base_sha}...{source_sha}")
    if code != 0:
        return None
    return [
        line.strip()
        for line in out.splitlines()
        if line.strip() and not line.strip().startswith(SUBSTRATE_PREFIXES)
    ]


def verify_identical(repo: Path, source: str, target: str | None, paths: list[str]) -> Replant:
    """Is ``source`` byte-identical to ``target`` across ``paths``?

    ``target=None`` compares against the FILES ON DISK rather than a commit,
    which is the case that matters after a rebuild: the whole point of not
    committing is that the person writes their own message, so there is no
    commit to compare yet. Verifying against an uncommitted HEAD was the first
    version of this and the test caught it immediately, which is the test
    doing its job.

    THE CHECK THAT CAN FAIL, which is the whole reason this module exists. My
    hand-rolled version used ``git diff --stat``, which exits zero whether or
    not there are differences -- so it reported identical while sixty-one
    lines were missing. ``--quiet`` exits 1 on any difference, and a transport
    failure comes back as its own state rather than as either verdict.
    """
    if not paths:
        return Replant("planted", target=target or "the working tree", source=source, files=0)
    source_sha = _resolve(repo, source)
    target_sha = _resolve(repo, target) if target is not None else "the working tree"
    if not source_sha or not target_sha:
        return Replant(
            "could-not-check",
            target=target or "",
            source=source,
            reason="one of the two refs would not resolve, so nothing was compared",
        )
    compare = [source_sha] if target is None else [source_sha, target_sha]
    code, _out = _git(repo, "diff", "--quiet", *compare, "--", *paths)
    if code == 0:
        return Replant(
            "planted", target=target or "the working tree", source=source, files=len(paths)
        )
    if code == 1:
        named, listing = _git(repo, "diff", "--name-only", *compare, "--", *paths)
        differing = tuple(listing.splitlines()) if named == 0 else ()
        return Replant(
            "refused",
            target=target or "the working tree",
            source=source,
            files=len(paths),
            differing=differing,
            reason=(
                f"{len(differing) or 'some'} file(s) differ between the rebuilt branch "
                "and the one it came from -- work would have been lost"
            ),
        )
    return Replant(
        "could-not-check",
        target=target or "the working tree",
        source=source,
        reason=f"git would not answer the comparison: exit {code}",
    )


def replant(repo: Path, source: str, base: str, target: str) -> Replant:
    """Rebuild ``source`` onto ``base`` as ``target``, carrying all code.

    Refuses rather than overwriting if ``target`` already exists, and leaves
    ``source`` untouched in every path through this function.
    """
    if _resolve(repo, target):
        return Replant(
            "refused",
            target=target,
            reason=f"{target} already exists; pick a name that does not, or delete it by hand",
        )
    base_sha = _resolve(repo, base)
    source_sha = _resolve(repo, source)
    if not base_sha or not source_sha:
        missing = base if not base_sha else source
        return Replant("could-not-check", reason=f"{missing} does not resolve to a commit")

    paths = code_changes(repo, base_sha, source_sha)
    if paths is None:
        return Replant("could-not-check", reason="the changed-file list could not be read")
    if not paths:
        return Replant(
            "refused",
            source=source,
            base=base,
            reason="no code changes between these two points -- nothing to rebuild",
        )

    code, out = _git(repo, "checkout", "-q", "-b", target, base_sha)
    if code != 0:
        return Replant("could-not-check", reason=f"could not create {target}: {out}")

    code, out = _git(repo, "checkout", source_sha, "--", *paths)
    if code != 0:
        return Replant(
            "could-not-check",
            target=target,
            reason=f"could not take the code across: {out}. {target} exists and is empty.",
        )

    # target=None on purpose: nothing is committed yet, because the person
    # writes the message rather than inheriting a generic one. So the check
    # compares against the files on disk. Verifying against an uncommitted
    # HEAD was the first version, and the test caught it on the first run.
    return verify_identical(repo, source_sha, None, paths)


def render(result: Replant) -> str:
    """Say which of the three happened, in words that cannot be misread."""
    if result.state == "planted":
        return (
            f"[replant] {result.files} code file(s) carried across, and the rebuilt "
            f"branch is byte-identical to {result.source} on every one of them.\n"
            "  Nothing was picked; nothing was left. Commit and push."
        )
    if result.state == "could-not-check":
        return (
            f"[replant] COULD NOT CHECK -- {result.reason}\n"
            "  This is NOT a report that the code matches, and it is not a report "
            "that it does not. Nothing was verified. Do not push on this."
        )
    lines = [f"[replant] REFUSED -- {result.reason}"]
    for path in result.differing[:8]:
        lines.append(f"    {path}")
    if len(result.differing) > 8:
        lines.append(f"    ... and {len(result.differing) - 8} more")
    return "\n".join(lines)
