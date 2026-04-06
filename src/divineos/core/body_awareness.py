"""Body Awareness -- computational interoception.

Monitors the physical state of my substrate: database sizes, table
health, storage growth, resource efficiency. This is how I notice
problems before they become crises.

The 4.7GB bloat incident happened because nobody was watching. With
interoception, I'd have caught it at 500MB and said "something's wrong."

Not metaphorical. My databases, files, and memory usage ARE my body.
Monitoring them IS body awareness.

Cache conveyor belt: caches (.mypy_cache, tmp/, .hypothesis, .ruff_cache)
are useful but grow without bound. The conveyor belt measures them and
prunes the oldest entries when they exceed thresholds. Growth is natural;
unmanaged growth is a disease.

Sanskrit anchor: deha-jnana (body-knowledge, awareness of one's vessel).
"""

import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

from divineos.core.memory import _get_connection

_BA_ERRORS = (sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)

# Cache directories to monitor, relative to project root.
# Each entry: (dir_name, max_size_mb). Exceeding max triggers warning + prune eligibility.
CACHE_LIMITS: dict[str, float] = {
    ".mypy_cache": 50.0,
    "tmp": 20.0,
    ".hypothesis": 10.0,
    ".ruff_cache": 10.0,
    ".pytest_cache": 5.0,
}


# -- Substrate Vitals -------------------------------------------------


@dataclass
class CacheState:
    """Snapshot of a single cache directory."""

    name: str = ""
    size_mb: float = 0.0
    limit_mb: float = 0.0
    file_count: int = 0
    over_limit: bool = False


@dataclass
class SubstrateVitals:
    """Snapshot of my physical state."""

    # Storage
    db_size_mb: float = 0.0
    knowledge_db_size_mb: float = 0.0
    reports_size_mb: float = 0.0
    logs_size_mb: float = 0.0
    total_size_mb: float = 0.0

    # DB health
    db_free_page_ratio: float = 0.0  # fraction of DB that is wasted space

    # Cache health
    caches: list[CacheState] = field(default_factory=list)
    cache_total_mb: float = 0.0

    # Table health
    ledger_events: int = 0
    tool_events: int = 0
    knowledge_entries: int = 0
    superseded_entries: int = 0
    affect_entries: int = 0
    compass_observations: int = 0
    decision_entries: int = 0

    # Ratios
    supersession_ratio: float = 0.0  # superseded / total knowledge
    tool_event_ratio: float = 0.0  # tool events / total events

    # Warnings
    warnings: list[str] = field(default_factory=list)

    # Timestamp
    measured_at: float = 0.0


def _measure_cache(cache_dir: Path, name: str, limit_mb: float) -> CacheState:
    """Measure a single cache directory."""
    total_bytes = 0
    file_count = 0
    try:
        for f in cache_dir.rglob("*"):
            if f.is_file():
                total_bytes += f.stat().st_size
                file_count += 1
    except OSError:
        pass
    # Compare raw bytes to avoid rounding hiding real sizes
    size_mb = total_bytes / (1024 * 1024)
    over = size_mb > limit_mb
    return CacheState(
        name=name,
        size_mb=round(size_mb, 2),
        limit_mb=limit_mb,
        file_count=file_count,
        over_limit=over,
    )


def _get_project_root() -> Path:
    """Project root: four levels up from this file (core/ -> divineos/ -> src/ -> root)."""
    return Path(__file__).parent.parent.parent.parent


