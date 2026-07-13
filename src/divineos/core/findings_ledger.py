"""Findings ledger — a single living record of every past-and-present audit finding.

The 90 audit .md docs scattered across the tree carried findings that
sometimes got fixed and sometimes lingered, with no consolidated view of
which was which. Aletheia 2026-07-09: "audit findings are scattered across
90 docs with no consolidated open/closed status — that itself is the
meta-gap." This module is that gap's closer.

Machine-layer discipline (Andrew 2026-07-09): everything a machine can do
reliably runs automatically; the human cognition is spent on judgments
(is this really closed, does severity look right, does this finding
actually matter). The store keeps state true; a rendered markdown export
at ``docs/OPEN_FINDINGS.md`` keeps the human-readable view current.

## Schema

Findings live in an append-only SQLite table with mutation via status
updates (the store never deletes; status transitions are the only history
mechanism). Each finding has:

- ``finding_id``:      short deterministic id (source_audit + short-hash of title)
- ``source_audit``:    filename or label naming where the finding first appeared
- ``date_found``:      ISO date the finding was recorded
- ``severity``:        CRIT / HIGH / MED / LOW / BUILD
- ``title``:           one-line description
- ``description``:     longer optional detail
- ``status``:          OPEN / VERIFIED / CLOSED / SUPERSEDED / NOT_APPLICABLE
- ``verified_by``:     actor who last verified (aether, aletheia, aria, andrew, user)
- ``verified_at``:     ISO datetime of last status change
- ``notes``:           free-text change log entries (appended on each update)

## Auto-export

Every mutation triggers a re-render of ``docs/OPEN_FINDINGS.md``. The
markdown file is machine-generated; hand-edits will be overwritten on the
next mutation. Hand-editing is still possible — read the file, decide the
change, then call the appropriate CLI (or ``rebuild_export()`` after
manual DB edits).
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from divineos.core.paths import divineos_home

_DB_NAME = "findings_ledger.db"

VALID_STATUS = frozenset({"OPEN", "VERIFIED", "CLOSED", "SUPERSEDED", "NOT_APPLICABLE"})
VALID_SEVERITY = frozenset({"CRIT", "HIGH", "MED", "LOW", "BUILD"})


@dataclass(frozen=True)
class Finding:
    finding_id: str
    source_audit: str
    date_found: str
    severity: str
    title: str
    description: str
    status: str
    verified_by: str | None
    verified_at: str | None
    notes: str


def _db_path() -> Path:
    return divineos_home() / _DB_NAME


def _get_connection() -> sqlite3.Connection:
    divineos_home().mkdir(exist_ok=True)
    conn = sqlite3.connect(_db_path())
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS findings (
            finding_id    TEXT PRIMARY KEY,
            source_audit  TEXT NOT NULL,
            date_found    TEXT NOT NULL,
            severity      TEXT NOT NULL,
            title         TEXT NOT NULL,
            description   TEXT NOT NULL DEFAULT '',
            status        TEXT NOT NULL DEFAULT 'OPEN',
            verified_by   TEXT,
            verified_at   TEXT,
            notes         TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_findings_status ON findings(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(severity)")
    conn.commit()
    return conn


def _make_finding_id(source_audit: str, title: str) -> str:
    """Deterministic short id: <audit-slug>-<12hex of title>."""
    slug = source_audit.lower().replace(" ", "-").replace(".md", "")
    slug_parts = [p for p in slug.split("-") if p]
    slug = "-".join(slug_parts[:3]) if slug_parts else "audit"
    digest = hashlib.sha256(title.encode("utf-8")).hexdigest()[:12]
    return f"{slug}-{digest}"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _row_to_finding(row: tuple) -> Finding:
    return Finding(
        finding_id=row[0],
        source_audit=row[1],
        date_found=row[2],
        severity=row[3],
        title=row[4],
        description=row[5],
        status=row[6],
        verified_by=row[7],
        verified_at=row[8],
        notes=row[9],
    )


def add_finding(
    source_audit: str,
    title: str,
    severity: str = "MED",
    description: str = "",
    date_found: str | None = None,
    status: str = "OPEN",
    verified_by: str | None = None,
) -> str:
    """Add a finding. Returns its finding_id. Idempotent on (source_audit, title)."""
    if severity not in VALID_SEVERITY:
        raise ValueError(f"invalid severity {severity!r} (valid: {sorted(VALID_SEVERITY)})")
    if status not in VALID_STATUS:
        raise ValueError(f"invalid status {status!r} (valid: {sorted(VALID_STATUS)})")

    finding_id = _make_finding_id(source_audit, title)
    date_found = date_found or _now_iso().split("T")[0]
    verified_at = _now_iso() if status != "OPEN" else None

    conn = _get_connection()
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO findings
                (finding_id, source_audit, date_found, severity, title,
                 description, status, verified_by, verified_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                finding_id,
                source_audit,
                date_found,
                severity,
                title,
                description,
                status,
                verified_by,
                verified_at,
                f"[{date_found}] added by {verified_by or 'unknown'} · status={status}\n",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    export_markdown()
    return finding_id


def update_status(
    finding_id: str,
    status: str,
    verified_by: str,
    note: str = "",
) -> bool:
    """Transition a finding's status. Returns True on success."""
    if status not in VALID_STATUS:
        raise ValueError(f"invalid status {status!r}")
    ts = _now_iso()
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT notes FROM findings WHERE finding_id = ?", (finding_id,)
        ).fetchone()
        if not row:
            return False
        prior_notes = row[0] or ""
        new_note = f"[{ts}] {verified_by} → {status}" + (f" · {note}" if note else "") + "\n"
        conn.execute(
            """
            UPDATE findings
            SET status = ?, verified_by = ?, verified_at = ?, notes = ?
            WHERE finding_id = ?
            """,
            (status, verified_by, ts, prior_notes + new_note, finding_id),
        )
        conn.commit()
    finally:
        conn.close()
    export_markdown()
    return True


