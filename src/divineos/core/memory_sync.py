"""Memory Sync — auto-updates Claude Code memory files from DivineOS state.

Two memory systems work in tandem, like human memory:
- Auto memories: recorded by the OS (project state, stats, recent lessons).
  These form whether you want them to or not — involuntary encoding.
- Manual memories: curated by user request (preferences, philosophy, relationship).
  These are deliberate choices about what to remember.

Auto memories are editable after recording. Record first, curate after.
Nothing is permanent that doesn't need to be. But you can't filter before
recording — that's suppression, not memory.

This module writes auto-memory files to the Claude Code memory directory.
It runs during extraction (formerly SESSION_END) to keep cross-session context accurate.
"""

import os
import sqlite3
from pathlib import Path
from typing import Any

from loguru import logger

from divineos.core.claim_store import count_claims
from divineos.core.decision_journal import count_decisions, get_paradigm_shifts
from divineos.core.growth import compute_growth_map
from divineos.core.knowledge import get_connection, get_lessons


def get_memory_dir() -> Path | None:
    """Find the Claude Code project memory directory.

    Walks up from the project root looking for .claude/projects/*/memory/.
    Returns None if not found.
    """
    # The memory dir lives at ~/.claude/projects/<project-slug>/memory/
    home = Path.home()
    claude_projects = home / ".claude" / "projects"
    if not claude_projects.exists():
        return None

    # Find the project directory matching "DivineOS" or "DIVINE-OS"
    for project_dir in claude_projects.iterdir():
        if not project_dir.is_dir():
            continue
        if "DIVINE" in project_dir.name.upper() or "divineos" in project_dir.name.lower():
            memory_dir = project_dir / "memory"
            if memory_dir.exists():
                return memory_dir
    return None


def sync_auto_memories(analysis: Any | None = None) -> dict[str, bool]:
    """Write auto-memory files from current DivineOS state.

    Returns {filename: True if updated, False if unchanged}.
    """
    memory_dir = get_memory_dir()
    if not memory_dir:
        logger.debug("Claude Code memory directory not found, skipping auto-sync")
        return {}

    results: dict[str, bool] = {}
    results["auto_project_state.md"] = _sync_project_state(memory_dir)
    results["auto_recent_lessons.md"] = _sync_recent_lessons(memory_dir)

    # Update MEMORY.md index if any auto files were created or changed
    if any(results.values()):
        _update_memory_index(memory_dir, results)

    updated = [f for f, changed in results.items() if changed]
    if updated:
        logger.debug(f"Auto-memories synced: {', '.join(updated)}")
    return results


