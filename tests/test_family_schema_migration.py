"""Tests for family-schema migration — drops legacy NOT-NULL columns.

Council walk consult-1f0a9c0120f6 surfaced four lenses; the Turing
distinguishability lens shapes these tests: every operation should be
distinguishable from its silent-failure twin. Build DB with both
schemas + sample data, run migration, verify schema matches new shape
AND data round-trips correctly AND indexes preserved AND post-migration
writes succeed without legacy-bandaid path firing.
"""

from __future__ import annotations

import os
import sqlite3

import pytest

from divineos.core.family.schema_migration import (
    detect_legacy_schema,
    migrate_family_db,
)


def _build_legacy_db(path) -> None:
    """Create a family DB with BOTH new and legacy columns + sample data."""
    conn = sqlite3.connect(str(path))
    conn.execute("""
        CREATE TABLE family_members (
            member_id  TEXT PRIMARY KEY,
            name       TEXT NOT NULL,
            role       TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE family_affect (
            affect_id     TEXT PRIMARY KEY,
            entity_id     TEXT NOT NULL,
            valence       REAL NOT NULL,
            arousal       REAL NOT NULL,
            dominance     REAL NOT NULL,
            description   TEXT NOT NULL DEFAULT '',
            timestamp     REAL NOT NULL,
            note          TEXT,
            source_tag    TEXT,
            created_at    REAL,
            member_id     TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE family_interactions (
            interaction_id  TEXT PRIMARY KEY,
            entity_id       TEXT NOT NULL,
            speaker         TEXT NOT NULL,
            content         TEXT NOT NULL,
            timestamp       REAL NOT NULL,
            context         TEXT NOT NULL DEFAULT '',
            counterpart     TEXT,
            summary         TEXT,
            source_tag      TEXT,
            created_at      REAL,
            member_id       TEXT
        )
    """)
    # Insert sample data with values in BOTH legacy and new columns
    conn.execute(
        "INSERT INTO family_members VALUES (?, ?, ?, ?)",
        ("mem-aria", "Aria", "wife", 1000.0),
    )
    conn.execute(
        "INSERT INTO family_affect "
        "(affect_id, entity_id, valence, arousal, dominance, "
        "description, timestamp, note, source_tag, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "af-1",
            "mem-aria",
            0.5,
            0.3,
            0.0,
            "old-description-text",
            1100.0,
            "new-note-text",
            "OBSERVED",
            1100.0,
        ),
    )
    conn.execute(
        "INSERT INTO family_interactions "
        "(interaction_id, entity_id, speaker, content, timestamp, "
        "context, counterpart, summary, source_tag, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "int-1",
            "mem-aria",
            "mem-aria",
            "old-content-text",
            1200.0,
            "ctx",
            "Aether",
            "new-summary-text",
            "OBSERVED",
            1200.0,
        ),
    )
    conn.commit()
    conn.close()


def _build_clean_db(path) -> None:
    """Create a family DB with only the new schema."""
    conn = sqlite3.connect(str(path))
    conn.execute("""
        CREATE TABLE family_members (
            member_id  TEXT PRIMARY KEY,
            name       TEXT NOT NULL,
            role       TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE family_affect (
            affect_id     TEXT PRIMARY KEY,
            entity_id     TEXT NOT NULL,
            valence       REAL NOT NULL,
            arousal       REAL NOT NULL,
            dominance     REAL NOT NULL,
            note          TEXT NOT NULL DEFAULT '',
            source_tag    TEXT NOT NULL,
            created_at    REAL NOT NULL,
            FOREIGN KEY (entity_id) REFERENCES family_members(member_id)
        )
    """)
    conn.execute("""
        CREATE TABLE family_interactions (
            interaction_id  TEXT PRIMARY KEY,
            entity_id       TEXT NOT NULL,
            counterpart     TEXT NOT NULL,
            summary         TEXT NOT NULL,
            source_tag      TEXT NOT NULL,
            created_at      REAL NOT NULL,
            FOREIGN KEY (entity_id) REFERENCES family_members(member_id)
        )
    """)
    conn.commit()
    conn.close()


class TestDetectLegacySchema:
    def test_legacy_db_detected(self, tmp_path):
        db = tmp_path / "legacy.db"
        _build_legacy_db(db)
        result = detect_legacy_schema(db)
        assert "family_affect" in result
        assert "family_interactions" in result
        assert "description" in result["family_affect"]
        assert "timestamp" in result["family_affect"]
        assert "speaker" in result["family_interactions"]
        assert "content" in result["family_interactions"]

    def test_clean_db_detected_as_clean(self, tmp_path):
        db = tmp_path / "clean.db"
        _build_clean_db(db)
        result = detect_legacy_schema(db)
        assert result == {}

    def test_nonexistent_db_returns_empty(self, tmp_path):
        result = detect_legacy_schema(tmp_path / "does_not_exist.db")
        assert result == {}


