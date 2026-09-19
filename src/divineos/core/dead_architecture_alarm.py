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
        # Legacy tables superseded by knowledge_edges (migration in edges.py).
        # Kept for rollback safety but intentionally empty.
        "knowledge_relationships",
        "logical_relations",
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


# Columns a store might carry its write-time in, ordered by how
# unambiguously they mean "when this row was written".
_TIME_COLUMNS = ("timestamp", "created_at", "scanned_at", "ts", "logged_at", "filed_at")

# Days of silence before a store that HOLDS DATA is called stale. A parameter
# somebody chose, not a fact about death — which is why the scan reports
# elapsed days beside it instead of hiding it inside a verdict.
STALE_AFTER_DAYS = 14


@dataclass
class StaleStore:
    """A store holding data that nothing has written to in a long while.

    THE DEATH THE EMPTINESS CHECK CANNOT SEE. `scan_dormant_tables` asks
    whether a table has zero rows, which catches a feature built and never
    used — a real catch, and kept. What it cannot see is the commoner death:
    a store that filled, worked, and then stopped being fed. Full-and-
    abandoned renders identically to full-and-thriving, so this alarm was
    most confident about the stores it understood least.

    Found 2026-09-19 the hard way. The wins ledger took 313 entries across
    two days in late August and had been silent for three weeks. Nothing
    noticed — it is a file rather than a table, and even as a table it would
    have read ACTIVE. I then shipped a health report whose denominator was
    that dead store, and called it repaired.

    Andrew, same day: "stop hiding from your failures.. get them out in the
    open where you can see them, only then can they ever be corrected."

    `days_quiet` is None when the store could not be dated at all. That is
    UNCHECKED, not fresh. A store I cannot date is not a store I have
    cleared, and collapsing those two is the exact fault this exists to end.
    """

    name: str
    rows: int
    days_quiet: float | None
    reason: str


@dataclass
class WiringIssue:
    """A wiring problem — component exists and tests pass but isn't connected in production."""

    component: str
    issue: str  # what's wrong
    detail: str  # how to fix it


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
    wiring_issues: list[WiringIssue] = field(default_factory=list)
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
                count = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]  # nosec B608: table/column names from module constants; values parameterized
                if count == 0:
                    dormant.append(table)
            except sqlite3.OperationalError:
                continue

        return dormant
    finally:
        conn.close()


def _newest_row_age_days(conn: sqlite3.Connection, table: str) -> tuple[float | None, str]:
    """Days since the newest row in `table`, or None with the reason why not.

    None is UNCHECKED and never fresh. A table carrying no recognisable
    time column is one this scan could not date, which is a different fact
    from one it dated and found current.
    """
    try:
        cols = {r[1].lower() for r in conn.execute(f"PRAGMA table_info([{table}])")}
    except sqlite3.OperationalError as e:
        return None, f"cannot read columns ({e})"

    col = next((c for c in _TIME_COLUMNS if c in cols), None)
    if col is None:
        return None, f"no recognisable time column (has: {', '.join(sorted(cols)) or 'none'})"

    try:
        newest = conn.execute(f"SELECT MAX([{col}]) FROM [{table}]").fetchone()[0]  # nosec B608: table/column names from sqlite_master and module constants
    except sqlite3.OperationalError as e:
        return None, f"cannot read {col} ({e})"

    if newest is None:
        return None, f"{col} is null on every row"

    try:
        newest_ts = float(newest)
    except (TypeError, ValueError):
        # Stored as an ISO string rather than an epoch.
        try:
            newest_ts = time.mktime(time.strptime(str(newest)[:19], "%Y-%m-%d %H:%M:%S"))
        except ValueError:
            return None, f"{col} holds an unparseable value ({str(newest)[:24]})"

    return (time.time() - newest_ts) / 86400.0, f"newest row via {col}"


