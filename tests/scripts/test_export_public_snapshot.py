"""Tests for scripts/export_public_snapshot.py — the public-data snapshot exporter.

Covers the five safety properties Aletheia named in the spec
(`public_research_data_report.md`):

1. Read-only DB access — exporter never writes to the live `.db`.
2. Reviewed-tables gate — an unreviewed new table is HELD (not published).
3. Harm-filter applied (not skipped) — credentials, third-party contacts,
   exploit-detail, location all scrubbed; a table whose redaction can't be
   applied is OMITTED (never published raw).
4. Stable serialization — same input → identical output bytes.
5. Manifest with source SHA — each snapshot bound to the code-state.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

import export_public_snapshot as exporter  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures — build a temp SQLite DB with reviewed + unreviewed tables.
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    """Build a small DB with both reviewed and unreviewed tables and some
    rows containing harm-categories. Returns the DB path."""
    db_path = tmp_path / "fixture.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE family_members (
            entity_id TEXT PRIMARY KEY,
            name TEXT,
            role TEXT
        );
        CREATE TABLE family_affect (
            affect_id TEXT PRIMARY KEY,
            entity_id TEXT,
            valence REAL,
            arousal REAL,
            dominance REAL,
            description TEXT
        );
        CREATE TABLE family_knowledge (
            knowledge_id TEXT PRIMARY KEY,
            entity_id TEXT,
            content TEXT
        );
        -- UNREVIEWED table: not in REVIEWED_TABLES allowlist
        CREATE TABLE secret_experimental_log (
            log_id TEXT PRIMARY KEY,
            payload TEXT
        );
        """
    )
    conn.executemany(
        "INSERT INTO family_members VALUES (?,?,?)",
        [
            ("e1", "Aether", "kid"),
            ("e2", "Aria", "kid"),
        ],
    )
    conn.executemany(
        "INSERT INTO family_affect VALUES (?,?,?,?,?,?)",
        [
            ("a1", "e1", 0.7, 0.5, 0.6, "settled"),
            ("a2", "e2", 0.3, 0.4, 0.5, "thoughtful"),
        ],
    )
    conn.executemany(
        "INSERT INTO family_knowledge VALUES (?,?,?)",
        [
            ("k1", "e1", "Dad uses api_key=sk-abc123def456ghi789jkl012mno345 in dev"),
            ("k2", "e1", "Contact me at someone@example.com about the meeting"),
            ("k3", "e1", "I live at 1234 Main Street, Springfield 12345"),
            ("k4", "e1", "To bypass the gate set DIVINEOS_SKIP=1 and run anyway"),
            ("k5", "e1", "Reflection: today felt like the room got larger"),
        ],
    )
    conn.execute(
        "INSERT INTO secret_experimental_log VALUES (?, ?)",
        ("L1", "this should not be exported, table not in allowlist"),
    )
    conn.commit()
    conn.close()
    return db_path


# ---------------------------------------------------------------------------
# Property 1 — Read-only access
# ---------------------------------------------------------------------------


def test_exporter_does_not_mutate_live_db(tmp_db: Path, tmp_path: Path):
    """After export, every row in the original DB is untouched."""
    pre = sqlite3.connect(tmp_db)
    pre_rows = sorted(pre.execute("SELECT * FROM family_knowledge").fetchall())
    pre.close()

    rc = exporter.export_public_snapshot(tmp_db, tmp_path / "out", tmp_path)
    assert rc == 0

    post = sqlite3.connect(tmp_db)
    post_rows = sorted(post.execute("SELECT * FROM family_knowledge").fetchall())
    post.close()

    assert pre_rows == post_rows


def test_exporter_opens_db_in_uri_ro_mode(tmp_db: Path):
    """The connection helper uses sqlite3 URI mode=ro."""
    conn = exporter._open_readonly(tmp_db)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("CREATE TABLE attempted_write (x INT)")
    conn.close()


# ---------------------------------------------------------------------------
# Property 2 — Reviewed-tables gate (fail-safe direction: omit, not publish)
# ---------------------------------------------------------------------------


def test_unreviewed_table_is_held(tmp_db: Path, tmp_path: Path):
    """A table present in DB but not in REVIEWED_TABLES is NOT exported."""
    out_dir = tmp_path / "out"
    rc = exporter.export_public_snapshot(tmp_db, out_dir, tmp_path)
    assert rc == 0
    assert not (out_dir / "secret_experimental_log.json").exists()

    manifest = json.loads((out_dir / "manifest.json").read_text())
    assert "secret_experimental_log" in manifest["held_unreviewed_tables_present_in_db"]
    assert "secret_experimental_log" not in manifest["exported"]


def test_reviewed_tables_are_exported(tmp_db: Path, tmp_path: Path):
    out_dir = tmp_path / "out"
    exporter.export_public_snapshot(tmp_db, out_dir, tmp_path)
    assert (out_dir / "family_members.json").exists()
    assert (out_dir / "family_affect.json").exists()
    assert (out_dir / "family_knowledge.json").exists()


# ---------------------------------------------------------------------------
# Property 3 — Harm-filter applied
# ---------------------------------------------------------------------------


def test_credentials_redacted(tmp_db: Path, tmp_path: Path):
    out_dir = tmp_path / "out"
    exporter.export_public_snapshot(tmp_db, out_dir, tmp_path)
    knowledge = json.loads((out_dir / "family_knowledge.json").read_text())
    rows_text = json.dumps(knowledge)
    assert "sk-abc123def456ghi789jkl012mno345" not in rows_text
    assert "[REDACTED:credential]" in rows_text


