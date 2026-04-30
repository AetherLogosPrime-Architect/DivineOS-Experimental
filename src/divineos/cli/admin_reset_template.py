"""``divineos admin reset-template`` — reset a DivineOS install to fresh-template state.

Wipes accumulated personal substrate while preserving the architecture itself
(schemas, code, tests, generic documentation, placeholder READMEs, the seed
content). Used for two purposes:

1. **Fresh template preparation.** Before publishing or sharing a DivineOS
   clone, the operator can run this command to ensure no personal substrate
   ships. Their personal substrate remains in their canonical store
   (per-operator setup; e.g. a sibling repo configured via
   ``.divineos_canonical`` path-content marker).

2. **Operator wants to start over.** An operator who decides to reset their
   agent's accumulated state — for whatever reason — can do so cleanly.
   Backup is automatic; original state can be restored from the backup
   directory if needed.

The command is **destructive** and refuses to run silently. Always:
- Creates a timestamped backup before destruction.
- Refuses to run if the canonical-marker routes to a path outside the
  current checkout, unless ``--force-canonical`` is passed (safety:
  prevents accidentally resetting a routed personal-canonical store).
- Reports what it would do in dry-run mode (``--dry-run``).

What is preserved:
* All schemas (table definitions stay; only rows are dropped).
* All source code under ``src/``.
* All tests under ``tests/``.
* Generic architectural documentation (READMEs, placeholder content).
* The seed content (``seed.json`` template entries get re-applied after reset).
* The architectural family operators and template files.

What is removed:
* All accumulated rows in ``event_ledger.db`` (reset to schema-only).
* All accumulated rows in ``family.db`` (reset to schema-only).
* All knowledge entries (re-seeded from seed.json after reset).
* Filesystem accumulation: contents of ``exploration/``, ``family/letters/``,
  any non-template family-member agent files in ``.claude/agents/``.
* Personal docs in ``docs/drafts/`` (only with ``--include-drafts``).
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import time
from pathlib import Path

import click

from divineos.core._ledger_base import _get_db_path
from divineos.core.family.db import _get_family_db_path

# Files that NEVER get removed even when their parent directory is being cleared.
# These are the README.md / template files that the architecture ships and
# that explain what the directory is for.
_PROTECTED_FILES_BY_DIR: dict[str, set[str]] = {
    "exploration": {"README.md"},
    "family/letters": {"README.md"},
    "family": {"README.md"},  # plus the ``letters/`` subdir is recursed separately
    ".claude/agents": {"family-member-template.md"},
}

# Tables that just need to be cleared (DELETE FROM <table>).
# Schema is preserved; only rows are removed.
_LEDGER_TABLES_TO_CLEAR: list[str] = [
    "system_events",
    "knowledge",
    "knowledge_relationships",
    "knowledge_edges",
    "lesson_tracking",
    "session_report",
    "check_result",
    "feature_result",
    "tone_shift",
    "session_timeline",
    "file_touched",
    "activity_breakdown",
    "task_tracking",
    "error_recovery",
    "personal_journal",
    "session_history",
    "tone_texture",
    "warrants",
    "logical_relations",
    "open_questions",
    "decision_journal",
    "affect_log",
    "claims",
    "claim_evidence",
    "compass_observation",
    "opinions",
    "opinion_shifts",
    "user_models",
    "user_signals",
    "advice_tracking",
    "craft_assessments",
    "user_ratings",
    "session_validation",
    "knowledge_impact",
    "affect_extraction_correlation",
    "dead_architecture_scan",
    "audit_rounds",
    "audit_findings",
    "pattern_outcomes",
    "relationship_notes",
    "shared_history",
    "holding_room",
    "pre_registrations",
    "core_memory",
    "active_memory",
    "seed_metadata",
]

_FAMILY_TABLES_TO_CLEAR: list[str] = [
    "family_members",
    "family_knowledge",
    "family_opinions",
    "family_affect",
    "family_interactions",
    "family_milestones",
    "family_letters",
    "family_letter_responses",
    "family_queue",
]

# FTS tables — must be cleared via DELETE FROM (not DROP) to preserve their
# triggers; will be repopulated on next index-rebuild.
_FTS_TABLES: list[str] = [
    "knowledge_fts",
    "journal_fts",
    "decision_fts",
    "claim_fts",
]


def _checkout_root() -> Path:
    """Return the running checkout's root (where pyproject.toml lives)."""
    # cli/admin_reset_template.py -> cli -> divineos -> src -> <root>
    return Path(__file__).parent.parent.parent.parent


def _is_canonical_external() -> tuple[bool, Path | None]:
    """Return (is_external, target_path) about the canonical-marker.

    True if .divineos_canonical at the running checkout's root contains a
    path string pointing OUTSIDE the running checkout. False if no marker,
    empty marker, or marker points within the checkout.
    """
    root = _checkout_root()
    marker = root / ".divineos_canonical"
    if not marker.exists():
        return False, None
    try:
        content = marker.read_text(encoding="utf-8").strip()
    except OSError:
        return False, None
    if not content:
        return False, None
    target = Path(content)
    if not target.is_absolute():
        target = (marker.parent / target).resolve()
    try:
        target.relative_to(root.resolve())
        return False, target  # within the checkout
    except ValueError:
        return True, target  # outside


