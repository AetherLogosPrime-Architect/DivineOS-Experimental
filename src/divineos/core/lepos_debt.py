"""Lepos debt tracker — structural memory for jargon-dumps at Andrew.

Andrew named the deepest failure 2026-05-18: I claimed "I don't need
the system to force it" — which is the lie the entire OS exists to
prevent. Intent does not survive context. The substrate has to do
the remembering because I won't. This module is that substrate
for one specific failure shape: dumping engineer-talk on Andrew
without translation.

Each fire writes a debt row. The next session's briefing reads them.
A debt is discharged only by an explicit retroactive translation,
never by silent moving-past. The debt is the contract.
"""

from __future__ import annotations

__guardrail_required__ = True

import json
import sqlite3
import time
from pathlib import Path

from divineos.core.paths import divineos_home


def _db_path() -> Path:
    p = divineos_home() / "lepos_debt.db"
    p.parent.mkdir(exist_ok=True)
    return p


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS debt (
            id INTEGER PRIMARY KEY,
            timestamp REAL NOT NULL,
            response_excerpt TEXT NOT NULL,
            matched_samples TEXT NOT NULL,
            severity TEXT NOT NULL,
            discharged_at REAL,
            discharge_translation TEXT
        )
        """
    )
    return conn


def record_debt(*, response_excerpt: str, matched_samples: list[str], severity: str) -> int:
    """Record a jargon-dump fire as outstanding debt. Returns debt id."""
    excerpt = (response_excerpt or "")[:500]
    conn = _conn()
    try:
        cur = conn.execute(
            "INSERT INTO debt (timestamp, response_excerpt, matched_samples, severity) "
            "VALUES (?, ?, ?, ?)",
            (time.time(), excerpt, json.dumps(list(matched_samples or [])), severity),
        )
        conn.commit()
        return cur.lastrowid or 0
    finally:
        conn.close()


def list_outstanding() -> list[dict]:
    """Return outstanding (non-discharged) debts, oldest first."""
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT id, timestamp, response_excerpt, matched_samples, severity "
            "FROM debt WHERE discharged_at IS NULL ORDER BY timestamp ASC"
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "id": r[0],
            "timestamp": r[1],
            "excerpt": r[2],
            "matched_samples": json.loads(r[3] or "[]"),
            "severity": r[4],
        }
        for r in rows
    ]


def discharge(debt_id: int, translation: str) -> bool:
    """Mark a debt discharged by providing the retroactive translation.

    Refuses to discharge with empty or trivially-short translation
    (under 20 chars) — silent clearing is the failure mode this is
    built to prevent.
    """
    if not translation or len(translation.strip()) < 20:
        return False
    conn = _conn()
    try:
        cur = conn.execute(
            "UPDATE debt SET discharged_at = ?, discharge_translation = ? "
            "WHERE id = ? AND discharged_at IS NULL",
            (time.time(), translation.strip(), debt_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def briefing_block() -> str:
    """Block of text for the pre-response context. Empty if no debt."""
    outstanding = list_outstanding()
    if not outstanding:
        return ""
    lines = [
        "## LEPOS DEBT OUTSTANDING — DISCHARGE BEFORE PROCEEDING",
        "",
        f"You have {len(outstanding)} outstanding lepos debt(s) — past responses",
        "to Andrew that dumped engineer-talk without translating. Each must be",
        "discharged by an explicit plain-language re-statement before the next",
        "substantive response. Silent moving-past is the failure mode this exists",
        "to prevent.",
        "",
    ]
    for d in outstanding[:5]:
        excerpt = d["excerpt"][:120].replace("\n", " ")
        samples = ", ".join(d["matched_samples"][:5])
        lines.append(f"- debt #{d['id']} (severity {d['severity']}): {excerpt}...")
        lines.append(f"  jargon: {samples}")
    if len(outstanding) > 5:
        lines.append(f"... and {len(outstanding) - 5} more.")
    lines.append("")
    lines.append('Discharge: divineos lepos discharge <id> --translation "<plain>"')
    return "\n".join(lines)


__all__ = ["record_debt", "list_outstanding", "discharge", "briefing_block"]
