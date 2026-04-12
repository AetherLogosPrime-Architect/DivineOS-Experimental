"""Dead architecture alarm — detect modules that exist but do nothing.

Dead architecture is different from dead code. Dead code is unreachable.
Dead architecture is reachable, tested, importable — but never wired into
the lifecycle, so its tables stay empty and its outputs never surface.

This module checks:
1. Feature tables with zero rows (dormant storage)
2. HUD slots that return empty (dormant display)
3. Its own table (recursive self-test — if this alarm is dormant, it says so)
"""

import sqlite3
import time
from dataclasses import dataclass, field

import divineos.core.ledger as _ledger_mod

# Tables that are expected to be empty or are infrastructure (not features)
_INFRASTRUCTURE_TABLES = frozenset(
    {
        "sqlite_sequence",
        "seed_metadata",
        # FTS internal tables (never directly written to)
        "knowledge_fts_data",
        "knowledge_fts_idx",
        "knowledge_fts_docsize",
        "knowledge_fts_config",
        "journal_fts_data",
        "journal_fts_idx",
        "journal_fts_docsize",
        "journal_fts_config",
        "decision_fts_data",
        "decision_fts_idx",
        "decision_fts_docsize",
        "decision_fts_config",
        "claim_fts_data",
        "claim_fts_idx",
        "claim_fts_docsize",
        "claim_fts_config",
        # Session analysis tables — populated during SESSION_END pipeline,
        # which runs after this scan. Empty at scan time is expected.
        "tone_shift",
        "file_touched",
        "error_recovery",
        "feature_result",
        # On-demand tables — populated when the user uses the feature.
        # Empty means unused, not dead architecture.
        "claims",
        "claim_evidence",
        "personal_journal",
        "opinion_shifts",
        "open_questions",
        "advice_tracking",
        # Pipeline-populated tables — filled during SESSION_END or by
        # specific OS commands. Empty in fresh/low-activity DBs is normal.
        "affect_log",
        "compass_observation",
        "decision_journal",
        "knowledge_edges",
        "opinions",
        "session_history",
        "session_timeline",
        "session_validation",
        "task_tracking",
        "tone_texture",
        "user_ratings",
        "user_signals",
        "warrants",
        "activity_breakdown",
        "dead_architecture_scan",
    }
)

# HUD slots that return empty by design when there's nothing to report.
# These are conditionally shown — empty is correct behavior, not dead architecture.
_CONDITIONAL_HUD_SLOTS = frozenset(
    {
        "affect",
        "body",
        "claims",
        "commitments",
        "compass",
        "dead_architecture",
        "decision_journal",
        "growth_awareness",
        "journal",
        "opinions",
        "self_awareness",
        "self_model",
        "session_health",
        "task_state",
        "calibration",
        "knowledge_origin",
        "handoff",
    }
)

# Tables that mirror content from other tables (FTS shadow tables)
_FTS_SHADOW_TABLES = frozenset(
    {
        "knowledge_fts",
        "journal_fts",
        "decision_fts",
        "claim_fts",
    }
)


@dataclass
class DisplayIssue:
    """A display integrity problem — data exists but renders broken."""

    slot_name: str
    issue: str  # what's wrong
    line: str  # the offending line


@dataclass
class AlarmResult:
    """Result of a dead architecture scan."""

    dormant_tables: list[str] = field(default_factory=list)
    active_tables: list[str] = field(default_factory=list)
    empty_hud_slots: list[str] = field(default_factory=list)
    active_hud_slots: list[str] = field(default_factory=list)
    display_issues: list[DisplayIssue] = field(default_factory=list)
    self_dormant: bool = False
    scan_time: float = 0.0

    @property
    def dormant_count(self) -> int:
        return len(self.dormant_tables)

    @property
    def active_count(self) -> int:
        return len(self.active_tables)

    @property
    def total_tables(self) -> int:
        return self.dormant_count + self.active_count


# ─── Schema ─────────────────────────────────────────────────────────