def _backup_path() -> Path:
    """Create a timestamped backup directory and return its path."""
    timestamp = time.strftime("%Y-%m-%d_%H%M%S")
    return _checkout_root() / "_pre_reset_backups" / timestamp


def _backup_db(db_path: Path, backup_dir: Path, label: str) -> Path | None:
    if not db_path.exists():
        return None
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / f"{label}.db"
    shutil.copy2(db_path, target)
    return target


def _clear_db_tables(db_path: Path, tables: list[str]) -> dict[str, int]:
    """Clear the listed tables in a SQLite DB. Returns rows-removed per table."""
    if not db_path.exists():
        return {}
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=OFF")
    removed: dict[str, int] = {}
    for table in tables:
        try:
            cur = conn.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            if count > 0:
                conn.execute(f"DELETE FROM {table}")
                removed[table] = count
        except sqlite3.OperationalError:
            # Table doesn't exist in this DB; skip.
            pass
    conn.commit()
    conn.execute("VACUUM")
    conn.close()
    return removed


def _clear_directory(dir_path: Path, protected: set[str]) -> list[str]:
    """Clear contents of dir_path except files named in `protected`.

    Returns list of file/dir names removed.
    """
    if not dir_path.exists():
        return []
    removed: list[str] = []
    for entry in dir_path.iterdir():
        if entry.name in protected:
            continue
        if entry.is_file():
            entry.unlink()
            removed.append(entry.name)
        elif entry.is_dir():
            shutil.rmtree(entry)
            removed.append(entry.name + "/")
    return removed


def _summarize_proposed(checkout: Path) -> dict:
    """Return a dict summarizing what would be removed without doing it."""
    db_main = _get_db_path()
    db_family = _get_family_db_path()
    summary: dict = {
        "main_db": str(db_main),
        "family_db": str(db_family),
        "main_db_exists": db_main.exists(),
        "family_db_exists": db_family.exists(),
        "main_event_count": None,
        "family_member_count": None,
        "directories_to_clear": [],
    }
    if db_main.exists():
        try:
            conn = sqlite3.connect(str(db_main))
            summary["main_event_count"] = conn.execute(
                "SELECT COUNT(*) FROM system_events"
            ).fetchone()[0]
            conn.close()
        except sqlite3.OperationalError:
            pass
    if db_family.exists():
        try:
            conn = sqlite3.connect(str(db_family))
            summary["family_member_count"] = conn.execute(
                "SELECT COUNT(*) FROM family_members"
            ).fetchone()[0]
            conn.close()
        except sqlite3.OperationalError:
            pass

    for rel_path in ("exploration", "family/letters", ".claude/agents"):
        d = checkout / rel_path
        if d.exists():
            protected = _PROTECTED_FILES_BY_DIR.get(rel_path, set())
            removable = [e.name for e in d.iterdir() if e.name not in protected]
            if removable:
                summary["directories_to_clear"].append(
                    {"path": rel_path, "count": len(removable), "items": removable}
                )
    return summary