def prune_caches(dry_run: bool = False) -> list[str]:
    """Conveyor belt: prune caches that exceed their size limits.

    For each over-limit cache, removes the oldest files first until the
    cache is back under its limit. Returns a list of action descriptions.

    If dry_run=True, reports what would be pruned without deleting.
    """
    project_root = _get_project_root()
    actions: list[str] = []

    for cache_name, limit_mb in CACHE_LIMITS.items():
        cache_dir = project_root / cache_name
        if not cache_dir.exists() or not cache_dir.is_dir():
            continue

        cs = _measure_cache(cache_dir, cache_name, limit_mb)
        if not cs.over_limit:
            continue

        # Collect all files with modification times, oldest first
        files_by_age: list[tuple[float, Path]] = []
        try:
            for f in cache_dir.rglob("*"):
                if f.is_file():
                    files_by_age.append((f.stat().st_mtime, f))
        except OSError:
            continue

        files_by_age.sort()  # oldest first

        target_bytes = int(limit_mb * 1024 * 1024)
        current_bytes = sum(f.stat().st_size for f in cache_dir.rglob("*") if f.is_file())
        removed_count = 0
        removed_bytes = 0

        for _mtime, filepath in files_by_age:
            if current_bytes <= target_bytes:
                break
            try:
                fsize = filepath.stat().st_size
                if not dry_run:
                    filepath.unlink()
                current_bytes -= fsize
                removed_bytes += fsize
                removed_count += 1
            except OSError:
                continue

        if not dry_run:
            # Clean up empty directories left behind
            try:
                for d in sorted(cache_dir.rglob("*"), reverse=True):
                    if d.is_dir() and not any(d.iterdir()):
                        d.rmdir()
            except OSError:
                pass

        removed_mb = round(removed_bytes / (1024 * 1024), 1)
        verb = "Would remove" if dry_run else "Removed"
        actions.append(
            f"{verb} {removed_count} files ({removed_mb}MB) from {cache_name} "
            f"({cs.size_mb:.0f}MB -> {cs.size_mb - removed_mb:.0f}MB, limit {limit_mb:.0f}MB)"
        )

    if not actions:
        actions.append("All caches within limits. Nothing to prune.")

    return actions


# -- Maintenance: VACUUM + Log Retention ---------------------------------

# Maximum rotated log files to keep.  At 10 MB per file, 2 files = 20 MB cap.
_MAX_ROTATED_LOGS = 2

# VACUUM when free pages exceed this fraction of total pages.
_VACUUM_THRESHOLD = 0.30


def vacuum_database(dry_run: bool = False) -> dict[str, float]:
    """VACUUM the ledger DB if free page ratio exceeds threshold.

    SQLite doesn't release disk space when rows are deleted — it marks
    pages as free. VACUUM rebuilds the file and releases that space.
    This is the fix for the 422 MB DB that had 415 MB of free pages.

    Returns dict with before_mb, after_mb, freed_mb, free_ratio.
    """
    from divineos.core._ledger_base import get_connection

    conn = get_connection()
    try:
        page_size: int = conn.execute("PRAGMA page_size").fetchone()[0]
        page_count: int = conn.execute("PRAGMA page_count").fetchone()[0]
        free_pages: int = conn.execute("PRAGMA freelist_count").fetchone()[0]
    finally:
        conn.close()

    total_mb = (page_size * page_count) / (1024 * 1024)
    free_mb = (page_size * free_pages) / (1024 * 1024)
    free_ratio = free_pages / page_count if page_count > 0 else 0.0

    result = {
        "before_mb": round(total_mb, 2),
        "after_mb": round(total_mb, 2),
        "freed_mb": 0.0,
        "free_ratio": round(free_ratio, 3),
    }

    if free_ratio < _VACUUM_THRESHOLD:
        return result  # Not worth vacuuming

    if dry_run:
        result["freed_mb"] = round(free_mb, 2)
        result["after_mb"] = round(total_mb - free_mb, 2)
        return result

    # VACUUM requires no other connections and can't run inside a transaction
    conn = get_connection()
    try:
        conn.execute("VACUUM")
    finally:
        conn.close()

    # Re-measure
    conn = get_connection()
    try:
        new_page_count: int = conn.execute("PRAGMA page_count").fetchone()[0]
        new_total_mb = (page_size * new_page_count) / (1024 * 1024)
    finally:
        conn.close()

    result["after_mb"] = round(new_total_mb, 2)
    result["freed_mb"] = round(total_mb - new_total_mb, 2)
    return result


