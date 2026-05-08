"""Ablation summary briefing surface.

Surfaces the count of mechanisms with measured-ablation-evidence vs
mechanisms not yet measured at briefing time. Closes the visibility
gap that PR #313 (design brief) and PR #314 (catalog) and PR #316
(toggles) and PRs #317-#318 (measurements) collectively address: the
agent should know which mechanisms have empirical backing without
having to manually run divineos prereg list or query knowledge entries.

Per chunk 5 of docs/per-mechanism-ablation-design-brief.md.

Counts come from two sources:
* knowledge entries tagged ablation-evidence (filed by ablation_runner)
* the mechanism catalog at docs/mechanism-claims.md (priority count)

When the catalog or knowledge store is unavailable, the surface returns
empty string (null-safe per the project pattern).

Mirrors the foundations_briefing_surface and council_walks patterns.
"""

from __future__ import annotations

from pathlib import Path

_CATALOG_REL = "docs/mechanism-claims.md"


def _find_repo_root(start: Path | None = None) -> Path | None:
    """Walk up from start to find a directory containing .git."""
    here = start if start is not None else Path.cwd()
    try:
        here = here.resolve()
    except OSError:
        return None
    for candidate in (here, *here.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _find_main_repo_root(worktree_root: Path) -> Path | None:
    git_marker = worktree_root / ".git"
    if not git_marker.is_file():
        return None
    try:
        text = git_marker.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not text.startswith("gitdir:"):
        return None
    gitdir = Path(text[len("gitdir:") :].strip())
    try:
        gitdir = gitdir.resolve()
    except OSError:
        return None
    if len(gitdir.parents) < 3:
        return None
    return gitdir.parents[2]


def _catalog_path(start: Path | None = None) -> Path | None:
    """Locate docs/mechanism-claims.md across worktree + main repo."""
    worktree_root = _find_repo_root(start)
    if worktree_root is None:
        return None
    candidates = []
    main_root = _find_main_repo_root(worktree_root)
    if main_root is not None and main_root != worktree_root:
        candidates.append(main_root)
    candidates.append(worktree_root)
    for root in candidates:
        p = root / _CATALOG_REL
        if p.is_file():
            return p
    return None


def _count_priority_mechanisms(catalog_text: str) -> int:
    """Count entries under the priority section of the catalog."""
    lines = catalog_text.splitlines()
    in_priority = False
    count = 0
    for line in lines:
        if line.startswith("## Priority mechanisms"):
            in_priority = True
            continue
        if in_priority and line.startswith("## "):
            break
        if in_priority and line.startswith("### "):
            count += 1
    return count


def _count_ablation_evidence_entries() -> int:
    """Count knowledge / ledger entries containing ABLATION EVIDENCE.

    Uses divineos search CLI via subprocess so this surface stays
    decoupled from internal knowledge-store APIs. Returns 0 on any error
    (null-safe).
    """
    import re
    import subprocess

    try:
        result = subprocess.run(
            ["divineos", "search", "ABLATION EVIDENCE"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return 0
    if result.returncode != 0:
        return 0
    match = re.search(r"=== (\d+) matches", result.stdout)
    if not match:
        return 0
    return int(match.group(1))


def format_for_briefing(start: Path | None = None) -> str:
    """Return a briefing block on ablation-evidence coverage.

    Returns empty string if the catalog does not exist (null-safe).
    """
    catalog = _catalog_path(start=start)
    if catalog is None:
        return ""
    try:
        catalog_text = catalog.read_text(encoding="utf-8")
    except OSError:
        return ""

    priority_count = _count_priority_mechanisms(catalog_text)
    if priority_count == 0:
        return ""

    evidence_count = _count_ablation_evidence_entries()

    lines = [
        "[ablation evidence] "
        + str(evidence_count)
        + " of "
        + str(priority_count)
        + " priority mechanisms have measured-ablation-evidence filed:",
        "  Run: python scripts/ablation_runner.py <mechanism>   |   divineos ask ablation-evidence",
        "  Per per-mechanism-ablation-design-brief.md (prereg-8af86ea36827, find-07e9f041c051)",
    ]
    return chr(10).join(lines) + chr(10)


__all__ = ["format_for_briefing"]