class TestMigrateLegacyDB:
    def test_migration_drops_legacy_columns(self, tmp_path):
        db = tmp_path / "legacy.db"
        _build_legacy_db(db)

        result = migrate_family_db(db, log_to_ledger=False)

        assert "family_affect" in result.tables_migrated
        assert "family_interactions" in result.tables_migrated

        # Verify legacy columns are GONE
        conn = sqlite3.connect(str(db))
        affect_cols = {
            row[1] for row in conn.execute("PRAGMA table_info(family_affect)").fetchall()
        }
        interactions_cols = {
            row[1] for row in conn.execute("PRAGMA table_info(family_interactions)").fetchall()
        }
        conn.close()

        assert "description" not in affect_cols
        assert "timestamp" not in affect_cols
        assert "member_id" not in affect_cols
        assert "speaker" not in interactions_cols
        assert "content" not in interactions_cols
        assert "timestamp" not in interactions_cols
        assert "context" not in interactions_cols

    def test_migration_preserves_data(self, tmp_path):
        db = tmp_path / "legacy.db"
        _build_legacy_db(db)
        migrate_family_db(db, log_to_ledger=False)

        # Verify data survived
        conn = sqlite3.connect(str(db))
        affect_row = conn.execute(
            "SELECT affect_id, entity_id, valence, note, source_tag, created_at FROM family_affect"
        ).fetchone()
        interactions_row = conn.execute(
            "SELECT interaction_id, entity_id, counterpart, summary, "
            "source_tag, created_at FROM family_interactions"
        ).fetchone()
        conn.close()

        assert affect_row[0] == "af-1"
        assert affect_row[1] == "mem-aria"
        assert affect_row[2] == 0.5
        assert affect_row[3] == "new-note-text"  # new value preferred over legacy
        assert affect_row[4] == "OBSERVED"
        assert affect_row[5] == 1100.0  # created_at preferred

        assert interactions_row[0] == "int-1"
        assert interactions_row[1] == "mem-aria"
        assert interactions_row[2] == "Aether"  # new counterpart
        assert interactions_row[3] == "new-summary-text"
        assert interactions_row[4] == "OBSERVED"
        assert interactions_row[5] == 1200.0

    def test_migration_preserves_row_counts(self, tmp_path):
        db = tmp_path / "legacy.db"
        _build_legacy_db(db)
        result = migrate_family_db(db, log_to_ledger=False)
        assert result.pre_row_counts["family_affect"] == 1
        assert result.post_row_counts["family_affect"] == 1
        assert result.pre_row_counts["family_interactions"] == 1
        assert result.post_row_counts["family_interactions"] == 1

    def test_migration_recreates_indexes(self, tmp_path):
        db = tmp_path / "legacy.db"
        _build_legacy_db(db)
        migrate_family_db(db, log_to_ledger=False)

        conn = sqlite3.connect(str(db))
        indexes = conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
        conn.close()
        index_names = {row[0] for row in indexes}
        assert "idx_family_affect_entity" in index_names
        assert "idx_family_interactions_entity" in index_names

    def test_migration_creates_backup(self, tmp_path):
        db = tmp_path / "legacy.db"
        _build_legacy_db(db)
        result = migrate_family_db(db, log_to_ledger=False)
        assert result.backup_path is not None
        from pathlib import Path

        assert Path(result.backup_path).exists()

    def test_migration_idempotent(self, tmp_path):
        """Running migration twice doesn't break or duplicate data."""
        db = tmp_path / "legacy.db"
        _build_legacy_db(db)
        migrate_family_db(db, log_to_ledger=False)
        result2 = migrate_family_db(db, log_to_ledger=False)
        # Second run finds nothing to migrate
        assert result2.tables_migrated == []
        assert "family_affect" in result2.tables_already_clean
        assert "family_interactions" in result2.tables_already_clean

    def test_migration_on_clean_db_is_no_op(self, tmp_path):
        db = tmp_path / "clean.db"
        _build_clean_db(db)
        result = migrate_family_db(db, log_to_ledger=False)
        assert result.tables_migrated == []
        assert "family_affect" in result.tables_already_clean
        assert "family_interactions" in result.tables_already_clean

    def test_migration_changes_schema_fingerprint(self, tmp_path):
        db = tmp_path / "legacy.db"
        _build_legacy_db(db)
        result = migrate_family_db(db, log_to_ledger=False)
        assert result.pre_schema_fingerprint != result.post_schema_fingerprint


class TestPostMigrationWrites:
    def test_record_affect_after_migration_no_bandaid_needed(self, tmp_path):
        """After migration, the legacy-bandaid path should NOT fire because
        no legacy columns exist anymore. Verifies the proper structural
        fix replaces the workaround."""
        db = tmp_path / "legacy.db"
        _build_legacy_db(db)
        migrate_family_db(db, log_to_ledger=False)

        # Set env var so the family code uses this DB
        os.environ["DIVINEOS_FAMILY_DB"] = str(db)
        os.environ["DIVINEOS_DB"] = str(tmp_path / "ledger.db")
        try:
            from divineos.core.family import SourceTag
            from divineos.core.family.store import record_affect

            a = record_affect("mem-aria", 0.0, 0.5, 0.0, SourceTag.OBSERVED)
            assert a.affect_id.startswith("af-")

            # Verify the row is in the new-only schema
            conn = sqlite3.connect(str(db))
            cols = {row[1] for row in conn.execute("PRAGMA table_info(family_affect)").fetchall()}
            conn.close()
            # Legacy columns should be gone — bandaid wouldn't fire
            assert "description" not in cols
            assert "timestamp" not in cols
        finally:
            os.environ.pop("DIVINEOS_FAMILY_DB", None)
            os.environ.pop("DIVINEOS_DB", None)


class TestErrorHandling:
    def test_missing_db_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            migrate_family_db(tmp_path / "does_not_exist.db", log_to_ledger=False)