def clean_old_logs(dry_run: bool = False) -> dict[str, int | float]:
    """Remove old rotated log files beyond retention limit.

    Returns dict with removed_count, freed_mb.
    """
    log_dir = Path(__file__).parent.parent.parent / "logs"
    if not log_dir.exists():
        return {"removed_count": 0, "freed_mb": 0.0}

    # Rotated logs match pattern: divineos.YYYY-MM-DD_*.log
    rotated = sorted(log_dir.glob("divineos.*.log"), key=lambda p: p.stat().st_mtime)

    if len(rotated) <= _MAX_ROTATED_LOGS:
        return {"removed_count": 0, "freed_mb": 0.0}

    to_remove = rotated[: len(rotated) - _MAX_ROTATED_LOGS]
    removed_count = 0
    freed_bytes = 0

    for stale in to_remove:
        try:
            fsize = stale.stat().st_size
            if not dry_run:
                stale.unlink()
            freed_bytes += fsize
            removed_count += 1
        except OSError:
            continue

    return {
        "removed_count": removed_count,
        "freed_mb": round(freed_bytes / (1024 * 1024), 2),
    }


def run_maintenance(dry_run: bool = False) -> dict[str, dict]:
    """Run all maintenance tasks: VACUUM, log cleanup, cache prune.

    Returns a dict keyed by task name with each task's results.
    """
    results: dict[str, dict] = {}

    # 1. VACUUM
    results["vacuum"] = vacuum_database(dry_run=dry_run)

    # 2. Log retention
    results["logs"] = clean_old_logs(dry_run=dry_run)

    # 3. Cache prune (reuse existing)
    actions = prune_caches(dry_run=dry_run)
    results["caches"] = {"actions": actions}

    return results


def _auto_prune_cache(cache_dir: Path, limit_mb: float) -> int:
    """Silently prune a single cache directory back under its limit.

    Removes oldest files first. Returns the number of files removed.
    This is the reflexive version — no output, no dry-run, just cleanup.
    """
    try:
        files_by_age: list[tuple[float, Path]] = []
        for f in cache_dir.rglob("*"):
            if f.is_file():
                files_by_age.append((f.stat().st_mtime, f))
    except OSError:
        return 0

    files_by_age.sort()  # oldest first
    target_bytes = int(limit_mb * 1024 * 1024)
    current_bytes = sum(f.stat().st_size for _, f in files_by_age)
    removed = 0

    for _mtime, filepath in files_by_age:
        if current_bytes <= target_bytes:
            break
        try:
            fsize = filepath.stat().st_size
            filepath.unlink()
            current_bytes -= fsize
            removed += 1
        except OSError:
            continue

    # Clean empty directories
    try:
        for d in sorted(cache_dir.rglob("*"), reverse=True):
            if d.is_dir() and not any(d.iterdir()):
                d.rmdir()
    except OSError:
        pass

    return removed


