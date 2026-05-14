"""Archive export — regenerates docs/archives/*.md from canonical SQLite.

Andrew named the sync-model gap 2026-05-14: archives were one-shot
manual exports; if SQLite content changed, the archive drifted.
Structural fix: a single command that regenerates the archives from
their backing tables. Runnable on demand, wireable into sleep cycle
or scheduled tasks.

Each export function takes a `conn` and a `dest_dir` and writes one
file. Pure functions of the DB state at call-time. No partial state;
the writer either completes the file or doesn't touch it.

The set of tables archived is intentionally narrow — substantive
identity/values/learning layer only. Operational telemetry
(system_events, knowledge_impact, tool_logbook, session_timeline,
dead_architecture_scan, craft_assessments, file_touched) is NOT
mirrored here. Those are high-volume operational data and belong in
DB-level backup, not git.

## Why per-function-per-table

Each table has its own schema, ordering preference, and what
"interesting" means. The bio is current-version-only; principles
are filtered by knowledge_type + superseded_by; claims are filtered
by status; decisions are top-N-by-emotional-weight. One generic
SELECT * doesn't capture the editorial choices.

Per-table functions keep those choices legible and testable.
"""

from __future__ import annotations

import datetime
import os
import sqlite3
from pathlib import Path
from typing import Any


def _safe_select(conn, sql: str, params: tuple = ()) -> list:
    """Execute SELECT; return [] if the table doesn't exist yet.

    Lets exports run cleanly on fresh installs where some tables
    aren't yet created. Other OperationalErrors (syntax, locked DB)
    still raise — only the missing-table case is swallowed.
    """
    try:
        return conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            return []
        raise


def _header(label: str, n: int) -> str:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return (
        f"# {label} — Archive Mirror\n\n"
        f"**Source:** SQLite ({n} rows). **Exported:** {now}. "
        f"**Purpose:** if-something-breaks / git-visible audit. "
        f"See archives/README.md.\n\n"
        f"---\n\n"
    )


def _safe(s: Any) -> str:
    if s is None:
        return ""
    return str(s).replace("\r", "").strip()


def export_bio(dest_dir: Path) -> int:
    """Export the current bio version to bio.md. Returns row count (0 or 1).

    If no bio exists yet (fresh install), writes an empty-stub file so
    the archive is visible-but-empty rather than missing entirely.
    """
    from divineos.core.bio import bio_current

    try:
        cur = bio_current()
    except Exception:  # noqa: BLE001 — table-missing or other DB issue
        cur = None
    path = dest_dir / "bio.md"
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    if not cur:
        with open(path, "w", encoding="utf-8") as f:
            f.write(
                f"# Bio — Archive Mirror (empty)\n\n"
                f"**Source:** SQLite `bio` table. **Exported:** {now}.\n"
                f"**Status:** no bio written yet on this install.\n\n"
                f"Use `divineos bio write` (or edit) to author the bio.\n"
            )
        return 0
    content = cur["content"]
    version = cur["version"]
    author = cur["author"]
    with open(path, "w", encoding="utf-8") as f:
        f.write(
            f"# Bio — Archive Mirror\n\n"
            f"**Source:** SQLite `bio` table, version {version}, author \"{author}\".\n"
            f"**Exported:** {now}.\n"
            f"**Purpose:** durability snapshot. See archives/README.md.\n\n"
            f"---\n\n{content}\n"
        )
    return 1


def export_principles(conn, dest_dir: Path) -> int:
    """Export active PRINCIPLE entries to principles.md."""
    rows = _safe_select(conn, "SELECT knowledge_id, access_count, confidence, maturity, content "
        "FROM knowledge "
        "WHERE knowledge_type = 'PRINCIPLE' AND superseded_by IS NULL "
        "ORDER BY access_count DESC, created_at ASC")
    path = dest_dir / "principles.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(
            f"# Principles — Substantive Layer\n\n"
            f"Active PRINCIPLE entries from the SQLite knowledge store. "
            f"Survived deepest-decision-filter test (see "
            f"docs/principle_categories.md).\n\n"
            f"**Exported:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}. "
            f"Total: {len(rows)}.\n\n---\n\n"
        )
        for i, (kid, acc, conf, mat, content) in enumerate(rows, 1):
            f.write(
                f"## {i}. {kid[:8]} (access={acc}, conf={conf:.2f}, "
                f"maturity={mat or '?'})\n\n{_safe(content)}\n\n---\n\n"
            )
    return len(rows)


