"""Regression-pin tests for Aletheia round-3 Findings 45 and 46.

Finding 45: archive_export.export_principles partitions by source
(Curated vs Auto-Extracted Correction-Pair Entries). The fix from
Finding 44 was not structurally pinned — only the file-existence
test ran. If a future refactor collapsed the partition back to a
single list, no test would catch it. This file pins the partition.

Finding 46: KNOWLEDGE_SOURCES was named-as-whitelist but not
enforced. CURATED_FROM_CORRECTED entered usage without registration.
Fix: register CURATED_FROM_CORRECTED in the set AND add
validate_source() called from store_knowledge. This file pins both
behaviors — set membership and write-time rejection of unknown
values.
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest


# --- Finding 45: partition regression-pin --------------------------------


def _seed_minimal_knowledge_db(conn: sqlite3.Connection) -> None:
    """Create a knowledge table matching what ``export_principles`` reads.

    NOTE: ``archive_export.export_principles`` reads columns ``maturity``
    and ``source`` which are NOT in the current production ``knowledge``
    schema (filed as schema-drift claim). This test reflects the schema
    export_principles SELECTs from, not the production-canonical shape.
    Schema-sync drift between archive_export and the live schema is a
    separate concern — see schema-sync-test-exemption comments below.
    """
    # schema-sync-test-exemption: archive-export reads legacy columns
    conn.execute(
        """
        CREATE TABLE knowledge (
            knowledge_id TEXT PRIMARY KEY,
            created_at REAL,
            knowledge_type TEXT,
            content TEXT,
            confidence REAL,
            access_count INTEGER,
            maturity TEXT,
            source TEXT,
            superseded_by TEXT
        )
        """
    )


def test_export_principles_partitions_by_source() -> None:
    """LOAD-BEARING: source='CORRECTED' entries land in the Auto-
    Extracted section; everything else lands in Curated. Pins the
    Finding 44 class-fix structurally."""
    from divineos.core.archive_export import export_principles

    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp)
        conn = sqlite3.connect(":memory:")
        _seed_minimal_knowledge_db(conn)
        conn.execute(
            "INSERT INTO knowledge VALUES (?, ?, 'PRINCIPLE', ?, 0.8, 5, 'TESTED', ?, NULL)",
            ("kid-corrected-001", 1000.0, "Correction-pair principle alpha", "CORRECTED"),
        )
        conn.execute(
            "INSERT INTO knowledge VALUES (?, ?, 'PRINCIPLE', ?, 0.8, 5, 'TESTED', ?, NULL)",
            ("kid-stated-001", 2000.0, "Stated principle beta", "STATED"),
        )
        conn.execute(
            "INSERT INTO knowledge VALUES (?, ?, 'PRINCIPLE', ?, 0.8, 5, 'TESTED', ?, NULL)",
            ("kid-curated-001", 3000.0, "Curated principle gamma", "CURATED_FROM_CORRECTED"),
        )
        conn.commit()

        n = export_principles(conn, dest)
        assert n == 3

        content = (dest / "principles.md").read_text(encoding="utf-8")

        # Two sections must exist
        assert "## Curated Principles" in content
        assert "## Auto-Extracted Correction-Pair Entries" in content

        curated_section, _, auto_section = content.partition(
            "## Auto-Extracted Correction-Pair Entries"
        )
        # CORRECTED lands in auto section
        assert "Correction-pair principle alpha" in auto_section, (
            "source='CORRECTED' entry should land in Auto-Extracted section"
        )
        assert "Correction-pair principle alpha" not in curated_section, (
            "source='CORRECTED' must not appear in Curated section"
        )
        # STATED lands in curated section
        assert "Stated principle beta" in curated_section, (
            "source='STATED' entry should land in Curated section"
        )
        # CURATED_FROM_CORRECTED is curated (the cleaned-up state),
        # not auto-extracted
        assert "Curated principle gamma" in curated_section, (
            "source='CURATED_FROM_CORRECTED' should land in Curated, not Auto-Extracted"
        )
        # Lower-epistemic warning is present
        assert "lower-epistemic" in content.lower() or "lower epistemic" in content.lower()


# --- Finding 46: KNOWLEDGE_SOURCES enforcement --------------------------


def test_curated_from_corrected_in_canonical_set() -> None:
    """The cleaned-correction state is registered as a canonical source."""
    from divineos.core.knowledge._base import KNOWLEDGE_SOURCES

    assert "CURATED_FROM_CORRECTED" in KNOWLEDGE_SOURCES


def test_validate_source_permits_canonical_values() -> None:
    """Every canonical source value passes validate_source."""
    from divineos.core.knowledge._base import KNOWLEDGE_SOURCES, validate_source

    for src in KNOWLEDGE_SOURCES:
        validate_source(src)  # must not raise


def test_validate_source_permits_none_or_empty() -> None:
    """None and empty string are tolerated — "unknown source" is OK."""
    from divineos.core.knowledge._base import validate_source

    validate_source(None)
    validate_source("")


def test_validate_source_rejects_unknown_value() -> None:
    """Drift-class values raise ValueError. The constraint named by
    the docstring is now enforced at write-time."""
    from divineos.core.knowledge._base import validate_source

    with pytest.raises(ValueError, match="Unknown knowledge source"):
        validate_source("MADE_UP_VALUE")


def test_store_knowledge_rejects_unknown_source() -> None:
    """The validate_source call is wired into the write path —
    store_knowledge raises when a caller passes a non-canonical
    source. Catches the regression where CURATED_FROM_CORRECTED-
    class drift entered the codebase without registration."""
    from divineos.core.knowledge.crud import store_knowledge

    with pytest.raises(ValueError, match="Unknown knowledge source"):
        store_knowledge(
            knowledge_type="PRINCIPLE",
            content="Testing rejection of unknown source value at write-time.",
            source="NOT_A_REAL_SOURCE",
        )