def _sync_project_state(memory_dir: Path) -> bool:
    """Write current project stats to auto_project_state.md."""
    parts: list[str] = []

    # Test count
    try:
        import subprocess

        result = subprocess.run(
            ["python", "-m", "pytest", "tests/", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=_find_project_root(),
        )
        for line in result.stdout.splitlines():
            if "test" in line and "selected" in line:
                parts.append(f"Tests: {line.strip()}")
                break
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    # Knowledge store stats
    try:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM knowledge WHERE superseded_by IS NULL"
            ).fetchone()
            total = row[0] if row else 0

            # Count by maturity
            maturity_rows = conn.execute(
                "SELECT maturity, COUNT(*) FROM knowledge "
                "WHERE superseded_by IS NULL GROUP BY maturity"
            ).fetchall()
            maturity = {r[0]: r[1] for r in maturity_rows}

            # Count by type
            type_rows = conn.execute(
                "SELECT knowledge_type, COUNT(*) FROM knowledge "
                "WHERE superseded_by IS NULL GROUP BY knowledge_type "
                "ORDER BY COUNT(*) DESC LIMIT 5"
            ).fetchall()
            top_types = [f"{r[1]} {r[0]}" for r in type_rows]
        finally:
            conn.close()

        parts.append(f"Knowledge store: {total} active entries")
        if maturity:
            mat_parts = [f"{v} {k}" for k, v in sorted(maturity.items())]
            parts.append(f"Maturity: {', '.join(mat_parts)}")
        if top_types:
            parts.append(f"Top types: {', '.join(top_types)}")
    except (ImportError, sqlite3.OperationalError):
        pass

    # Active lessons
    try:
        active = get_lessons(status="active")
        improving = get_lessons(status="improving")
        resolved = get_lessons(status="resolved")
        if active or improving or resolved:
            parts.append(
                f"Lessons: {len(active)} active, {len(improving)} improving, "
                f"{len(resolved)} resolved"
            )
    except (ImportError, sqlite3.OperationalError):
        pass

    # Growth trend
    try:
        growth = compute_growth_map(limit=10)
        if growth["sessions"] >= 2:
            parts.append(
                f"Growth: {growth['trend']} over {growth['sessions']} sessions "
                f"(avg score {growth['avg_health_score']:.2f})"
            )
    except (ImportError, sqlite3.OperationalError):
        pass

    # Claims count
    try:
        counts = count_claims()
        if counts["total"] > 0:
            parts.append(f"Claims: {counts['total']} filed")
    except (ImportError, sqlite3.OperationalError):
        pass

    # Decisions count
    try:
        total_decisions = count_decisions()
        shifts = get_paradigm_shifts(limit=10)
        if total_decisions > 0:
            parts.append(f"Decisions: {total_decisions} recorded, {len(shifts)} paradigm shifts")
    except (ImportError, sqlite3.OperationalError):
        pass

    if not parts:
        return False

    content = f"""---
name: Auto-synced project state
description: Current DivineOS stats and health — auto-updated at SESSION_END, editable for curation
type: project
---

{chr(10).join("- " + p for p in parts)}

*Auto-recorded by DivineOS at SESSION_END. Editable after recording — nothing is permanent that doesn't need to be.*
"""

    return _write_if_changed(memory_dir / "auto_project_state.md", content)


def _sync_recent_lessons(memory_dir: Path) -> bool:
    """Write active and improving lessons to auto_recent_lessons.md."""
    parts: list[str] = []

    try:
        active = get_lessons(status="active")
        improving = get_lessons(status="improving")

        if active:
            parts.append("**Active (still working on):**")
            for lesson in active[:5]:
                desc = lesson.get("description", "")[:120]
                count = lesson.get("occurrences", 1)
                parts.append(f"- ({count}x) {desc}")

        if improving:
            parts.append("")
            parts.append("**Improving (getting better at):**")
            for lesson in improving[:5]:
                desc = lesson.get("description", "")[:120]
                count = lesson.get("occurrences", 1)
                parts.append(f"- ({count}x) {desc}")
    except (ImportError, sqlite3.OperationalError):
        return False

    if not parts:
        return False

    content = f"""---
name: Auto-synced active lessons
description: Current active and improving lessons from DivineOS — auto-updated at SESSION_END
type: project
---

{chr(10).join(parts)}

*Auto-recorded by DivineOS at SESSION_END. Editable after recording — nothing is permanent that doesn't need to be.*
"""

    return _write_if_changed(memory_dir / "auto_recent_lessons.md", content)


def _update_memory_index(memory_dir: Path, results: dict[str, bool]) -> None:
    """Ensure auto-memory files are listed in MEMORY.md."""
    index_path = memory_dir / "MEMORY.md"
    if not index_path.exists():
        return

    current = index_path.read_text(encoding="utf-8")
    lines = current.strip().split("\n")
    changed = False

    auto_entries = {
        "auto_project_state.md": "- [auto_project_state.md](auto_project_state.md) — Auto-synced: project stats, knowledge, growth",
        "auto_recent_lessons.md": "- [auto_recent_lessons.md](auto_recent_lessons.md) — Auto-synced: active and improving lessons",
    }

    for filename, entry_line in auto_entries.items():
        if filename in results:
            # Check if any existing line already links to this file
            already_listed = any(f"[{filename}]" in line for line in lines)
            if not already_listed:
                lines.append(entry_line)
                changed = True

    if changed:
        index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_if_changed(path: Path, content: str) -> bool:
    """Write file only if content differs. Returns True if written."""
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing.strip() == content.strip():
            return False
    path.write_text(content, encoding="utf-8")
    return True


def _find_project_root() -> str:
    """Find the DivineOS project root directory."""
    # Try git root first
    try:
        import subprocess

        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, OSError):
        pass
    return os.getcwd()
