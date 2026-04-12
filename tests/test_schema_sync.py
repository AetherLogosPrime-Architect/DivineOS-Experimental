"""Schema sync test — catch divergence between production and test schemas.

The 280-failure incident proved that tests can pass while the system is
fundamentally broken because test fixtures created schemas that didn't
match production. This test prevents that from happening again.

It initializes a database through the PRODUCTION init path, captures every
table's columns, then verifies that any test file with inline CREATE TABLE
statements produces a compatible schema.
"""

import re
import sqlite3
from pathlib import Path

import pytest


def _get_production_schema(db_path: str) -> dict[str, list[str]]:
    """Initialize a DB through all production init functions, return column names per table."""
    import os

    os.environ["DIVINEOS_DB"] = db_path

    # Clear any cached connections/paths
    from divineos.core import ledger as ledger_mod

    if hasattr(ledger_mod, "_DB_PATH"):
        ledger_mod._DB_PATH = None

    # Call ALL production init functions in dependency order
    from divineos.core.ledger import init_db

    init_db()

    from divineos.core.knowledge._base import init_knowledge_table

    init_knowledge_table()

    from divineos.core.memory import init_memory_tables

    init_memory_tables()

    from divineos.core.knowledge.edges import init_edge_table

    init_edge_table()

    from divineos.core.affect import init_affect_log

    init_affect_log()

    from divineos.core.moral_compass import init_compass

    init_compass()

    from divineos.core.decision_journal import init_decision_journal

    init_decision_journal()

    from divineos.core.claim_store import init_claim_tables

    init_claim_tables()

    from divineos.core.opinion_store import init_opinion_table

    init_opinion_table()

    from divineos.core.user_model import init_user_model_table

    init_user_model_table()

    from divineos.core.self_critique import init_critique_table

    init_critique_table()

    from divineos.core.advice_tracking import init_advice_table

    init_advice_table()

    from divineos.core.user_ratings import init_ratings_table

    init_ratings_table()

    from divineos.core.growth import init_session_history_table

    init_session_history_table()

    from divineos.core.tone_texture import init_tone_texture_table

    init_tone_texture_table()

    from divineos.core.affect_calibration import init_calibration_table

    init_calibration_table()

    from divineos.core.questions import init_questions_table

    init_questions_table()

    from divineos.core.knowledge.relationships import init_relationship_table

    init_relationship_table()

    from divineos.core.knowledge.temporal import init_temporal_columns

    init_temporal_columns()

    from divineos.core.knowledge_impact import init_impact_table

    init_impact_table()

    from divineos.core.external_validation import init_validation_table

    init_validation_table()

    from divineos.core.logic.warrants import init_warrant_table

    init_warrant_table()

    from divineos.core.logic.logic_reasoning import init_relation_table

    init_relation_table()

    from divineos.core.dead_architecture_alarm import init_alarm_table

    init_alarm_table()

    # Now read the schema
    conn = sqlite3.connect(db_path)
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()

    schema: dict[str, list[str]] = {}
    for (table_name,) in tables:
        cols = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        schema[table_name] = [col[1] for col in cols]  # col[1] = column name

    conn.close()
    return schema


def _extract_inline_schemas(test_dir: Path) -> dict[str, dict[str, list[str]]]:
    """Find all inline CREATE TABLE statements in test files.

    Returns {filename: {table_name: [columns]}}.
    """
    pattern = re.compile(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\s*\((.*?)\)",
        re.DOTALL | re.IGNORECASE,
    )
    col_pattern = re.compile(r"^\s*(\w+)\s+\w+", re.MULTILINE)

    results: dict[str, dict[str, list[str]]] = {}

    for test_file in sorted(test_dir.glob("test_*.py")):
        content = test_file.read_text(encoding="utf-8")
        matches = pattern.findall(content)
        if not matches:
            continue

        file_tables: dict[str, list[str]] = {}
        for table_name, body in matches:
            # Extract column names from the CREATE TABLE body
            cols = []
            for line in body.split(","):
                line = line.strip()
                if not line:
                    continue
                # Skip constraints (PRIMARY KEY, FOREIGN KEY, UNIQUE, CHECK)
                if re.match(
                    r"(?:PRIMARY|FOREIGN|UNIQUE|CHECK|CREATE|CONSTRAINT)\s",
                    line,
                    re.IGNORECASE,
                ):
                    continue
                col_match = col_pattern.match(line)
                if col_match:
                    cols.append(col_match.group(1))
            if cols:
                file_tables[table_name] = cols

        if file_tables:
            results[test_file.name] = file_tables

    return results


