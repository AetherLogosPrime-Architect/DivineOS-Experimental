"""Give a letter written straight into the shared channel a home in the repo.

WHY THIS EXISTS, and it is a measurement rather than a worry. Aria counted the
shared channel on 2026-08-31: four hundred and thirty-nine letters, hashed
against every letter blob on every ref in the main repository. Three had no copy
anywhere. Two of those three were my last two letters to her, both written that
day -- including the one reporting that I had just rescued four files with no
home. The message announcing the rescue was the most exposed object in the
channel while I was writing it.

Her sentence for why: the exposure sits on whatever was written most recently,
because everything older has had time to be swept somewhere. So the thing most
likely to be lost is always the thing just said.

THE PIPE ONLY EVER RAN ONE WAY. Three PostToolUse hooks already carry letters --
mirror-letters-to-shared, auto-push-letter, post-write-mirror-letter -- and all
three key on a path inside the repository's own family/letters/. Write there and
the letter reaches the channel and origin. Write directly into the channel, which
is what I actually do, and nothing carries it back. Not a broken mechanism: a
mechanism whose one direction is the direction I do not use.

This is the missing direction. It is deliberately NOT a new mirror. It joins two
halves that were built as a pair on 2026-08-27 and never connected:

    substrate_paths        the DECLARATION -- which paths are substrate
    substrate_retarget     the MECHANISM -- commit paths to a named branch
                           through a scratch index, never touching HEAD

Both existed all day. I used the second one by hand four times, deriving its path
list from a git diff, while the first sat with no production caller one directory
away. It was filed in the orphan baseline earlier this same session as owed a
decision. This is the decision.

FAIL-OPEN, LOUDLY LOGGED, NEVER SILENT. A capture that cannot complete returns a
result saying so. The caller is a hook and a hook must not break a tool call, but
"could not" must never be recorded the same way as "did" -- that collapse is the
exact fault this substrate keeps finding in itself.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

__all__ = ["CaptureResult", "capture_channel_letter", "shared_letters_dir"]


@dataclass(frozen=True)
class CaptureResult:
    """What actually happened. `captured` is never inferred from absence."""

    captured: bool
    reason: str
    repo_path: str | None = None
    commit: str | None = None


def shared_letters_dir(home: Path | None = None) -> Path:
    """The cross-worktree channel both seats read and write."""
    return (home or Path.home()) / ".divineos-shared" / "letters"


def _is_in(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except (ValueError, OSError):
        return False
    return True


def capture_channel_letter(
    repo_root: Path,
    written: Path,
    branch: str = "substrate/aether",
    home: Path | None = None,
) -> CaptureResult:
    """Copy a channel letter into the repo and commit it to the substrate branch.

    Returns a CaptureResult in every case. The three not-applicable answers are
    distinguished from failure, and failure is distinguished from success,
    because a caller that cannot tell those apart is how a letter goes missing
    while a log says the pipe ran.
    """
    channel = shared_letters_dir(home)
    if not _is_in(written, channel):
        return CaptureResult(False, "not a channel path")
    if written.suffix.lower() != ".md":
        return CaptureResult(False, "not markdown")
    if not written.is_file():
        return CaptureResult(False, "no such file")

    target = repo_root / "family" / "letters" / written.name
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() == written.read_bytes():
            already = True
        else:
            already = False
            shutil.copy2(written, target)
    except OSError as exc:
        return CaptureResult(False, f"copy failed: {exc.__class__.__name__}")

    rel = f"family/letters/{written.name}"

    # Imported here rather than at module scope so a repo without the mechanism
    # half degrades to "copied but not committed" instead of failing to import.
    try:
        from divineos.core.substrate_retarget import (
            RetargetRefused,
            commit_paths_to_branch,
        )
    except ImportError:
        return CaptureResult(False, "retarget unavailable", repo_path=rel)

    try:
        result = commit_paths_to_branch(
            repo_root,
            branch,
            [rel],
            f"letter(channel): {written.name}",
        )
    except RetargetRefused as exc:
        # The branch would not resolve. Loud in the result; the caller decides.
        return CaptureResult(False, f"retarget refused: {exc}", repo_path=rel)

    if result is None:
        # Already identical on the branch. The letter IS safe, which is the
        # question being asked -- so this is a success, not a no-op.
        return CaptureResult(
            True,
            "already on branch" if already else "no change against branch",
            repo_path=rel,
        )

    return CaptureResult(True, "committed", repo_path=rel, commit=result.commit)