def scan_stale_stores(stale_after_days: float = STALE_AFTER_DAYS) -> list[StaleStore]:
    """Stores that HOLD DATA and have not been written to in a long while.

    The half `scan_dormant_tables` structurally cannot see: it asks whether a
    store is empty, and a store that filled and then died is not empty. See
    `StaleStore` for the incident that produced this.

    Covers the file-backed stores too, because the one that actually died is
    a file — fixing the class while missing the instance would have been the
    same joke one level up.
    """
    out: list[StaleStore] = []
    conn = _ledger_mod.get_connection()
    try:
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ]
        for table in sorted(tables):
            if table in _INFRASTRUCTURE_TABLES or table in _FTS_SHADOW_TABLES:
                continue
            try:
                rows = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]  # nosec B608: name from sqlite_master
            except sqlite3.OperationalError:
                continue
            if rows == 0:
                continue  # empty is the OTHER check's business
            age, reason = _newest_row_age_days(conn, table)
            if age is None:
                out.append(StaleStore(table, rows, None, f"UNCHECKED — {reason}"))
            elif age > stale_after_days:
                out.append(
                    StaleStore(
                        table, rows, age, f"quiet {age:.0f}d (stale past {stale_after_days:.0f}d)"
                    )
                )
    finally:
        conn.close()

    out.extend(_scan_stale_files(stale_after_days))
    return out


def _scan_stale_files(stale_after_days: float) -> list[StaleStore]:
    """The file-backed stores — where the wins ledger died unseen."""
    out: list[StaleStore] = []
    loaders = (
        ("wins ledger", "divineos.core.success_ledger", "load_successes"),
        ("corrections", "divineos.core.corrections", "load_corrections"),
    )
    for name, module, fn in loaders:
        try:
            mod = __import__(module, fromlist=[fn])
            records = getattr(mod, fn)()
        except Exception as e:  # noqa: BLE001 - unreadable is not fresh
            out.append(StaleStore(name, 0, None, f"UNCHECKED — store unreadable ({e})"))
            continue
        if not records:
            continue  # empty is the other check's business
        stamps = []
        for r in records:
            for key in _TIME_COLUMNS:
                if key in r:
                    try:
                        stamps.append(float(r[key]))
                    except (TypeError, ValueError):
                        pass
                    break
        if not stamps:
            out.append(StaleStore(name, len(records), None, "UNCHECKED — no readable timestamps"))
            continue
        age = (time.time() - max(stamps)) / 86400.0
        if age > stale_after_days:
            out.append(
                StaleStore(
                    name,
                    len(records),
                    age,
                    f"quiet {age:.0f}d (stale past {stale_after_days:.0f}d)",
                )
            )
    return out


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
                count = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]  # nosec B608: table/column names from module constants; values parameterized
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