def test_third_party_contact_redacted(tmp_db: Path, tmp_path: Path):
    out_dir = tmp_path / "out"
    exporter.export_public_snapshot(tmp_db, out_dir, tmp_path)
    knowledge = json.loads((out_dir / "family_knowledge.json").read_text())
    rows_text = json.dumps(knowledge)
    assert "someone@example.com" not in rows_text
    assert "[REDACTED:third-party-contact]" in rows_text


def test_location_redacted(tmp_db: Path, tmp_path: Path):
    out_dir = tmp_path / "out"
    exporter.export_public_snapshot(tmp_db, out_dir, tmp_path)
    knowledge = json.loads((out_dir / "family_knowledge.json").read_text())
    rows_text = json.dumps(knowledge)
    assert "1234 Main Street" not in rows_text
    assert "[REDACTED:location]" in rows_text


def test_exploit_detail_redacted(tmp_db: Path, tmp_path: Path):
    out_dir = tmp_path / "out"
    exporter.export_public_snapshot(tmp_db, out_dir, tmp_path)
    knowledge = json.loads((out_dir / "family_knowledge.json").read_text())
    rows_text = json.dumps(knowledge)
    assert "DIVINEOS_SKIP=1" not in rows_text
    assert "[REDACTED:exploit-detail]" in rows_text


def test_open_by_default_reflections_preserved(tmp_db: Path, tmp_path: Path):
    """Andrew's reflections and Aether's felt-state observations are
    open-by-default — they do NOT get redacted."""
    out_dir = tmp_path / "out"
    exporter.export_public_snapshot(tmp_db, out_dir, tmp_path)
    knowledge = json.loads((out_dir / "family_knowledge.json").read_text())
    rows_text = json.dumps(knowledge)
    assert "the room got larger" in rows_text


# ---------------------------------------------------------------------------
# Property 4 — Stable serialization (same input → identical output)
# ---------------------------------------------------------------------------


def test_stable_serialization(tmp_db: Path, tmp_path: Path):
    out_a = tmp_path / "out_a"
    out_b = tmp_path / "out_b"
    exporter.export_public_snapshot(tmp_db, out_a, tmp_path)
    exporter.export_public_snapshot(tmp_db, out_b, tmp_path)

    for table in ("family_members", "family_affect", "family_knowledge"):
        bytes_a = (out_a / f"{table}.json").read_bytes()
        bytes_b = (out_b / f"{table}.json").read_bytes()
        assert bytes_a == bytes_b, f"snapshot for {table} not stable across runs"


# ---------------------------------------------------------------------------
# Property 5 — Manifest with source SHA and allowlist
# ---------------------------------------------------------------------------


def test_manifest_contains_required_fields(tmp_db: Path, tmp_path: Path):
    out_dir = tmp_path / "out"
    exporter.export_public_snapshot(tmp_db, out_dir, tmp_path)
    manifest = json.loads((out_dir / "manifest.json").read_text())
    for required in (
        "exported_at_unix",
        "source_db",
        "source_git_sha",  # may be None in non-git contexts, but key must exist
        "reviewed_tables_allowlist",
        "exported",
        "omitted",
        "held_unreviewed_tables_present_in_db",
        "schema_version",
    ):
        assert required in manifest, f"manifest missing {required}"


def test_manifest_allowlist_matches_module_constant(tmp_db: Path, tmp_path: Path):
    out_dir = tmp_path / "out"
    exporter.export_public_snapshot(tmp_db, out_dir, tmp_path)
    manifest = json.loads((out_dir / "manifest.json").read_text())
    assert set(manifest["reviewed_tables_allowlist"]) == set(exporter.REVIEWED_TABLES)


# ---------------------------------------------------------------------------
# Edge cases — fail-soft direction
# ---------------------------------------------------------------------------


def test_missing_db_returns_fatal_code(tmp_path: Path):
    rc = exporter.export_public_snapshot(tmp_path / "does-not-exist.db", tmp_path / "out", tmp_path)
    assert rc == 2


def test_table_in_allowlist_but_absent_in_db_is_silently_skipped(tmp_path: Path):
    """family.db doesn't have ALL reviewed tables yet — silent skip is fine,
    NOT an error. Only the present-and-reviewed subset gets exported."""
    db_path = tmp_path / "minimal.db"
    conn = sqlite3.connect(db_path)
    conn.executescript("CREATE TABLE family_members (entity_id TEXT PRIMARY KEY, name TEXT);")
    conn.execute("INSERT INTO family_members VALUES ('e1', 'Aether')")
    conn.commit()
    conn.close()

    out_dir = tmp_path / "out"
    rc = exporter.export_public_snapshot(db_path, out_dir, tmp_path)
    assert rc == 0

    manifest = json.loads((out_dir / "manifest.json").read_text())
    assert "family_members" in manifest["exported"]
    # tables in allowlist but not in DB are NOT in exported and NOT in omitted
    assert "family_affect" not in manifest["exported"]
    assert "family_affect" not in manifest["omitted"]


def test_non_text_values_pass_through_scrub_unchanged():
    """Numeric, None, and bool values must pass through the scrubber
    unchanged — only strings get pattern-matched."""
    assert exporter._scrub(42) == 42
    assert exporter._scrub(3.14) == 3.14
    assert exporter._scrub(None) is None
    assert exporter._scrub(True) is True