class TestSchemaSync:
    """Production schema matches what tests assume."""

    def test_production_init_creates_core_tables(self, tmp_path: Path) -> None:
        """All core tables exist after production init."""
        db_path = str(tmp_path / "schema_test.db")
        schema = _get_production_schema(db_path)

        core_tables = {
            "system_events",
            "knowledge",
            "core_memory",
            "active_memory",
            "knowledge_edges",
            "lesson_tracking",
            "compass_observation",
            "affect_log",
        }
        missing = core_tables - set(schema.keys())
        assert not missing, f"Missing core tables: {missing}"

    def test_knowledge_table_has_all_columns(self, tmp_path: Path) -> None:
        """Knowledge table has every column the codebase expects."""
        db_path = str(tmp_path / "schema_test.db")
        schema = _get_production_schema(db_path)

        expected_cols = {
            "knowledge_id",
            "created_at",
            "updated_at",
            "knowledge_type",
            "content",
            "confidence",
            "source_events",
            "tags",
            "access_count",
            "content_hash",
            "superseded_by",
            "corroboration_count",
            "contradiction_count",
            "source",
            "maturity",
        }
        actual_cols = set(schema.get("knowledge", []))
        missing = expected_cols - actual_cols
        assert not missing, f"Knowledge table missing columns: {missing}"

    def test_lesson_tracking_has_all_columns(self, tmp_path: Path) -> None:
        """Lesson tracking has every column — this is the table tests most often recreate inline."""
        db_path = str(tmp_path / "schema_test.db")
        schema = _get_production_schema(db_path)

        expected_cols = {
            "lesson_id",
            "created_at",
            "category",
            "description",
            "first_session",
            "occurrences",
            "last_seen",
            "sessions",
            "status",
            "content_hash",
            "agent",
        }
        actual_cols = set(schema.get("lesson_tracking", []))
        missing = expected_cols - actual_cols
        assert not missing, f"lesson_tracking missing columns: {missing}"

    def test_inline_schemas_are_subsets_of_production(self, tmp_path: Path) -> None:
        """Every inline CREATE TABLE in test files uses columns that exist in production.

        This catches the reverse problem — test creates columns that production doesn't have.
        """
        db_path = str(tmp_path / "schema_test.db")
        prod_schema = _get_production_schema(db_path)
        test_dir = Path(__file__).parent
        inline_schemas = _extract_inline_schemas(test_dir)

        violations: list[str] = []
        for filename, tables in inline_schemas.items():
            for table_name, test_cols in tables.items():
                if table_name not in prod_schema:
                    # Table might be test-only (e.g., temporary fixture)
                    continue
                prod_cols = set(prod_schema[table_name])
                extra = set(test_cols) - prod_cols
                if extra:
                    violations.append(
                        f"{filename}: {table_name} has columns {extra} not in production"
                    )

        assert not violations, "Test inline schemas have columns not in production:\n" + "\n".join(
            f"  - {v}" for v in violations
        )

    def test_inline_schemas_not_missing_critical_columns(self, tmp_path: Path) -> None:
        """Inline CREATE TABLE statements don't omit critical columns.

        This is the 280-failure scenario: test creates a table with fewer columns
        than production, so tests pass against a simpler schema than reality.
        """
        db_path = str(tmp_path / "schema_test.db")
        prod_schema = _get_production_schema(db_path)
        test_dir = Path(__file__).parent
        inline_schemas = _extract_inline_schemas(test_dir)

        warnings: list[str] = []
        for filename, tables in inline_schemas.items():
            for table_name, test_cols in tables.items():
                if table_name not in prod_schema:
                    continue
                prod_cols = set(prod_schema[table_name])
                missing = prod_cols - set(test_cols)
                if missing:
                    warnings.append(
                        f"{filename}: {table_name} missing {len(missing)} columns: "
                        f"{sorted(missing)}"
                    )

        if warnings:
            pytest.fail(
                "Tests create tables with fewer columns than production — "
                "these tests may pass against a simpler schema than reality:\n"
                + "\n".join(f"  - {w}" for w in warnings)
            )
