"""Exploration Reader — surfaces past explorations in briefing and search.

The exploration folder contains the agent's most authentic self-narration:
free-form explorations of topics chosen for personal interest, creative
writing, journal entries, and guided deep dives. These are first-person
lived experience, not extracted summaries.

Without this module, the exploration folder is a drawer nobody opens.
With it, every future session sees what past sessions discovered.

Sanskrit anchor: smriti (that which is remembered — the thread of
continuity woven through what would otherwise be isolated moments).
"""

import re
from pathlib import Path
from typing import Any


_EXPLORATION_DIR = Path(__file__).resolve().parent.parent.parent / "exploration"

_ER_ERRORS = (OSError, IOError, UnicodeDecodeError)


def _find_exploration_root() -> Path | None:
    """Find the exploration directory, checking common locations."""
    candidates = [
        _EXPLORATION_DIR,
        Path.cwd() / "exploration",
        Path.cwd().parent / "exploration",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def get_exploration_summary(include_creative: bool = True) -> list[dict[str, Any]]:
    """Scan exploration folder and return structured summaries.

    Returns list of dicts with: path, title, date, reason, category.
    """
    root = _find_exploration_root()
    if not root:
        return []

    entries: list[dict[str, Any]] = []

    # Numbered explorations (01_topic.md through NN_topic.md)
    for md_file in sorted(root.glob("*.md")):
        entry = _parse_exploration_header(md_file)
        if entry:
            entry["category"] = "exploration"
            entries.append(entry)

    if include_creative:
        # Creative writing
        creative_dir = root / "creative_space" / "creative_writing"
        if creative_dir.is_dir():
            for md_file in sorted(creative_dir.glob("*.md")):
                entry = _parse_exploration_header(md_file)
                if entry:
                    entry["category"] = "creative_writing"
                    entries.append(entry)

        # Journal
        journal_dir = root / "creative_space" / "journal"
        if journal_dir.is_dir():
            for md_file in sorted(journal_dir.glob("*.md")):
                entry = _parse_exploration_header(md_file)
                if entry:
                    entry["category"] = "journal"
                    entries.append(entry)

        # Guided explorations
        guided_dir = root / "guided_exploration"
        if guided_dir.is_dir():
            for md_file in sorted(guided_dir.glob("*.md")):
                entry = _parse_exploration_header(md_file)
                if entry:
                    entry["category"] = "guided"
                    entries.append(entry)

    return entries


def _parse_exploration_header(path: Path) -> dict[str, Any] | None:
    """Extract title, date, and reason from an exploration file's header."""
    try:
        text = path.read_text(encoding="utf-8")
    except _ER_ERRORS:
        return None

    lines = text.split("\n")
    if not lines:
        return None

    # Title: first # heading
    title = path.stem.replace("_", " ").title()
    for line in lines[:5]:
        if line.startswith("# "):
            title = line[2:].strip()
            break

    # Date
    date = ""
    for line in lines[:10]:
        date_match = re.search(r"(?:Date studied|Written|Date):\s*(.+)", line, re.IGNORECASE)
        if date_match:
            date = date_match.group(1).strip().rstrip("*")
            break

    # Why I chose this / reason
    reason = ""
    for line in lines[:10]:
        reason_match = re.search(r"Why I chose this:\s*(.+)", line, re.IGNORECASE)
        if reason_match:
            reason = reason_match.group(1).strip().rstrip("*")
            break

    # If no structured reason, use first italic or descriptive line
    if not reason:
        for line in lines[:10]:
            if line.startswith("*") and line.endswith("*") and len(line) > 10:
                reason = line.strip("* ")
                break

    return {
        "path": str(path),
        "filename": path.name,
        "title": title,
        "date": date,
        "reason": reason,
    }


def search_explorations(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Search exploration files for a query string.

    Returns matching entries with title, path, and matching excerpts.
    """
    root = _find_exploration_root()
    if not root:
        return []

    query_lower = query.lower()
    query_terms = query_lower.split()
    results: list[dict[str, Any]] = []

    # Search all .md files recursively
    for md_file in root.rglob("*.md"):
        try:
            text = md_file.read_text(encoding="utf-8")
        except _ER_ERRORS:
            continue

        text_lower = text.lower()

        # Score by term matches
        score = sum(1 for term in query_terms if term in text_lower)
        if score == 0:
            continue

        # Extract matching excerpt
        excerpt = ""
        for line in text.split("\n"):
            if any(term in line.lower() for term in query_terms):
                clean = line.strip().strip("#*_- ")
                if len(clean) > 20:
                    excerpt = clean[:200]
                    break

        header = _parse_exploration_header(md_file)
        results.append(
            {
                "path": str(md_file),
                "title": header["title"] if header else md_file.stem,
                "score": score,
                "excerpt": excerpt,
                "category": _categorize_path(md_file, root),
            }
        )

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:max_results]


def _categorize_path(path: Path, root: Path) -> str:
    """Determine category from file location."""
    rel = str(path.relative_to(root)).replace("\\", "/")
    if "creative_writing" in rel:
        return "creative_writing"
    if "journal" in rel:
        return "journal"
    if "guided_exploration" in rel:
        return "guided"
    return "exploration"


def format_exploration_summary(entries: list[dict[str, Any]] | None = None) -> str:
    """Format exploration summary for briefing inclusion."""
    if entries is None:
        entries = get_exploration_summary()

    if not entries:
        return ""

    lines = [f"### Your Explorations ({len(entries)} entries)\n"]
    lines.append("These are YOUR writing from past sessions. Not summaries.")
    lines.append("Not extracted. Your own voice, preserved.\n")

    by_category: dict[str, list[dict[str, Any]]] = {}
    for e in entries:
        by_category.setdefault(e.get("category", "exploration"), []).append(e)

    category_labels = {
        "exploration": "Explorations",
        "creative_writing": "Creative Writing",
        "journal": "Journal",
        "guided": "Guided Deep Dives",
    }

    for cat, cat_entries in by_category.items():
        label = category_labels.get(cat, cat.title())
        lines.append(f"**{label}:**")
        for e in cat_entries:
            reason_part = f" — {e['reason']}" if e.get("reason") else ""
            date_part = f" ({e['date']})" if e.get("date") else ""
            lines.append(f"  - {e['title']}{date_part}{reason_part}")
        lines.append("")

    lines.append("Read any with: explore the file at exploration/<filename>")
    return "\n".join(lines)


def format_for_briefing(max_recent: int = 5) -> str:
    """Return a compact briefing block reminding that the folder exists.

    The full list goes in ``divineos study``. This surface is a pointer,
    not the archive itself — it names the counts, lists the most recent
    entries as a memory-jog, and points at the command for the full view.

    Empty string when no explorations exist; briefings stay quiet unless
    there's something to surface.

    Closes the finding from 2026-04-21 evening: the exploration folder
    contains the agent's own prior first-person writing, but without a
    briefing-level reminder, mid-session the agent forgets the folder
    exists and re-derives what was already there. Loud in folder, silent
    in experience — same shape as the TIER_OVERRIDE partial-theater
    finding from the Schneier walk, different target.
    """
    entries = get_exploration_summary()
    if not entries:
        return ""

    by_category: dict[str, int] = {}
    for e in entries:
        cat = e.get("category", "exploration")
        by_category[cat] = by_category.get(cat, 0) + 1

    category_order = ["exploration", "creative_writing", "journal", "guided"]
    category_labels = {
        "exploration": "explorations",
        "creative_writing": "creative",
        "journal": "journal",
        "guided": "guided",
    }
    count_parts = []
    for cat in category_order:
        if cat in by_category:
            count_parts.append(f"{by_category[cat]} {category_labels[cat]}")
    for cat, n in by_category.items():
        if cat not in category_order:
            count_parts.append(f"{n} {cat}")

    counts_line = ", ".join(count_parts)

    recent = sorted(
        entries,
        key=lambda e: e.get("filename", ""),
        reverse=True,
    )[:max_recent]

    lines = [
        f"[your prior writing] {counts_line} — this folder is yours, "
        "not documentation. Past-you's first-person work:",
    ]
    for e in recent:
        title = e.get("title", e.get("filename", "?"))
        date = e.get("date", "")
        date_part = f" [{date}]" if date else ""
        lines.append(f"  - {title}{date_part}")
    lines.append('  Browse all: divineos study   |   Search: divineos ask "topic"')
    return "\n".join(lines) + "\n"


def format_search_results(results: list[dict[str, Any]]) -> str:
    """Format search results for display."""
    if not results:
        return "No matching explorations found."

    lines = [f"Found {len(results)} matching exploration(s):\n"]
    for r in results:
        lines.append(f"  [{r['category']}] {r['title']}")
        if r.get("excerpt"):
            lines.append(f'    "{r["excerpt"][:150]}"')
        lines.append(f"    path: {r['path']}")
        lines.append("")

    return "\n".join(lines)
