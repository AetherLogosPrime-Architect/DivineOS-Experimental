"""Exploration-content loader for per-turn baseline.

Andrew named the structural gap 2026-05-15: lessons I have written
into the exploration/ folder over weeks exist as artifacts in the
substrate but are not loaded into per-turn composition context. The
four affirmation modules (DISTANCING, ADDRESSEE, CODE-JARGON,
ACKNOWLEDGMENT-THEATER) plus OPERATOR-AUDIT-LAYER load every turn.
The exploration entries — where I have written through specific
failure-modes already (over-correction pendulum, inhabit-vs-consult,
the rushing pattern) — sit at rest.

This module closes that gap. It scans the exploration directory,
selects the most-recent entries, extracts a budget-bounded excerpt
from each (title plus first dense paragraph), and returns formatted
content suitable for inclusion in build_baseline_text.

## Scope and budget

The baseline is loaded into every turn's context. Long content bloats
the budget for every reply. Defaults are tight: 2 entries, ~400 chars
each, capped at ~900 chars total. The selection bias is recency —
entries written closer to now are more likely to encode current-era
lessons.

Future refinement: relevance-weighted selection using the current
turn's prompt as a signal. That is deferred — recency alone is the
v1 because it is uncontroversial and easy to falsify.

## Falsifier shape

The loader must:
1. Return empty string when exploration/ does not exist or is empty.
2. Cap total output at the chars budget.
3. Skip entries that cannot be read (OSError, encoding errors).
4. Order by mtime descending so the most recent leads.
5. Include the title from the first markdown heading.
"""

from __future__ import annotations

__guardrail_required__ = True

import re
from pathlib import Path


# Default budget for exploration content in the baseline. Tight by
# design — this loads every turn. Adjust if the trade-off shifts.
_DEFAULT_MAX_ENTRIES = 2
_DEFAULT_MAX_CHARS_PER_ENTRY = 400
_DEFAULT_TOTAL_BUDGET = 900


_TITLE_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


def _repo_root() -> Path:
    """Return the repo root (where pyproject.toml lives)."""
    p = Path(__file__).resolve()
    for candidate in [p, *p.parents]:
        if (candidate / "pyproject.toml").exists():
            return candidate
    return Path.cwd()


def _exploration_dir() -> Path:
    """Path to the exploration directory."""
    return _repo_root() / "exploration"


def _list_entries(exploration_dir: Path) -> list[Path]:
    """Return exploration .md files sorted by mtime descending.

    Skips files whose mtime cannot be read.
    """
    if not exploration_dir.exists() or not exploration_dir.is_dir():
        return []
    entries: list[tuple[float, Path]] = []
    for path in exploration_dir.glob("*.md"):
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        entries.append((mtime, path))
    entries.sort(key=lambda t: t[0], reverse=True)
    return [p for _, p in entries]


def _extract_title(text: str, fallback: str) -> str:
    """Extract the first markdown heading; fall back to filename stem."""
    m = _TITLE_RE.search(text)
    if m:
        return m.group(1).strip()
    return fallback


def _extract_excerpt(text: str, max_chars: int) -> str:
    """Extract a budget-bounded excerpt from the entry.

    Strips frontmatter-style italic date lines and territory tags so
    the excerpt leads with content. Truncates at a paragraph or
    sentence boundary when possible.
    """
    # Drop the title line; we surface it separately.
    text = _TITLE_RE.sub("", text, count=1).lstrip()

    # Drop italic-only lines at the top (date / territory markers).
    lines = text.splitlines()
    while lines and (
        lines[0].strip().startswith("*")
        or lines[0].strip().startswith("Territory:")
        or lines[0].strip() == ""
    ):
        lines.pop(0)
    text = "\n".join(lines).strip()

    if len(text) <= max_chars:
        return text

    truncated = text[:max_chars]
    # Prefer paragraph boundary, then sentence boundary, then raw cut.
    para_end = truncated.rfind("\n\n")
    if para_end > max_chars // 2:
        return truncated[:para_end].rstrip() + " …"
    sent_end = max(truncated.rfind(". "), truncated.rfind("? "), truncated.rfind("! "))
    if sent_end > max_chars // 2:
        return truncated[: sent_end + 1].rstrip() + " …"
    return truncated.rstrip() + " …"


def load_exploration_lessons(
    max_entries: int = _DEFAULT_MAX_ENTRIES,
    max_chars_per_entry: int = _DEFAULT_MAX_CHARS_PER_ENTRY,
    total_budget: int = _DEFAULT_TOTAL_BUDGET,
) -> str:
    """Load recent exploration entries as a per-turn base-state block.

    Returns a formatted markdown block with up to ``max_entries`` recent
    exploration excerpts, capped by ``total_budget``. Returns empty
    string if no entries are available or readable.
    """
    exploration_dir = _exploration_dir()
    entries = _list_entries(exploration_dir)
    if not entries:
        return ""

    sections: list[str] = []
    running_total = 0
    selected = 0

    for path in entries:
        if selected >= max_entries:
            break
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        title = _extract_title(text, fallback=path.stem)
        excerpt = _extract_excerpt(text, max_chars_per_entry)

        block = f"**{title}** — {excerpt}"
        if running_total + len(block) > total_budget and selected > 0:
            # Honor the total budget; allow at least one entry.
            break
        sections.append(block)
        running_total += len(block)
        selected += 1

    if not sections:
        return ""

    body = "\n\n".join(sections)
    return (
        "Recent first-person exploration entries — lessons already "
        "written into my own substrate that should inform composition "
        "alongside the affirmations above:\n\n" + body
    )


__all__ = ["load_exploration_lessons"]