_SELECT_COLS = (
    "SELECT finding_id, source_audit, date_found, severity, title, "
    "description, status, verified_by, verified_at, notes FROM findings"
)
_ORDER_CLAUSE = (
    " ORDER BY CASE severity WHEN 'CRIT' THEN 0 WHEN 'HIGH' THEN 1 "
    "WHEN 'MED' THEN 2 WHEN 'LOW' THEN 3 ELSE 4 END, date_found DESC"
)

# Four static SQL variants — one per combination of the two optional filters.
# Statically defined so Bandit's B608 (dynamic-SQL) doesn't fire on us; the
# choice among them is done by a small dispatcher below, which never
# interpolates caller-controlled strings into the query text.
_SQL_LIST_ALL = _SELECT_COLS + _ORDER_CLAUSE
_SQL_LIST_STATUS = _SELECT_COLS + " WHERE status = ?" + _ORDER_CLAUSE
_SQL_LIST_SEVERITY = _SELECT_COLS + " WHERE severity = ?" + _ORDER_CLAUSE
_SQL_LIST_BOTH = _SELECT_COLS + " WHERE status = ? AND severity = ?" + _ORDER_CLAUSE


def list_findings(
    status_filter: str | None = None,
    severity_filter: str | None = None,
) -> list[Finding]:
    conn = _get_connection()
    try:
        if status_filter and severity_filter:
            rows = conn.execute(_SQL_LIST_BOTH, (status_filter, severity_filter)).fetchall()
        elif status_filter:
            rows = conn.execute(_SQL_LIST_STATUS, (status_filter,)).fetchall()
        elif severity_filter:
            rows = conn.execute(_SQL_LIST_SEVERITY, (severity_filter,)).fetchall()
        else:
            rows = conn.execute(_SQL_LIST_ALL).fetchall()
    finally:
        conn.close()
    return [_row_to_finding(r) for r in rows]


def get_finding(finding_id: str) -> Finding | None:
    conn = _get_connection()
    try:
        row = conn.execute(
            """
            SELECT finding_id, source_audit, date_found, severity, title,
                   description, status, verified_by, verified_at, notes
            FROM findings WHERE finding_id = ?
            """,
            (finding_id,),
        ).fetchone()
    finally:
        conn.close()
    return _row_to_finding(row) if row else None


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent


