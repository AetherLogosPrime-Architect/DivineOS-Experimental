"""auto-commit at substrate checkpoints — the Permanently Equip spell for commits.

Andrew 2026-07-05: "make commit automatic after extract and before sleep :)"

The gap this closes: today I finished substrate-touching work in-session and
didn't commit before rest. Andrew caught it. This module welds the commit
into the checkpoints themselves so the next time this exact shape shows up,
the commit fires without being remembered.

Three call-sites (all pointed at the same function):
  1. pre-extract  — was BLOCK, now AUTO-COMMIT (extract runs afterwards)
  2. post-extract — commit whatever extract itself wrote (self-grade,
                    journal entries, updated docs, etc.)
  3. pre-sleep    — commit any drift since extract before consolidation

Discipline:
  - Syncs external channels (aria-aether letters) into repo_mirror BEFORE
    committing, so external-only writes don't slip through.
  - `git add -A` — includes untracked. Substrate letters are often
    untracked new files.
  - Fail-soft: subprocess failures log-and-continue rather than raising.
    The point is to save work, not to block the checkpoint on git noise.
  - Idempotent: clean tree → no-op, no empty commit.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from divineos.core.uncommitted_work_check import (
    DEFAULT_CHANNELS,
    ExternalChannel,
    check_uncommitted_work,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AutoCommitResult:
    committed: bool
    reason: str  # human-readable outcome (for CLI surfacing)
    files_synced: int = 0  # external files copied into repo_mirror
    dirty_lines: int = 0  # git status --porcelain lines seen


def _sync_external_channels(
    channels: tuple[ExternalChannel, ...],
    repo_root: Path,
) -> int:
    """Copy new external-channel files into their repo_mirror.

    Same sync semantics as check_uncommitted_work.scan_external_channels,
    but performs the copy instead of only reporting. Returns the count
    of files copied. Append-only channels only (name-equality suffices;
    no content-diff needed).
    """
    copied = 0
    for channel in channels:
        if not channel.source.is_dir():
            continue
        mirror = repo_root / channel.repo_mirror
        mirror.mkdir(parents=True, exist_ok=True)
        mirror_names = {p.name for p in mirror.glob(channel.pattern)}
        for src_file in channel.source.glob(channel.pattern):
            if src_file.name in mirror_names:
                continue
            try:
                shutil.copy2(src_file, mirror / src_file.name)
                copied += 1
            except OSError as e:
                logger.warning(
                    "auto_commit: failed to sync %s from %s: %s",
                    src_file.name,
                    channel.name,
                    e,
                )
    return copied


def auto_commit_substrate(
    repo_root: Path,
    reason: str,
    channels: tuple[ExternalChannel, ...] = DEFAULT_CHANNELS,
) -> AutoCommitResult:
    """Commit any uncommitted substrate work at a checkpoint boundary.

    reason: short string that appears in the commit subject
            (e.g. "post-extract", "pre-sleep", "pre-extract").
    """
    if not (repo_root / ".git").exists():
        return AutoCommitResult(committed=False, reason="not a git repo")

    files_synced = _sync_external_channels(channels, repo_root)

    report = check_uncommitted_work(repo_root, channels=channels)
    dirty_lines = len(report.repo_dirty)

    if not report.has_work and files_synced == 0:
        return AutoCommitResult(
            committed=False,
            reason="clean tree — nothing to commit",
        )

    try:
        subprocess.run(
            ["git", "add", "-A"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        logger.warning("auto_commit: git add failed: %s", e.stderr)
        return AutoCommitResult(
            committed=False,
            reason=f"git add failed: {e.stderr.strip()[:200]}",
            files_synced=files_synced,
            dirty_lines=dirty_lines,
        )

    staged_check = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if staged_check.returncode == 0:
        return AutoCommitResult(
            committed=False,
            reason="nothing staged after add",
            files_synced=files_synced,
            dirty_lines=dirty_lines,
        )

    subject = f"auto-commit ({reason}): substrate checkpoint"
    body = (
        f"Auto-commit fired at {reason} boundary.\n\n"
        f"External files synced into repo: {files_synced}\n"
        f"Dirty-tree lines caught: {dirty_lines}\n\n"
        "Committed automatically per Andrew 2026-07-05: the commit "
        "at extract/sleep boundaries fires itself, not remembered.\n\n"
        "Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
    )
    try:
        subprocess.run(
            ["git", "commit", "-m", subject, "-m", body],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        logger.warning("auto_commit: git commit failed at %s: %s", reason, e.stderr)
        return AutoCommitResult(
            committed=False,
            reason=f"git commit failed: {e.stderr.strip()[:200]}",
            files_synced=files_synced,
            dirty_lines=dirty_lines,
        )

    return AutoCommitResult(
        committed=True,
        reason=f"committed at {reason}",
        files_synced=files_synced,
        dirty_lines=dirty_lines,
    )


def find_repo_root(start: Path) -> Path | None:
    """Walk up from `start` to the first ancestor containing .git; None if
    none found."""
    p = start.resolve()
    while p != p.parent:
        if (p / ".git").exists():
            return p
        p = p.parent
    return None