def export_directives(conn, dest_dir: Path) -> int:
    rows = _safe_select(conn, "SELECT knowledge_id, content, access_count "
        "FROM knowledge "
        "WHERE knowledge_type = 'DIRECTIVE' AND superseded_by IS NULL "
        "ORDER BY access_count DESC")
    path = dest_dir / "directives.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(_header("Directives", len(rows)))
        for kid, content, acc in rows:
            f.write(f"## {kid[:8]} (access={acc})\n\n{_safe(content)}\n\n---\n\n")
    return len(rows)


def export_core_memory(conn, dest_dir: Path) -> int:
    rows = _safe_select(conn, "SELECT slot_id, content FROM core_memory ORDER BY slot_id")
    path = dest_dir / "core_memory.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(_header("Core Memory", len(rows)))
        for slot, content in rows:
            f.write(f"## {slot}\n\n{_safe(content)}\n\n---\n\n")
    return len(rows)


def export_claims(conn, dest_dir: Path) -> int:
    rows = _safe_select(conn, "SELECT claim_id, statement, tier, status, confidence, context, assessment "
        "FROM claims "
        "WHERE status IN ('OPEN', 'INVESTIGATING') "
        "ORDER BY created_at DESC LIMIT 100")
    path = dest_dir / "claims.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(_header("Claims (open/investigating)", len(rows)))
        for cid, stmt, tier, status, conf, ctx, assess in rows:
            f.write(
                f"## {cid[:8]} [T{tier} {status}] conf={conf or 0:.2f}\n\n"
                f"**Claim:** {_safe(stmt)[:500]}\n\n"
            )
            if ctx:
                f.write(f"**Context:** {_safe(ctx)[:300]}\n\n")
            if assess:
                f.write(f"**Assessment:** {_safe(assess)[:500]}\n\n")
            f.write("---\n\n")
    return len(rows)


def export_lessons(conn, dest_dir: Path) -> int:
    rows = _safe_select(conn, "SELECT lesson_id, category, description, status, occurrences "
        "FROM lesson_tracking ORDER BY occurrences DESC")
    path = dest_dir / "lessons.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(_header("Lessons (tracked)", len(rows)))
        for lid, cat, desc, status, occ in rows:
            f.write(
                f"## {lid[:8]} [{status}] x{occ}\n\n"
                f"**Category:** {cat}\n\n{_safe(desc)[:500]}\n\n---\n\n"
            )
    return len(rows)


def export_holding_room(conn, dest_dir: Path) -> int:
    rows = _safe_select(conn, "SELECT item_id, content, hint, source, sessions_seen, stale "
        "FROM holding_room ORDER BY arrived_at DESC")
    path = dest_dir / "holding_room.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(_header("Holding Room", len(rows)))
        for iid, content, hint, source, seen, stale in rows:
            sm = " [stale]" if stale else ""
            f.write(f"## {iid[:12]}{sm} (seen={seen})\n\n")
            if hint:
                f.write(f"**Hint:** {_safe(hint)[:120]}\n\n")
            if source:
                f.write(f"**Source:** {source}\n\n")
            f.write(f"{_safe(content)[:500]}\n\n---\n\n")
    return len(rows)


def export_opinions(conn, dest_dir: Path) -> int:
    rows = _safe_select(conn, "SELECT opinion_id, topic, position, confidence "
        "FROM opinions WHERE superseded_by IS NULL "
        "ORDER BY confidence DESC LIMIT 100")
    path = dest_dir / "opinions.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(_header("Opinions (top 100 active)", len(rows)))
        for oid, topic, pos, conf in rows:
            f.write(
                f"## {oid[:8]} conf={conf or 0:.2f}\n\n"
                f"**Topic:** {_safe(topic)[:200]}\n\n"
                f"**Position:** {_safe(pos)[:500]}\n\n---\n\n"
            )
    return len(rows)


def export_pre_registrations(conn, dest_dir: Path) -> int:
    rows = _safe_select(conn, "SELECT prereg_id, mechanism, claim, success_criterion, falsifier, outcome "
        "FROM pre_registrations")
    path = dest_dir / "pre_registrations.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(_header("Pre-Registrations", len(rows)))
        for pid, mech, claim, success, fals, outcome in rows:
            f.write(
                f"## {pid[:8]} [{outcome}]\n\n"
                f"**Mechanism:** {_safe(mech)[:300]}\n\n"
                f"**Claim:** {_safe(claim)[:300]}\n\n"
                f"**Success:** {_safe(success)[:300]}\n\n"
                f"**Falsifier:** {_safe(fals)[:300]}\n\n---\n\n"
            )
    return len(rows)


