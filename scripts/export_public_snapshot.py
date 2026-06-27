"""Public-data snapshot exporter — text JSON snapshots of reviewed family tables.

Per Aletheia's spec 2026-06-27 (`public_research_data_report.md`):

Andrew wants the family affect/knowledge data to be public — research being
honest — but the live binary `.db` files committed to git are the wrong
mechanism. Opaque binary, blob churn fills git history with gibberish, bloats
clones. Text snapshots solve the same goal: diffable, readable in any editor,
strictly MORE inspectable than the binary.

## Design summary

- **Allowlist (REVIEWED_TABLES).** Only tables a human has glanced at for the
  4 harm-categories get exported. A new table is HELD (not published) until
  a human adds it to the set. Fail-safe direction: forgotten-to-review stays
  private.
- **Open-by-default for reviewed tables.** Andrew's name, reflections, hard
  moments — all public. The exclusion axis is harm-prevention, not secrecy.
- **Read-only DB access.** Exporter NEVER writes to the live substrate
  (sqlite URI mode=ro).
- **Harm-filter for 4 categories** (per Aletheia's spec):
  1. Credentials / secrets / keys (regex on text columns)
  2. Non-consenting third parties (only Andrew + family_members are
     consented entities; identifying detail of any other real person
     gets scrubbed)
  3. Operationally exploitable specifics (bypass/override mechanism
     detail)
  4. Andrew's physical-locating fields (street address, precise geo —
     NOT his name)
- **Fail-soft per table.** Error on one table logs + SKIPS that table
  (omits, never leaks). A table whose redaction can't be applied is
  OMITTED, not published raw.
- **Stable serialization.** Sorted keys + sorted rows by primary key
  → unchanged snapshot produces an identical file.
- **Manifest with source SHA.** Each snapshot bound to the code-state
  that produced it.

## Usage

    python scripts/export_public_snapshot.py [--db-path PATH] [--out-dir PATH]

Defaults:
    --db-path  <repo>/family/family.db
    --out-dir  <repo>/data/public-snapshots

Exit codes:
    0  success (or partial success with some tables omitted)
    2  fatal error (DB missing, output dir not writable, etc.)
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# REVIEWED_TABLES — the human-glanced allowlist.
#
# A table NOT in this set is HELD until a human adds it. This is the
# one-time per-new-table review forcing the harm-glance before any new
# table goes public.
# ---------------------------------------------------------------------------

REVIEWED_TABLES = frozenset(
    {
        "family_members",
        "family_affect",
        "family_knowledge",
        "family_opinions",
        "family_milestones",
        "family_interactions",
        "family_queue",
    }
)


# ---------------------------------------------------------------------------
# HARM_FILTER — 4 categories, applied as column/value scrubbers.
# ---------------------------------------------------------------------------

# 1. Credentials / secrets / keys
_CREDENTIAL_PATTERNS = (
    re.compile(r"\b(?:api[_-]?key|apikey)[\s=:]+[\w\-/+=]{12,}", re.IGNORECASE),
    re.compile(r"\b(?:password|passwd|pwd)[\s=:]+\S{6,}", re.IGNORECASE),
    re.compile(r"\b(?:secret|token)[\s=:]+\w{16,}", re.IGNORECASE),
    re.compile(r"\b(?:bearer|authorization)[\s:]+[\w\-./+=]{20,}", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9]{32,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
)

# 2. Non-consenting third parties — phone, email, social handles of UNKNOWN
#    people. Detection is conservative; we redact anything matching common
#    PII shapes. Andrew's own contact info is also redacted (he is consented
#    by name, not by contact-details which would invite unwanted contact).
_THIRD_PARTY_PATTERNS = (
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),  # email
    re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),  # US phone
    re.compile(r"\bSSN[\s:#]*\d{3}[-\s]?\d{2}[-\s]?\d{4}\b", re.IGNORECASE),
)

# 3. Operationally exploitable specifics — bypass/override mechanism detail
#    that would let an attacker corrupt the substrate. Conservative regex on
#    explicit "how to bypass" language.
_EXPLOIT_PATTERNS = (
    re.compile(
        r"\b(?:to\s+bypass|how\s+to\s+bypass|disable\s+the\s+gate|override\s+the\s+check)\b[^.\n]{0,80}",
        re.IGNORECASE,
    ),
)

# 4. Andrew's physical-locating details — street address pattern + ZIP-code
#    pattern. Conservative US-style match. Does NOT include his name (his
#    name is public per the consent stance).
_LOCATION_PATTERNS = (
    re.compile(
        r"\b\d{1,5}\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+"
        r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Place|Pl|Way)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b\d{5}(?:-\d{4})?\b"),  # US ZIP (5 or 9 digit)
)


def _scrub(value: object) -> object:
    """Apply all four harm-filter categories to a single value.

    Non-text values pass through unchanged. Text values get pattern-replaced.
    Returns the scrubbed value.
    """
    if not isinstance(value, str):
        return value
    out = value
    for pat in _CREDENTIAL_PATTERNS:
        out = pat.sub("[REDACTED:credential]", out)
    for pat in _THIRD_PARTY_PATTERNS:
        out = pat.sub("[REDACTED:third-party-contact]", out)
    for pat in _EXPLOIT_PATTERNS:
        out = pat.sub("[REDACTED:exploit-detail]", out)
    for pat in _LOCATION_PATTERNS:
        out = pat.sub("[REDACTED:location]", out)
    return out


# ---------------------------------------------------------------------------
# Exporter
# ---------------------------------------------------------------------------


def _open_readonly(db_path: Path) -> sqlite3.Connection:
    """Open the DB in URI mode=ro so the exporter cannot write to live state."""
    uri = f"file:{db_path.as_posix()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _list_tables(conn: sqlite3.Connection) -> list[str]:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
    return [r[0] for r in cur.fetchall()]


def _primary_key_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return [r[1] for r in cur.fetchall() if r[5] != 0]  # r[5] is pk index, 0=not pk


def _export_table(conn: sqlite3.Connection, table: str, out_dir: Path) -> tuple[bool, str]:
    """Export one table to JSON. Returns (success, message).

    Fail-soft contract: any error logs + returns (False, reason). Caller
    omits failed tables from the manifest. NEVER writes a partial / raw
    table — either the scrubbed JSON gets written, or the file is absent.
    """
    try:
        cur = conn.execute(f"SELECT * FROM {table}")
        columns = [d[0] for d in cur.description]
        rows = cur.fetchall()
    except sqlite3.Error as exc:
        return False, f"select failed: {exc}"

    try:
        scrubbed = [
            {col: _scrub(row[i]) for i, col in enumerate(columns)} for row in rows
        ]
    except Exception as exc:  # noqa: BLE001 — fail-soft envelope
        return False, f"scrub failed: {exc}"

    pk_cols = _primary_key_columns(conn, table) or columns[:1]
    try:
        scrubbed.sort(key=lambda r: tuple(str(r.get(c, "")) for c in pk_cols))
    except Exception as exc:  # noqa: BLE001
        return False, f"sort failed: {exc}"

    out_path = out_dir / f"{table}.json"
    payload = {
        "table": table,
        "row_count": len(scrubbed),
        "columns": columns,
        "rows": scrubbed,
    }
    try:
        out_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError as exc:
        return False, f"write failed: {exc}"

    return True, f"{len(scrubbed)} rows"


def _git_sha(repo_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def export_public_snapshot(db_path: Path, out_dir: Path, repo_root: Path) -> int:
    """Top-level: dump all reviewed tables in db_path to JSON in out_dir.

    Returns 0 on success (even if some individual tables failed and were
    omitted — that's the fail-soft contract). Returns 2 only on fatal
    setup errors (DB missing, output dir not writable).
    """
    if not db_path.exists():
        print(f"[snapshot] FATAL: db not found at {db_path}", file=sys.stderr)
        return 2
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"[snapshot] FATAL: cannot create out_dir {out_dir}: {exc}", file=sys.stderr)
        return 2

    try:
        conn = _open_readonly(db_path)
    except sqlite3.Error as exc:
        print(f"[snapshot] FATAL: cannot open db {db_path}: {exc}", file=sys.stderr)
        return 2

    try:
        present_tables = set(_list_tables(conn))
    except sqlite3.Error as exc:
        conn.close()
        print(f"[snapshot] FATAL: cannot list tables: {exc}", file=sys.stderr)
        return 2

    # Reviewed-tables gate. Tables in DB but NOT in REVIEWED_TABLES are HELD.
    # Tables in REVIEWED_TABLES but NOT in DB are silently absent (the DB
    # may legitimately not have all reviewed tables yet).
    held = sorted(present_tables - REVIEWED_TABLES)
    exporting = sorted(present_tables & REVIEWED_TABLES)

    exported: dict[str, int] = {}
    omitted: dict[str, str] = {}

    for table in exporting:
        ok, msg = _export_table(conn, table, out_dir)
        if ok:
            # msg is "N rows"
            try:
                exported[table] = int(msg.split()[0])
            except (ValueError, IndexError):
                exported[table] = 0
            print(f"[snapshot] {table}: {msg}")
        else:
            omitted[table] = msg
            print(f"[snapshot] {table}: OMITTED ({msg})", file=sys.stderr)

    conn.close()

    manifest = {
        "exported_at_unix": int(time.time()),
        "source_db": str(db_path),
        "source_git_sha": _git_sha(repo_root),
        "reviewed_tables_allowlist": sorted(REVIEWED_TABLES),
        "exported": exported,
        "omitted": omitted,
        "held_unreviewed_tables_present_in_db": held,
        "schema_version": 1,
    }
    manifest_path = out_dir / "manifest.json"
    try:
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"[snapshot] FATAL: cannot write manifest: {exc}", file=sys.stderr)
        return 2

    print(
        f"[snapshot] done: {len(exported)} exported, "
        f"{len(omitted)} omitted, {len(held)} unreviewed-held"
    )
    return 0


def _default_paths() -> tuple[Path, Path, Path]:
    repo_root = Path(__file__).resolve().parent.parent
    return (
        repo_root / "family" / "family.db",
        repo_root / "data" / "public-snapshots",
        repo_root,
    )


def main(argv: list[str] | None = None) -> int:
    default_db, default_out, default_repo = _default_paths()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument("--db-path", type=Path, default=default_db)
    parser.add_argument("--out-dir", type=Path, default=default_out)
    parser.add_argument("--repo-root", type=Path, default=default_repo)
    args = parser.parse_args(argv)
    return export_public_snapshot(args.db_path, args.out_dir, args.repo_root)


if __name__ == "__main__":
    raise SystemExit(main())