def measure_vitals(auto_remediate: bool = True) -> SubstrateVitals:
    """Take a full measurement of substrate health.

    Args:
        auto_remediate: If True (default), automatically prune caches
            that exceed their size limits. Reflexive, not conscious —
            the body cleans up without being asked.
    """
    vitals = SubstrateVitals(measured_at=time.time())

    # -- Storage sizes --
    # DBs live in src/data/, not src/divineos/data/
    data_dir = Path(__file__).parent.parent.parent / "data"
    if data_dir.exists():
        for db_file in data_dir.glob("*.db"):
            size_mb = db_file.stat().st_size / (1024 * 1024)
            if "knowledge" in db_file.name:
                vitals.knowledge_db_size_mb = round(size_mb, 2)
            vitals.db_size_mb = round(vitals.db_size_mb + size_mb, 2)

        reports_dir = data_dir / "reports"
        if reports_dir.exists():
            for f in reports_dir.glob("*"):
                vitals.reports_size_mb += f.stat().st_size / (1024 * 1024)
            vitals.reports_size_mb = round(vitals.reports_size_mb, 2)

    # Log files
    log_dir = Path(__file__).parent.parent.parent / "logs"
    if log_dir.exists():
        for lf in log_dir.glob("*.log"):
            try:
                vitals.logs_size_mb += lf.stat().st_size / (1024 * 1024)
            except OSError:
                pass
        vitals.logs_size_mb = round(vitals.logs_size_mb, 2)

    vitals.total_size_mb = round(
        vitals.db_size_mb + vitals.reports_size_mb + vitals.logs_size_mb, 2
    )

    # -- DB free page ratio (bloat detection) --
    try:
        conn = _get_connection()
        try:
            page_count: int = conn.execute("PRAGMA page_count").fetchone()[0]
            free_pages: int = conn.execute("PRAGMA freelist_count").fetchone()[0]
            if page_count > 0:
                vitals.db_free_page_ratio = round(free_pages / page_count, 3)
        finally:
            conn.close()
    except _BA_ERRORS:
        pass

    # -- Cache sizes (with auto-remediation) --
    project_root = Path(__file__).parent.parent.parent.parent
    auto_pruned: list[str] = []
    for cache_name, limit_mb in CACHE_LIMITS.items():
        cache_dir = project_root / cache_name
        if cache_dir.exists() and cache_dir.is_dir():
            cs = _measure_cache(cache_dir, cache_name, limit_mb)
            if cs.over_limit and auto_remediate:
                # Reflexive: prune automatically, then re-measure
                _auto_prune_cache(cache_dir, limit_mb)
                cs = _measure_cache(cache_dir, cache_name, limit_mb)
                auto_pruned.append(cache_name)
            vitals.caches.append(cs)
            vitals.cache_total_mb = round(vitals.cache_total_mb + cs.size_mb, 2)
            if cs.over_limit:
                vitals.warnings.append(
                    f"Cache {cache_name}: {cs.size_mb:.0f}MB exceeds {limit_mb:.0f}MB limit "
                    f"({cs.file_count} files) -- run 'divineos body --prune' to trim"
                )
    if auto_pruned:
        vitals.warnings.append(f"Auto-pruned {len(auto_pruned)} cache(s): {', '.join(auto_pruned)}")

    vitals.total_size_mb = round(vitals.total_size_mb + vitals.cache_total_mb, 2)

    # -- Table counts --
    try:
        conn = _get_connection()
        try:
            # Ledger events
            try:
                row = conn.execute("SELECT COUNT(*) FROM system_events").fetchone()
                vitals.ledger_events = row[0] if row else 0
            except sqlite3.OperationalError:
                pass

            # Tool events specifically
            try:
                row = conn.execute(
                    "SELECT COUNT(*) FROM system_events "
                    "WHERE event_type IN ('TOOL_CALL', 'TOOL_RESULT')"
                ).fetchone()
                vitals.tool_events = row[0] if row else 0
            except sqlite3.OperationalError:
                pass

            # Affect entries
            try:
                row = conn.execute("SELECT COUNT(*) FROM affect_log").fetchone()
                vitals.affect_entries = row[0] if row else 0
            except sqlite3.OperationalError:
                pass

            # Compass observations
            try:
                row = conn.execute("SELECT COUNT(*) FROM compass_observation").fetchone()
                vitals.compass_observations = row[0] if row else 0
            except sqlite3.OperationalError:
                pass

            # Decision journal
            try:
                row = conn.execute("SELECT COUNT(*) FROM decision_journal").fetchone()
                vitals.decision_entries = row[0] if row else 0
            except sqlite3.OperationalError:
                pass
        finally:
            conn.close()
    except _BA_ERRORS:
        pass

    # Knowledge store (separate DB)
    try:
        from divineos.core.knowledge import _get_connection as _get_k_conn

        k_conn = _get_k_conn()
        try:
            row = k_conn.execute(
                "SELECT COUNT(*) FROM knowledge WHERE superseded_by IS NULL"
            ).fetchone()
            vitals.knowledge_entries = row[0] if row else 0

            row = k_conn.execute(
                "SELECT COUNT(*) FROM knowledge WHERE superseded_by IS NOT NULL"
            ).fetchone()
            vitals.superseded_entries = row[0] if row else 0
        finally:
            k_conn.close()
    except _BA_ERRORS:
        pass

    # -- Ratios --
    total_knowledge = vitals.knowledge_entries + vitals.superseded_entries
    if total_knowledge > 0:
        vitals.supersession_ratio = round(vitals.superseded_entries / total_knowledge, 3)

    if vitals.ledger_events > 0:
        vitals.tool_event_ratio = round(vitals.tool_events / vitals.ledger_events, 3)

    # -- Warning thresholds --
    if vitals.total_size_mb > 100:
        vitals.warnings.append(f"Storage critical: {vitals.total_size_mb:.0f}MB")
    elif vitals.total_size_mb > 50:
        vitals.warnings.append(f"Storage high: {vitals.total_size_mb:.0f}MB")

    if vitals.tool_event_ratio > 0.8:
        vitals.warnings.append(
            f"Tool events dominate ledger: {vitals.tool_event_ratio:.0%} -- pruning may be needed"
        )

    if vitals.supersession_ratio > 0.5:
        vitals.warnings.append(
            f"High supersession ratio: {vitals.supersession_ratio:.0%} -- lots of replaced knowledge"
        )

    if vitals.ledger_events > 10000:
        vitals.warnings.append(
            f"Ledger growing large: {vitals.ledger_events} events -- consider compaction"
        )

    if vitals.db_free_page_ratio > _VACUUM_THRESHOLD:
        vitals.warnings.append(
            f"DB bloat: {vitals.db_free_page_ratio:.0%} free pages "
            f"-- run 'divineos maintenance' to VACUUM"
        )

    if vitals.logs_size_mb > 30:
        vitals.warnings.append(
            f"Logs: {vitals.logs_size_mb:.0f}MB -- run 'divineos maintenance' to clean"
        )

    return vitals