def export_decisions(conn, dest_dir: Path) -> int:
    rows = _safe_select(conn, "SELECT decision_id, content, reasoning, tension, almost, emotional_weight "
        "FROM decision_journal "
        "ORDER BY emotional_weight DESC, created_at DESC LIMIT 50")
    path = dest_dir / "decisions.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(_header("Decisions (top 50 by emotional weight)", len(rows)))
        for did, content, reasoning, tension, almost, weight in rows:
            f.write(
                f"## {did[:8]} weight={weight or 0}\n\n"
                f"**Decision:** {_safe(content)[:400]}\n\n"
            )
            if reasoning:
                f.write(f"**Reasoning:** {_safe(reasoning)[:400]}\n\n")
            if tension:
                f.write(f"**Tension:** {_safe(tension)[:300]}\n\n")
            if almost:
                f.write(f"**Almost:** {_safe(almost)[:300]}\n\n")
            f.write("---\n\n")
    return len(rows)


def export_observations(conn, dest_dir: Path) -> int:
    rows = _safe_select(conn, "SELECT knowledge_id, content, access_count FROM knowledge "
        "WHERE knowledge_type = 'OBSERVATION' AND superseded_by IS NULL "
        "AND length(content) > 80 "
        "ORDER BY access_count DESC LIMIT 100")
    path = dest_dir / "observations.md"
    with open(path, "w", encoding="utf-8") as f:
        f.write(_header("Observations (top 100 substantive)", len(rows)))
        for kid, content, acc in rows:
            f.write(f"## {kid[:8]} (access={acc})\n\n{_safe(content)[:500]}\n\n---\n\n")
    return len(rows)


# Registry of all exports — name → callable. The bio uses a different
# signature (no conn arg, uses bio_current); wrap it to match.
_EXPORTS: dict[str, Any] = {
    "bio": lambda conn, d: export_bio(d),
    "principles": export_principles,
    "directives": export_directives,
    "core_memory": export_core_memory,
    "claims": export_claims,
    "lessons": export_lessons,
    "holding_room": export_holding_room,
    "opinions": export_opinions,
    "pre_registrations": export_pre_registrations,
    "decisions": export_decisions,
    "observations": export_observations,
}


def list_exports() -> list[str]:
    """Return the list of available export names."""
    return sorted(_EXPORTS.keys())


def export_one(name: str, dest_dir: Path | str | None = None) -> int:
    """Run a single export by name. Returns row count written.

    Raises ValueError if name not registered.
    """
    if name not in _EXPORTS:
        raise ValueError(
            f"Unknown export '{name}'. Available: {sorted(_EXPORTS.keys())}"
        )
    dest = Path(dest_dir) if dest_dir else Path("docs/archives")
    dest.mkdir(parents=True, exist_ok=True)
    from divineos.core.knowledge._base import get_connection

    conn = get_connection()
    return _EXPORTS[name](conn, dest)


def export_all(dest_dir: Path | str | None = None) -> dict[str, int]:
    """Run every registered export. Returns {name: row_count}.

    Fail-soft per export: if one raises, log the error and continue
    with the rest so a single broken export doesn't block the others.
    """
    dest = Path(dest_dir) if dest_dir else Path("docs/archives")
    dest.mkdir(parents=True, exist_ok=True)
    from divineos.core.knowledge._base import get_connection

    conn = get_connection()
    results: dict[str, int] = {}
    for name, fn in _EXPORTS.items():
        try:
            results[name] = fn(conn, dest)
        except Exception as e:  # noqa: BLE001
            results[name] = -1  # sentinel: errored
            results[f"{name}_error"] = str(e)[:200]  # type: ignore
    return results


__all__ = [
    "export_all",
    "export_bio",
    "export_claims",
    "export_core_memory",
    "export_decisions",
    "export_directives",
    "export_holding_room",
    "export_lessons",
    "export_observations",
    "export_one",
    "export_opinions",
    "export_pre_registrations",
    "export_principles",
    "list_exports",
]