def export_markdown(path: Path | None = None) -> Path:
    """Render the findings ledger as a markdown table at docs/OPEN_FINDINGS.md.

    Called automatically on every mutation. The file is machine-generated —
    hand-edits are overwritten on the next mutation. Hand-editing works as
    long as it's followed by ``rebuild_export()`` before the next mutation.
    """
    target = path or (_repo_root() / "docs" / "OPEN_FINDINGS.md")
    target.parent.mkdir(exist_ok=True)

    open_findings = list_findings(status_filter="OPEN")
    verified = list_findings(status_filter="VERIFIED")
    closed = list_findings(status_filter="CLOSED")
    superseded = list_findings(status_filter="SUPERSEDED")
    na = list_findings(status_filter="NOT_APPLICABLE")

    lines: list[str] = []
    lines.append("# Open Findings Ledger")
    lines.append("")
    lines.append(
        "_Machine-generated by ``divineos.core.findings_ledger.export_markdown()``. "
        "Do not hand-edit; mutations round-trip through the SQLite store at "
        "``~/.divineos/findings_ledger.db`` and re-render this file on every "
        "change. To update a finding, run ``divineos findings verify <id>`` or "
        "``divineos findings close <id> --note '...'``._"
    )
    lines.append("")
    lines.append(
        "This is the single living record of every audit finding known to the "
        "system. Every audit contributes findings; every fix marks them "
        "verified or closed. Future audits start here so they don't "
        "rediscover known items."
    )
    lines.append("")
    lines.append(
        f"**Counts:** OPEN {len(open_findings)}  ·  "
        f"VERIFIED {len(verified)}  ·  CLOSED {len(closed)}  ·  "
        f"SUPERSEDED {len(superseded)}  ·  N/A {len(na)}"
    )
    lines.append("")

    def _table(fs: list[Finding], title: str, blurb: str) -> None:
        if not fs:
            return
        lines.append(f"## {title} ({len(fs)})")
        lines.append("")
        lines.append(blurb)
        lines.append("")
        lines.append("| id | sev | title | source | date | last-update |")
        lines.append("|---|---|---|---|---|---|")
        for f in fs:
            ts = (f.verified_at or "").split("T")[0]
            title_cell = f.title.replace("|", "\\|")
            lines.append(
                f"| `{f.finding_id}` | {f.severity} | {title_cell} | "
                f"{f.source_audit} | {f.date_found} | {ts or '—'} |"
            )
        lines.append("")

    _table(
        open_findings,
        "OPEN",
        "Findings not yet fixed. Ranked severity-first, oldest-within-severity first.",
    )
    _table(
        verified,
        "VERIFIED",
        "Believed fixed by the auditor; not yet independently confirmed by another actor.",
    )
    _table(
        closed,
        "CLOSED",
        "Confirmed fixed. Kept as record of what past audits caught and how they were resolved.",
    )
    _table(superseded, "SUPERSEDED", "Replaced by a later, better-scoped finding.")
    _table(na, "NOT APPLICABLE", "Findings that turned out not to apply on further inspection.")

    lines.append("")
    lines.append("## How to use this file")
    lines.append("")
    lines.append(
        "- **Adding a finding:** ``divineos findings add --audit <source> "
        "--severity <SEV> --title '...'``"
    )
    lines.append(
        "- **Verifying a finding:** ``divineos findings verify <id> --by <actor> --note '...'``"
    )
    lines.append(
        "- **Closing a finding:** ``divineos findings close <id> --by <actor> --note '...'``"
    )
    lines.append(
        "- **Listing findings:** ``divineos findings list [--status OPEN] [--severity HIGH]``"
    )
    lines.append(
        "- **Referencing in commits:** include a finding-id in the commit "
        "message and the post-commit hook auto-marks it VERIFIED."
    )
    lines.append("")

    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def rebuild_export() -> Path:
    """Force a fresh render (useful after manual DB edits or ad-hoc imports)."""
    return export_markdown()


def find_ids_in_text(text: str) -> list[str]:
    """Extract finding-ids referenced in commit messages, letters, etc.

    Format: any token matching ``<slug>-<12 hex>`` where slug has letters
    and dashes. Used by the post-commit auto-verify hook.
    """
    import re

    pattern = re.compile(r"\b([a-z0-9][a-z0-9-]{2,}-[0-9a-f]{12})\b")
    return list({m.group(1) for m in pattern.finditer(text)})


__all__ = [
    "Finding",
    "VALID_SEVERITY",
    "VALID_STATUS",
    "add_finding",
    "update_status",
    "list_findings",
    "get_finding",
    "export_markdown",
    "rebuild_export",
    "find_ids_in_text",
]