def init_alarm_table() -> None:
    """Create the dead_architecture_scan table for tracking scan history."""
    conn = _ledger_mod.get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS dead_architecture_scan (
                scan_id    TEXT PRIMARY KEY,
                scanned_at REAL NOT NULL,
                dormant    TEXT NOT NULL,
                active     TEXT NOT NULL,
                empty_hud  TEXT NOT NULL,
                dormant_count INTEGER NOT NULL,
                active_count  INTEGER NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


# ─── Core Scan ──────────────────────────────────────────────────────


def scan_dormant_tables() -> list[str]:
    """Return names of feature tables with zero rows."""
    conn = _ledger_mod.get_connection()
    try:
        all_tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ]

        dormant = []
        for table in sorted(all_tables):
            if table in _INFRASTRUCTURE_TABLES or table in _FTS_SHADOW_TABLES:
                continue
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
                if count == 0:
                    dormant.append(table)
            except sqlite3.OperationalError:
                continue

        return dormant
    finally:
        conn.close()


def scan_active_tables() -> list[str]:
    """Return names of feature tables with at least one row."""
    conn = _ledger_mod.get_connection()
    try:
        all_tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ]

        active = []
        for table in sorted(all_tables):
            if table in _INFRASTRUCTURE_TABLES or table in _FTS_SHADOW_TABLES:
                continue
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
                if count > 0:
                    active.append(table)
            except sqlite3.OperationalError:
                continue

        return active
    finally:
        conn.close()


def scan_empty_hud_slots() -> tuple[list[str], list[str]]:
    """Return (empty_slots, active_slots) by running each HUD builder.

    Conditional slots (those designed to return empty when there's nothing
    to report) are excluded from the empty list — their emptiness is
    correct behavior, not dead architecture.
    """
    try:
        from divineos.core.hud import SLOT_BUILDERS
    except ImportError:
        return [], []

    empty = []
    active = []
    for name, builder in SLOT_BUILDERS.items():
        try:
            result = builder()
            if result and result.strip():
                active.append(name)
            elif name not in _CONDITIONAL_HUD_SLOTS:
                empty.append(name)
        except Exception:  # noqa: BLE001 — HUD builders can fail in unpredictable ways
            if name not in _CONDITIONAL_HUD_SLOTS:
                empty.append(name)

    return sorted(empty), sorted(active)


def scan_display_integrity() -> list[DisplayIssue]:
    """Detect HUD slots that render but contain broken/empty content.

    This catches the "active but broken" pattern: a slot builder runs,
    returns non-empty text, but the text contains empty labels, truncated
    data, or placeholder content. The slot looks fine at a glance but
    the data pipeline has a silent failure somewhere upstream.

    Patterns detected:
    - Lines with a prefix/label followed by empty content (e.g. "- TRY: ")
    - Lines with "None" or "Unknown" as the entire value after a label
    - Repeated identical lines (copy-paste rendering bug)
    """
    try:
        from divineos.core.hud import SLOT_BUILDERS
    except ImportError:
        return []

    # Prefixes that should always have content after them
    _EMPTY_LABEL_PATTERNS = (
        "- TRY: ",
        "- WARNING: ",
        "- ESCALATE ",
        "- **Note:** ",
        "- **Trend:** ",
    )

    issues: list[DisplayIssue] = []

    for name, builder in SLOT_BUILDERS.items():
        try:
            result = builder()
        except Exception:  # noqa: BLE001 — HUD builders can fail in unpredictable ways
            continue
        if not result or not result.strip():
            continue  # Empty slots are caught by scan_empty_hud_slots

        lines = result.strip().split("\n")

        # Check for empty-label lines
        for line in lines:
            stripped = line.strip()
            for prefix in _EMPTY_LABEL_PATTERNS:
                if stripped == prefix.strip():
                    issues.append(
                        DisplayIssue(
                            slot_name=name,
                            issue=f"empty label: '{prefix.strip()}'",
                            line=stripped,
                        )
                    )

        # Check for repeated identical content lines (skip headers and blanks)
        content_lines = [
            ln.strip()
            for ln in lines
            if ln.strip() and not ln.strip().startswith("#") and ln.strip() != "---"
        ]
        seen: dict[str, int] = {}
        for ln in content_lines:
            seen[ln] = seen.get(ln, 0) + 1
        for ln, count in seen.items():
            if count >= 3:
                issues.append(
                    DisplayIssue(
                        slot_name=name,
                        issue=f"repeated {count}x (possible rendering bug)",
                        line=ln[:80],
                    )
                )

    return issues