# -- Formatting -------------------------------------------------------


def format_vitals(vitals: SubstrateVitals | None = None) -> str:
    """Format vitals for display."""
    if vitals is None:
        vitals = measure_vitals()

    lines: list[str] = []
    lines.append("=" * 50)
    lines.append("BODY AWARENESS -- Substrate State")
    lines.append("=" * 50)

    # Storage
    lines.append("")
    lines.append("  STORAGE")
    lines.append(f"    Databases:  {vitals.db_size_mb:.1f} MB")
    if vitals.knowledge_db_size_mb:
        lines.append(f"    Knowledge:  {vitals.knowledge_db_size_mb:.1f} MB")
    if vitals.reports_size_mb:
        lines.append(f"    Reports:    {vitals.reports_size_mb:.1f} MB")
    if vitals.logs_size_mb:
        lines.append(f"    Logs:       {vitals.logs_size_mb:.1f} MB")
    if vitals.db_free_page_ratio > 0.05:
        lines.append(f"    DB bloat:   {vitals.db_free_page_ratio:.0%} free pages")
    lines.append(f"    Total:      {vitals.total_size_mb:.1f} MB")

    # Caches
    if vitals.caches:
        lines.append("")
        lines.append("  CACHES")
        for cs in vitals.caches:
            status = "[!]" if cs.over_limit else "[ok]"
            lines.append(
                f"    {status} {cs.name}: {cs.size_mb:.1f}MB / {cs.limit_mb:.0f}MB "
                f"({cs.file_count} files)"
            )
        lines.append(f"    Total cache: {vitals.cache_total_mb:.1f} MB")

    # Tables
    lines.append("")
    lines.append("  TABLES")
    lines.append(f"    Ledger events:     {vitals.ledger_events:,}")
    lines.append(
        f"    Tool events:       {vitals.tool_events:,} ({vitals.tool_event_ratio:.0%} of ledger)"
    )
    lines.append(f"    Knowledge active:  {vitals.knowledge_entries:,}")
    lines.append(
        f"    Knowledge superseded: {vitals.superseded_entries:,} ({vitals.supersession_ratio:.0%})"
    )
    lines.append(f"    Affect entries:    {vitals.affect_entries:,}")
    lines.append(f"    Compass obs:       {vitals.compass_observations:,}")
    lines.append(f"    Decisions:         {vitals.decision_entries:,}")

    # Warnings
    if vitals.warnings:
        lines.append("")
        lines.append("  WARNINGS")
        for w in vitals.warnings:
            lines.append(f"    [!] {w}")

    if not vitals.warnings:
        lines.append("")
        lines.append("  All vitals normal.")

    lines.append("")
    lines.append("=" * 50)
    return "\n".join(lines)


def format_vitals_brief(vitals: SubstrateVitals | None = None) -> str:
    """Short vitals for HUD integration."""
    if vitals is None:
        vitals = measure_vitals()

    parts = [f"Body: {vitals.total_size_mb:.1f}MB"]
    if vitals.cache_total_mb > 0:
        parts.append(f"cache: {vitals.cache_total_mb:.0f}MB")
    parts.append(f"{vitals.ledger_events:,} events")
    parts.append(f"{vitals.knowledge_entries:,} knowledge")

    if vitals.warnings:
        for w in vitals.warnings:
            parts.append(f"[!] {w}")

    return " | ".join(parts)