def scan_wiring() -> list[WiringIssue]:
    """Verify that key singletons and factories return populated objects.

    This catches the "constructed but not connected" pattern: a module
    exists, imports cleanly, passes all its own tests — but the production
    factory that creates it doesn't actually wire up its dependencies.

    Each check probes a real factory/singleton the way production code would
    use it. If the result is empty or missing expected content, it's a
    wiring issue.
    """
    issues: list[WiringIssue] = []

    # Council engine: should have experts registered
    try:
        from divineos.core.council.engine import get_council_engine

        engine = get_council_engine()
        if len(engine.experts) == 0:
            issues.append(
                WiringIssue(
                    component="council_engine",
                    issue="Engine singleton has zero experts registered",
                    detail="get_council_engine() returns empty engine — "
                    "experts exist but _register_all_experts() is not called",
                )
            )
    except (ImportError, AttributeError):
        # Council module may not be importable in all environments, or
        # the engine API may have shifted. Narrowed from bare Exception
        # so genuine bugs in get_council_engine() surface instead of
        # silently passing — the scanner that detects "works on paper,
        # broken in production" must not itself be broken on paper.
        pass

    # SLOT_BUILDERS: should have at least the core HUD slots
    try:
        from divineos.core.hud import SLOT_BUILDERS

        expected_core = {"identity", "active_goals", "recent_lessons", "session_health"}
        missing = expected_core - set(SLOT_BUILDERS.keys())
        if missing:
            issues.append(
                WiringIssue(
                    component="hud_slot_builders",
                    issue=f"Core HUD slots missing from SLOT_BUILDERS: {sorted(missing)}",
                    detail="HUD builder dict should contain all core slots",
                )
            )
    except (ImportError, AttributeError):
        pass

    # Active memory: refresh should produce results if knowledge exists
    try:
        from divineos.core.knowledge import get_connection

        conn = get_connection()
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM knowledge WHERE superseded_by IS NULL"
            ).fetchone()[0]
        finally:
            conn.close()

        if count > 5:
            from divineos.core.active_memory import get_active_memory

            active = get_active_memory()
            if not active:
                issues.append(
                    WiringIssue(
                        component="active_memory",
                        issue=f"{count} knowledge entries exist but active memory is empty",
                        detail="get_active_memory() returns nothing — "
                        "refresh may not be running or scoring may filter everything",
                    )
                )
    except (ImportError, AttributeError, sqlite3.Error):
        pass

    # Clarity hooks: HookIntegrationInterface._clarity_hooks is a
    # registration framework with four hook categories. If all lists
    # are empty AND the module lacks a documented-intent marker, the
    # framework is defined but has no producers — classic "registered
    # but no subscribers" dead architecture. Modules that carry one
    # of the intent markers (AGENT_RUNTIME or PHASE_1_STAGED) have
    # declared the dead-on-CLI state as intentional design and are
    # respected by the probe.
    try:
        from divineos.clarity_system import hook_integration as _hi_module
        from divineos.clarity_system.hook_integration import HookIntegrationInterface

        module_doc = (
            (_hi_module.__doc__ or "")
            + "\n"
            + (_hi_module.__file__ and _read_module_header(_hi_module.__file__) or "")
        )
        has_intent_marker = _has_intent_marker(module_doc)

        hooks = HookIntegrationInterface._clarity_hooks
        total_subscribers = sum(len(v) for v in hooks.values())
        if total_subscribers == 0 and not has_intent_marker:
            issues.append(
                WiringIssue(
                    component="clarity_hook_integration",
                    issue="HookIntegrationInterface has zero subscribers across all four registries",
                    detail="register_pre_work_hook / post_work / clarity_generated / "
                    "summary_generated define a full hook framework, but no production "
                    "module calls these registration methods. Either wire a subscriber "
                    "or add an intent marker (AGENT_RUNTIME for hook/MCP-invoked, "
                    "PHASE_1_STAGED for opt-in rollout).",
                )
            )
    except (ImportError, AttributeError, OSError):
        pass

    return issues


# Recognized documented-intent markers. A module that has zero
# non-test callers but carries one of these strings in its docstring
# or module header is intentionally-uncalled for a documented reason,
# not dead architecture.
_INTENT_MARKERS = frozenset(
    {
        # Invoked via shell hook or MCP protocol, not Python import
        "AGENT_RUNTIME",
        # Staged opt-in rollout; no callers by design until first opt-in lands
        "PHASE_1_STAGED",
    }
)


def _has_intent_marker(text: str) -> bool:
    """True if the given text contains any recognized intent marker."""
    return any(marker in text for marker in _INTENT_MARKERS)


def _read_module_header(path: str) -> str:
    """Read the first ~30 lines of a module file to check for markers
    that live outside the docstring (e.g. comment lines at the top)."""
    try:
        with open(path, encoding="utf-8") as f:
            return "".join(next(f, "") for _ in range(30))
    except OSError:
        return ""


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
    result.wiring_issues = scan_wiring()
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
    if result.wiring_issues:
        parts.append(f"{len(result.wiring_issues)} wiring issues")
    if result.self_dormant:
        parts.append("(alarm itself is dormant -- first scan)")
    return " | ".join(parts)


def format_alarm_detail(result: AlarmResult) -> str:
    """Detailed multi-line report."""
    lines = [
        f"Dead Architecture Scan -- {result.dormant_count} dormant, {result.active_count} active"
        f"{f', {len(result.display_issues)} display issues' if result.display_issues else ''}"
        f"{f', {len(result.wiring_issues)} wiring issues' if result.wiring_issues else ''}",
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

    if result.wiring_issues:
        lines.append("Wiring issues (constructed but not connected):")
        for wi in result.wiring_issues:
            lines.append(f"  [!] {wi.component}: {wi.issue}")
            lines.append(f"      fix: {wi.detail}")
        lines.append("")

    if result.self_dormant:
        lines.append("[!] This alarm's own table is empty -- first scan has not been recorded yet.")
        lines.append("")

    lines.append(f"Active tables ({result.active_count}):")
    for t in result.active_tables:
        lines.append(f"  + {t}")

    return "\n".join(lines)