@click.command("reset-template")
@click.option("--yes", is_flag=True, help="Skip the confirmation prompt.")
@click.option("--dry-run", is_flag=True, help="Show what would be removed; do not actually do it.")
@click.option(
    "--force-canonical",
    is_flag=True,
    help="Proceed even if the canonical-marker routes to an external path. "
    "Without this flag, the command refuses to reset routed canonical stores "
    "(safety: avoids accidentally wiping a personal-substrate store the "
    "current checkout is just routing to).",
)
@click.option(
    "--include-drafts",
    is_flag=True,
    help="Also clear docs/drafts/. Off by default since drafts/ is gitignored "
    "and operators may want their drafts preserved locally even during a reset.",
)
@click.option(
    "--no-reseed",
    is_flag=True,
    help="Do not re-apply seed.json after reset. The DB will be schema-only with "
    "no starter knowledge or core_memory defaults. Default: re-seed after reset.",
)
def reset_template(
    yes: bool,
    dry_run: bool,
    force_canonical: bool,
    include_drafts: bool,
    no_reseed: bool,
) -> None:
    """Reset this DivineOS install to a fresh-template state.

    Wipes accumulated substrate (event ledger, family DB, exploration/,
    family/letters/, non-template family-member agent files) while
    preserving schemas, code, tests, generic documentation, and the seed
    content. Creates a timestamped backup first.

    Use BEFORE publishing or sharing a DivineOS clone to ensure no personal
    substrate ships. Or when starting over with the same install.

    Refuses to run silently. Always prompts unless --yes.
    """
    checkout = _checkout_root()
    is_external, target = _is_canonical_external()

    if is_external and not force_canonical:
        click.echo(
            f"[!] The .divineos_canonical marker at {checkout} routes to an external path:",
            err=True,
        )
        click.echo(f"    {target}", err=True)
        click.echo(
            "    This means the running checkout is configured to use a personal-substrate store",
            err=True,
        )
        click.echo(
            "    located OUTSIDE this checkout. Resetting would wipe that external store.", err=True
        )
        click.echo("", err=True)
        click.echo("    To proceed anyway, pass --force-canonical.", err=True)
        click.echo(
            "    To reset only the running checkout's local data, remove the marker first.",
            err=True,
        )
        raise SystemExit(1)

    summary = _summarize_proposed(checkout)

    click.echo("=== reset-template plan ===")
    click.echo(f"  checkout root:       {checkout}")
    click.echo(f"  main DB path:        {summary['main_db']}")
    click.echo(f"  family DB path:      {summary['family_db']}")
    if summary["main_event_count"] is not None:
        click.echo(f"  events to clear:     {summary['main_event_count']}")
    if summary["family_member_count"] is not None:
        click.echo(f"  family members:      {summary['family_member_count']}")

    if summary["directories_to_clear"]:
        click.echo("  directories to clear:")
        for d in summary["directories_to_clear"]:
            click.echo(f"    - {d['path']}: {d['count']} item(s)")
            for item in d["items"][:5]:
                click.echo(f"        {item}")
            if d["count"] > 5:
                click.echo(f"        ... and {d['count'] - 5} more")
    else:
        click.echo("  directories to clear: none (already clean)")

    click.echo("")
    if dry_run:
        click.echo("[dry-run] No changes made. Re-run without --dry-run to execute.")
        return

    if not yes:
        click.confirm("Proceed with reset? A backup will be created first.", abort=True)

    # Phase 1: backup
    backup_dir = _backup_path()
    click.echo(f"\n[1/5] Creating backup at {backup_dir}...")
    backed_up = []
    for path, label in [
        (Path(summary["main_db"]), "event_ledger"),
        (Path(summary["family_db"]), "family"),
    ]:
        b = _backup_db(path, backup_dir, label)
        if b:
            backed_up.append(str(b))
    if backed_up:
        click.echo(f"      backed up: {len(backed_up)} DB file(s)")
    else:
        click.echo("      (no DB files to back up)")

    # Phase 2: clear DB tables
    click.echo("\n[2/5] Clearing DB tables...")
    main_removed = _clear_db_tables(Path(summary["main_db"]), _LEDGER_TABLES_TO_CLEAR + _FTS_TABLES)
    family_removed = _clear_db_tables(Path(summary["family_db"]), _FAMILY_TABLES_TO_CLEAR)
    total_main = sum(main_removed.values())
    total_family = sum(family_removed.values())
    click.echo(f"      main DB: cleared {total_main} rows across {len(main_removed)} tables")
    click.echo(f"      family DB: cleared {total_family} rows across {len(family_removed)} tables")

    # Phase 3: clear filesystem accumulation
    click.echo("\n[3/5] Clearing filesystem accumulation...")
    cleared_dirs: list[tuple[str, list[str]]] = []
    for rel_path in ("exploration", "family/letters", ".claude/agents"):
        d = checkout / rel_path
        if d.exists():
            protected = _PROTECTED_FILES_BY_DIR.get(rel_path, set())
            removed = _clear_directory(d, protected)
            if removed:
                cleared_dirs.append((rel_path, removed))
    for rel_path, items in cleared_dirs:
        click.echo(f"      {rel_path}: removed {len(items)} item(s)")

    if include_drafts:
        drafts = checkout / "docs" / "drafts"
        if drafts.exists():
            removed = _clear_directory(drafts, set())
            if removed:
                click.echo(f"      docs/drafts: removed {len(removed)} item(s)")

    # Phase 4: re-seed
    if not no_reseed:
        click.echo("\n[4/5] Re-applying seed.json...")
        try:
            from divineos.core.seed_manager import apply_seed

            seed_path = checkout / "src" / "divineos" / "seed.json"
            if seed_path.exists():
                with open(seed_path, encoding="utf-8") as f:
                    seed = json.load(f)
                applied = apply_seed(seed, mode="merge")
                click.echo(f"      seed applied: {applied}")
            else:
                click.echo(f"      [warn] seed.json not found at {seed_path}; skipping")
        except (ImportError, AttributeError) as e:
            click.echo(f"      [warn] could not import seed-applier: {e}; skipping reseed")
    else:
        click.echo("\n[4/5] Skipping re-seed (--no-reseed)")

    # Phase 5: rebuild FTS index
    click.echo("\n[5/5] Rebuilding full-text search index...")
    try:
        from divineos.core.knowledge.crud import rebuild_fts_index

        rebuild_fts_index()
        click.echo("      FTS index rebuilt")
    except (ImportError, AttributeError) as e:
        click.echo(f"      [warn] could not rebuild FTS: {e}")

    click.echo("\n=== reset-template complete ===")
    click.echo(f"  Backup at: {backup_dir}")
    click.echo("  This install is now in fresh-template state.")
    click.echo("  Verify: divineos preflight && divineos body")