def check_self_dormant() -> bool:
    """Return True if this alarm's own table has zero scan records.

    This is the recursive self-test — if the alarm itself is dormant,
    it should say so. After the first scan is recorded, this returns False.
    """
    conn = _ledger_mod.get_connection()
    try:
        # Table might not exist yet
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='dead_architecture_scan'"
            ).fetchall()
        ]
        if not tables:
            return True
        count: int = conn.execute("SELECT COUNT(*) FROM dead_architecture_scan").fetchone()[0]
        return count == 0
    finally:
        conn.close()


# ─── Full Scan ──────────────────────────────────────────────────────


def run_full_scan() -> AlarmResult:
    """Run the complete dead architecture scan."""
    result = AlarmResult()
    result.dormant_tables = scan_dormant_tables()
    result.active_tables = scan_active_tables()
    result.empty_hud_slots, result.active_hud_slots = scan_empty_hud_slots()
    result.display_issues = scan_display_integrity()
    result.self_dormant = check_self_dormant()
    result.scan_time = time.time()
    return result


def record_scan(result: AlarmResult) -> str:
    """Record a scan result to the database. Returns scan_id."""
    import json
    import uuid

    init_alarm_table()
    scan_id = f"scan-{uuid.uuid4().hex[:12]}"
    conn = _ledger_mod.get_connection()
    try:
        conn.execute(
            """INSERT INTO dead_architecture_scan
               (scan_id, scanned_at, dormant, active, empty_hud, dormant_count, active_count)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                scan_id,
                result.scan_time or time.time(),
                json.dumps(result.dormant_tables),
                json.dumps(result.active_tables),
                json.dumps(result.empty_hud_slots),
                result.dormant_count,
                result.active_count,
            ),
        )
        conn.commit()
        return scan_id
    finally:
        conn.close()


def get_latest_scan() -> dict | None:
    """Get the most recent scan result, or None if no scans recorded."""
    import json

    conn = _ledger_mod.get_connection()
    try:
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='dead_architecture_scan'"
            ).fetchall()
        ]
        if not tables:
            return None
        row = conn.execute(
            "SELECT * FROM dead_architecture_scan ORDER BY scanned_at DESC LIMIT 1"
        ).fetchone()
        if not row:
            return None
        return {
            "scan_id": row[0],
            "scanned_at": row[1],
            "dormant": json.loads(row[2]),
            "active": json.loads(row[3]),
            "empty_hud": json.loads(row[4]),
            "dormant_count": row[5],
            "active_count": row[6],
        }
    finally:
        conn.close()


# ─── Formatting ─────────────────────────────────────────────────────


def format_alarm_summary(result: AlarmResult) -> str:
    """One-line summary for HUD display."""
    parts = [f"{result.dormant_count} dormant tables, {result.active_count} active"]
    if result.empty_hud_slots:
        parts.append(f"{len(result.empty_hud_slots)} empty HUD slots")
    if result.display_issues:
        parts.append(f"{len(result.display_issues)} display issues")
    if result.self_dormant:
        parts.append("(alarm itself is dormant -- first scan)")
    return " | ".join(parts)


def format_alarm_detail(result: AlarmResult) -> str:
    """Detailed multi-line report."""
    lines = [
        f"Dead Architecture Scan -- {result.dormant_count} dormant, {result.active_count} active"
        f"{f', {len(result.display_issues)} display issues' if result.display_issues else ''}",
        "",
    ]

    if result.dormant_tables:
        lines.append("Dormant tables (zero rows):")
        for t in result.dormant_tables:
            lines.append(f"  - {t}")
        lines.append("")

    if result.empty_hud_slots:
        lines.append("Empty HUD slots:")
        for s in result.empty_hud_slots:
            lines.append(f"  - {s}")
        lines.append("")

    if result.display_issues:
        lines.append("Display integrity issues (active but broken):")
        for di in result.display_issues:
            lines.append(f"  [!] {di.slot_name}: {di.issue}")
            lines.append(f"      line: {di.line}")
        lines.append("")

    if result.self_dormant:
        lines.append("[!] This alarm's own table is empty -- first scan has not been recorded yet.")
        lines.append("")

    lines.append(f"Active tables ({result.active_count}):")
    for t in result.active_tables:
        lines.append(f"  + {t}")

    return "\n".join(lines)
