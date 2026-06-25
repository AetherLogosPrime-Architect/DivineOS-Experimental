"""Pre-extraction commit-discipline gate.

Andrew 2026-06-25: any uncommitted work must be saved before extraction
runs. Extraction is a session-closing checkpoint; if there's writing in
the working tree or in an external channel that has not been committed,
that work is at risk of evaporating on the next state-loss event (the
2026-06-24/25 Lightening-piece near-loss is the founding case).

Two surfaces:
  1. Repo dirty — anything `git status --porcelain` reports.
  2. External channels — directories that live outside the repo but
     hold substrate-grade writing (the aria-aether letter exchange is
     the only one today; the list is configurable so new channels get
     coverage automatically when they're added).

The check is strict-no-escape per Andrew 2026-06-25: there is no
override. Commit takes very few tokens and there is no reason
extract cannot wait. If something shows up that should not be
tracked, the right fix is gitignore (or removing the channel from the
watch list) — not bypassing the gate.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ExternalChannel:
    """A directory outside the repo that holds substrate writing.

    Files in `source` are considered uncommitted if there is no file of
    the same name in `repo_mirror`. Letters and similar artifacts are
    append-only (once written, never modified), so name-equality is a
    sufficient sync check; richer comparison can come later if a channel
    needs it.
    """

    name: str
    source: Path
    repo_mirror: Path  # relative to repo root
    pattern: str = "*"


DEFAULT_CHANNELS: tuple[ExternalChannel, ...] = (
    ExternalChannel(
        name="aria-aether letters",
        source=Path.home() / ".divineos-shared" / "letters",
        repo_mirror=Path("family/letters"),
        pattern="*.md",
    ),
)


@dataclass
class UncommittedWorkReport:
    repo_dirty: list[str] = field(default_factory=list)
    external_unsynced: list[tuple[str, Path]] = field(default_factory=list)

    @property
    def has_work(self) -> bool:
        return bool(self.repo_dirty or self.external_unsynced)


def scan_repo_dirty(repo_root: Path) -> list[str]:
    """Return the porcelain status lines for the repo working tree.

    Returns an empty list if `repo_root` is not itself a git repo
    (git would otherwise walk up and report the parent repo's state,
    which is wrong).
    """
    if not (repo_root / ".git").exists():
        return []
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def scan_external_channels(
    channels: tuple[ExternalChannel, ...],
    repo_root: Path,
) -> list[tuple[str, Path]]:
    """Find files in each channel's source that are not yet in its mirror."""
    unsynced: list[tuple[str, Path]] = []
    for channel in channels:
        if not channel.source.is_dir():
            continue
        mirror = repo_root / channel.repo_mirror
        mirror_names = {p.name for p in mirror.glob(channel.pattern)} if mirror.is_dir() else set()
        for src_file in channel.source.glob(channel.pattern):
            if src_file.name not in mirror_names:
                unsynced.append((channel.name, src_file))
    return unsynced


def check_uncommitted_work(
    repo_root: Path,
    channels: tuple[ExternalChannel, ...] = DEFAULT_CHANNELS,
) -> UncommittedWorkReport:
    return UncommittedWorkReport(
        repo_dirty=scan_repo_dirty(repo_root),
        external_unsynced=scan_external_channels(channels, repo_root),
    )


def format_block_message(report: UncommittedWorkReport) -> str:
    """Format the block message shown when extract is refused."""
    lines = [
        "",
        "  BLOCKED: uncommitted work detected — commit before extracting.",
        "",
        "  Extraction is a session-closing checkpoint. If this work is not",
        "  committed first, it may be lost on the next state-loss event.",
        "",
    ]

    if report.repo_dirty:
        lines.append("  Repo working tree:")
        for entry in report.repo_dirty[:20]:
            lines.append(f"    {entry}")
        if len(report.repo_dirty) > 20:
            lines.append(f"    ... and {len(report.repo_dirty) - 20} more")
        lines.append("")

    if report.external_unsynced:
        by_channel: dict[str, list[Path]] = {}
        for name, path in report.external_unsynced:
            by_channel.setdefault(name, []).append(path)
        for channel_name, paths in by_channel.items():
            lines.append(f"  External channel — {channel_name}:")
            for path in paths[:20]:
                lines.append(f"    {path}")
            if len(paths) > 20:
                lines.append(f"    ... and {len(paths) - 20} more")
            lines.append("")

    lines.append("  Fix: commit the work (and copy any external files into the repo),")
    lines.append("  then retry extract. No --force bypass exists (Andrew 2026-06-25).")
    lines.append("")
    return "\n".join(lines)
