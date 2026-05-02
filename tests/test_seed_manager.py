"""Tests for seed versioning and validation."""

import os

from divineos.core.knowledge import init_knowledge_table
from divineos.core.ledger import init_db
from divineos.core.memory import init_memory_tables
from divineos.core.seed_manager import (
    apply_seed,
    get_applied_seed_version,
    reclassify_seed_as_inherited,
    restore_inherited_confidence,
    set_applied_seed_version,
    should_reseed,
    validate_seed,
)


class TestValidateSeed:
    def test_valid_seed(self):
        seed = {
            "version": "1.0.0",
            "core_memory": {
                "user_identity": "test user",
                "project_purpose": "test project",
            },
            "knowledge": [
                {"type": "FACT", "content": "Test fact about the system"},
            ],
            "lessons": [
                {"category": "testing"},
            ],
        }
        errors = validate_seed(seed)
        assert errors == []

    def test_missing_version(self):
        seed = {
            "core_memory": {"user_identity": "test", "project_purpose": "test"},
            "knowledge": [],
        }
        errors = validate_seed(seed)
        assert any("version" in e for e in errors)

    def test_missing_required_core_slots(self):
        seed = {
            "version": "1.0.0",
            "core_memory": {"user_identity": "test"},
            "knowledge": [],
        }
        errors = validate_seed(seed)
        assert any("project_purpose" in e for e in errors)

    def test_empty_content(self):
        seed = {
            "version": "1.0.0",
            "core_memory": {"user_identity": "test", "project_purpose": "test"},
            "knowledge": [{"type": "FACT", "content": "  "}],
        }
        errors = validate_seed(seed)
        assert any("empty content" in e for e in errors)

    def test_missing_knowledge_type(self):
        seed = {
            "version": "1.0.0",
            "core_memory": {"user_identity": "test", "project_purpose": "test"},
            "knowledge": [{"content": "No type field here"}],
        }
        errors = validate_seed(seed)
        assert any("type" in e for e in errors)

    def test_not_a_dict(self):
        errors = validate_seed("not a dict")
        assert errors == ["Seed data must be a dict"]


class TestShouldReseed:
    def test_no_current_version(self):
        assert should_reseed(None, "1.0.0") is True

    def test_same_version(self):
        assert should_reseed("1.0.0", "1.0.0") is False

    def test_newer_seed(self):
        assert should_reseed("1.0.0", "1.1.0") is True

    def test_older_seed(self):
        assert should_reseed("2.0.0", "1.0.0") is False

    def test_patch_bump(self):
        assert should_reseed("1.0.0", "1.0.1") is True


class TestSeedVersionTracking:
    def test_set_and_get_version(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()

            assert get_applied_seed_version() is None

            set_applied_seed_version("1.0.0")
            assert get_applied_seed_version() == "1.0.0"

            set_applied_seed_version("1.1.0")
            assert get_applied_seed_version() == "1.1.0"
        finally:
            os.environ.pop("DIVINEOS_DB", None)


class TestApplySeed:
    def test_merge_mode_skips_existing(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()
            init_memory_tables()

            seed = {
                "version": "1.0.0",
                "core_memory": {
                    "user_identity": "test user identity for the seed system",
                    "project_purpose": "test project purpose for validation",
                },
                "knowledge": [
                    {"type": "FACT", "content": "First fact about the seed system"},
                    {"type": "FACT", "content": "Second fact about the seed system"},
                ],
                "lessons": [],
            }

            # First apply
            counts1 = apply_seed(seed, mode="merge")
            assert counts1["knowledge"] == 2
            assert counts1["skipped"] == 0

            # Second apply — should skip existing
            counts2 = apply_seed(seed, mode="merge")
            assert counts2["skipped"] == 2
            assert counts2["knowledge"] == 0
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_merge_preserves_existing_filled_core_slot(self, tmp_path):
        """Merge mode must not overwrite a lived-in identity slot.

        Scenario: the seed ships a TEMPLATE placeholder for my_identity.
        The running DB already has real content (an AI grew into it over
        time). Re-applying the seed in merge mode should skip that slot,
        not clobber it with the placeholder.
        """
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()
            init_memory_tables()

            from divineos.core.memory import get_core, set_core

            # An AI has already filled my_identity with real content
            real_identity = "I am a specific agent with a name, values, and a voice that is mine."
            set_core("my_identity", real_identity)

            # Seed ships a TEMPLATE placeholder for that same slot
            seed = {
                "version": "2.1.0",
                "core_memory": {
                    "user_identity": "a user identity string to seed",
                    "project_purpose": "a project purpose string to seed",
                    "my_identity": "[TEMPLATE — fill this in as you come to know yourself.]",
                },
                "knowledge": [],
                "lessons": [],
            }

            counts = apply_seed(seed, mode="merge")

            # my_identity was already filled — skipped, not overwritten
            current = get_core()
            assert current["my_identity"] == real_identity
            assert counts["core_slots_skipped"] >= 1

            # Empty slots still got filled
            assert current["user_identity"] == "a user identity string to seed"
            assert current["project_purpose"] == "a project purpose string to seed"
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_merge_fills_empty_core_slots(self, tmp_path):
        """On a fresh DB, merge mode should still populate empty slots from seed."""
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()
            init_memory_tables()

            seed = {
                "version": "1.0.0",
                "core_memory": {
                    "user_identity": "fresh user identity from seed",
                    "project_purpose": "fresh project purpose from seed",
                },
                "knowledge": [],
                "lessons": [],
            }
            counts = apply_seed(seed, mode="merge")
            assert counts["core_slots"] == 2

            from divineos.core.memory import get_core

            current = get_core()
            assert current["user_identity"] == "fresh user identity from seed"
            assert current["project_purpose"] == "fresh project purpose from seed"
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_full_mode_overwrites_existing_slots(self, tmp_path):
        """Full mode (explicit re-seed) still overwrites — that's the escape hatch."""
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()
            init_memory_tables()

            from divineos.core.memory import get_core, set_core

            set_core("my_identity", "old identity content already in place")

            seed = {
                "version": "1.0.0",
                "core_memory": {
                    "user_identity": "user identity from seed",
                    "project_purpose": "project purpose from seed",
                    "my_identity": "new identity content from the seed",
                },
                "knowledge": [],
                "lessons": [],
            }
            apply_seed(seed, mode="full")

            current = get_core()
            assert current["my_identity"] == "new identity content from the seed"
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_records_version(self, tmp_path):
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()
            init_memory_tables()

            seed = {
                "version": "1.2.3",
                "core_memory": {
                    "user_identity": "version tracking test user",
                    "project_purpose": "version tracking test project",
                },
                "knowledge": [],
                "lessons": [],
            }
            apply_seed(seed)
            assert get_applied_seed_version() == "1.2.3"
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_merge_skips_superseded_entries(self, tmp_path):
        """Seed should NOT resurrect knowledge that was previously superseded."""
        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()
            init_memory_tables()

            seed = {
                "version": "1.0.0",
                "core_memory": {
                    "user_identity": "test identity for resurrection check",
                    "project_purpose": "test purpose for resurrection check",
                },
                "knowledge": [
                    {"type": "FACT", "content": "This fact will be superseded"},
                    {"type": "FACT", "content": "This fact stays active"},
                ],
                "lessons": [],
            }

            # First apply — both entries created
            counts1 = apply_seed(seed, mode="merge")
            assert counts1["knowledge"] == 2

            # Supersede the first entry
            from divineos.core.knowledge import get_knowledge, supersede_knowledge

            entries = get_knowledge(knowledge_type="FACT")
            superseded_entry = [e for e in entries if "will be superseded" in e["content"]][0]
            supersede_knowledge(superseded_entry["knowledge_id"], reason="test")

            # Re-apply seed — the superseded entry should NOT come back
            counts2 = apply_seed(seed, mode="merge")
            assert counts2["skipped"] == 2  # both skipped (1 active, 1 superseded)
            assert counts2["knowledge"] == 0

            # Verify only 1 active FACT remains
            active = get_knowledge(knowledge_type="FACT")
            assert len(active) == 1
            assert "stays active" in active[0]["content"]
        finally:
            os.environ.pop("DIVINEOS_DB", None)


class TestSeedSourceClassification:
    """Seed entries must land as INHERITED, not STATED.

    Before the fix: apply_seed called store_knowledge without a source
    arg, so every seed entry defaulted to STATED ('told by user'). This
    polluted the epistemic reporter — seed data showed up as if the
    user had told me each thing this session. Fix: default to INHERITED,
    honor explicit source if specified.
    """

    def test_seed_entries_stored_as_inherited_by_default(self, tmp_path):
        from divineos.core.knowledge import _get_connection

        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()
            init_memory_tables()

            seed = {
                "version": "1.0.0",
                "core_memory": {
                    "user_identity": "test identity for source classification",
                    "project_purpose": "test purpose for source classification",
                },
                "knowledge": [
                    {"type": "FACT", "content": "Inherited fact one about seed"},
                    {"type": "FACT", "content": "Inherited fact two about seed"},
                ],
                "lessons": [],
            }
            apply_seed(seed, mode="merge")

            conn = _get_connection()
            try:
                rows = conn.execute(
                    "SELECT source FROM knowledge WHERE superseded_by IS NULL"
                ).fetchall()
            finally:
                conn.close()

            sources = [r[0] for r in rows]
            assert sources, "seed should have created entries"
            assert all(s == "INHERITED" for s in sources), (
                f"every seed entry must land as INHERITED; got {sources}"
            )
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_seed_entries_honor_explicit_source(self, tmp_path):
        """If a seed entry explicitly specifies source, don't override it."""
        from divineos.core.knowledge import _get_connection

        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()
            init_memory_tables()

            seed = {
                "version": "1.0.0",
                "core_memory": {
                    "user_identity": "test identity for explicit source honor",
                    "project_purpose": "test purpose for explicit source honor",
                },
                "knowledge": [
                    {
                        "type": "FACT",
                        "content": "Observed fact that shipped corroborated",
                        "source": "DEMONSTRATED",
                    },
                ],
                "lessons": [],
            }
            apply_seed(seed, mode="merge")

            conn = _get_connection()
            try:
                row = conn.execute(
                    "SELECT source FROM knowledge WHERE superseded_by IS NULL"
                ).fetchone()
            finally:
                conn.close()

            assert row[0] == "DEMONSTRATED", "explicit source in seed entry must be honored"
        finally:
            os.environ.pop("DIVINEOS_DB", None)


class TestReclassifySeedMigration:
    """Migration: fix legacy STATED seed entries to INHERITED."""

    def test_reclassifies_matching_stated_entries(self, tmp_path):
        from divineos.core.knowledge import _get_connection, store_knowledge

        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()
            init_memory_tables()

            # Simulate a legacy seed load (source defaulted to STATED)
            store_knowledge(
                knowledge_type="FACT",
                content="Legacy seed fact one",
                source="STATED",
            )
            store_knowledge(
                knowledge_type="FACT",
                content="Legacy seed fact two",
                source="STATED",
            )
            # And a non-seed STATED entry that should NOT be touched
            store_knowledge(
                knowledge_type="FACT",
                content="User-told fact never in seed",
                source="STATED",
            )

            seed_data = {
                "knowledge": [
                    {"type": "FACT", "content": "Legacy seed fact one"},
                    {"type": "FACT", "content": "Legacy seed fact two"},
                ],
            }
            counts = reclassify_seed_as_inherited(seed_data)

            assert counts["reclassified"] == 2
            assert counts["not_seed"] == 1

            conn = _get_connection()
            try:
                rows = conn.execute(
                    "SELECT content, source FROM knowledge WHERE superseded_by IS NULL"
                ).fetchall()
            finally:
                conn.close()

            by_content = {r[0]: r[1] for r in rows}
            assert by_content["Legacy seed fact one"] == "INHERITED"
            assert by_content["Legacy seed fact two"] == "INHERITED"
            # The non-seed user-told fact stays STATED
            assert by_content["User-told fact never in seed"] == "STATED"
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_is_idempotent(self, tmp_path):
        from divineos.core.knowledge import store_knowledge

        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()
            init_memory_tables()

            store_knowledge(
                knowledge_type="FACT",
                content="Some seed fact",
                source="STATED",
            )
            seed_data = {
                "knowledge": [
                    {"type": "FACT", "content": "Some seed fact"},
                ],
            }
            first = reclassify_seed_as_inherited(seed_data)
            second = reclassify_seed_as_inherited(seed_data)

            assert first["reclassified"] == 1
            assert second["reclassified"] == 0
            assert second["already_correct"] == 1
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_does_not_touch_demonstrated(self, tmp_path):
        """DEMONSTRATED entries that happen to match seed content must not
        be downgraded to INHERITED — they had evidence behind them."""
        from divineos.core.knowledge import _get_connection, store_knowledge

        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()
            init_memory_tables()

            store_knowledge(
                knowledge_type="FACT",
                content="Shared content observed this session",
                source="DEMONSTRATED",
            )
            seed_data = {
                "knowledge": [
                    {"type": "FACT", "content": "Shared content observed this session"},
                ],
            }
            counts = reclassify_seed_as_inherited(seed_data)
            assert counts["reclassified"] == 0

            conn = _get_connection()
            try:
                row = conn.execute(
                    "SELECT source FROM knowledge WHERE superseded_by IS NULL"
                ).fetchone()
            finally:
                conn.close()

            assert row[0] == "DEMONSTRATED", "must not downgrade DEMONSTRATED entries to INHERITED"
        finally:
            os.environ.pop("DIVINEOS_DB", None)


class TestRestoreInheritedConfidence:
    """Migration: heal INHERITED entries spuriously demoted by the orphan bug.

    Before the orphan-flagger fix, fresh seed entries were demoted to
    confidence 0.5 on the same day they loaded. This migration walks the
    canonical seed and restores INHERITED entries sitting at the bug's
    sentinel value (0.5) back to their seed-specified confidence.
    """

    def test_restores_matching_inherited_at_sentinel(self, tmp_path):
        from divineos.core.knowledge import _get_connection, store_knowledge

        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()
            init_memory_tables()

            # Simulate the bug's outcome: INHERITED entry demoted to 0.5
            store_knowledge(
                knowledge_type="PRINCIPLE",
                content="Foundational seed principle",
                source="INHERITED",
                confidence=0.5,  # demoted by the orphan bug
            )
            # A non-seed INHERITED entry at 0.5 (should NOT be restored —
            # content doesn't match the current seed)
            store_knowledge(
                knowledge_type="PRINCIPLE",
                content="Some old seed content no longer in canonical seed",
                source="INHERITED",
                confidence=0.5,
            )

            seed_data = {
                "knowledge": [
                    {
                        "type": "PRINCIPLE",
                        "content": "Foundational seed principle",
                        "confidence": 1.0,
                    },
                ],
            }
            counts = restore_inherited_confidence(seed_data)

            assert counts["restored"] == 1
            # The non-matching one is "not_victim" because content isn't in seed
            assert counts["not_victim"] == 1

            conn = _get_connection()
            try:
                rows = conn.execute(
                    "SELECT content, confidence FROM knowledge WHERE superseded_by IS NULL"
                ).fetchall()
            finally:
                conn.close()
            by_content = {r[0]: r[1] for r in rows}
            assert by_content["Foundational seed principle"] == 1.0
            # Non-matching one stays at 0.5
            assert by_content["Some old seed content no longer in canonical seed"] == 0.5
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_does_not_touch_entries_at_other_confidences(self, tmp_path):
        """If an INHERITED entry is at confidence != 0.5, it wasn't the bug's
        victim — don't mess with it."""
        from divineos.core.knowledge import _get_connection, store_knowledge

        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()
            init_memory_tables()

            store_knowledge(
                knowledge_type="FACT",
                content="Matching seed content but at intentional confidence",
                source="INHERITED",
                confidence=0.7,  # deliberately set, not the bug sentinel
            )
            seed_data = {
                "knowledge": [
                    {
                        "type": "FACT",
                        "content": "Matching seed content but at intentional confidence",
                        "confidence": 1.0,
                    },
                ],
            }
            counts = restore_inherited_confidence(seed_data)
            assert counts["restored"] == 0
            assert counts["already_ok"] == 1

            conn = _get_connection()
            try:
                row = conn.execute(
                    "SELECT confidence FROM knowledge WHERE superseded_by IS NULL"
                ).fetchone()
            finally:
                conn.close()
            assert row[0] == 0.7  # untouched
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_ignores_stated_and_demonstrated(self, tmp_path):
        """Only INHERITED entries are candidates. STATED/DEMONSTRATED entries
        at 0.5 were not victims of this bug (they earned their confidence
        through session evidence)."""
        from divineos.core.knowledge import _get_connection, store_knowledge

        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()
            init_memory_tables()

            store_knowledge(
                knowledge_type="FACT",
                content="A STATED fact that matches seed content",
                source="STATED",
                confidence=0.5,
            )
            seed_data = {
                "knowledge": [
                    {
                        "type": "FACT",
                        "content": "A STATED fact that matches seed content",
                        "confidence": 1.0,
                    },
                ],
            }
            counts = restore_inherited_confidence(seed_data)
            assert counts["restored"] == 0

            conn = _get_connection()
            try:
                row = conn.execute(
                    "SELECT confidence FROM knowledge WHERE superseded_by IS NULL"
                ).fetchone()
            finally:
                conn.close()
            assert row[0] == 0.5  # STATED entry untouched
        finally:
            os.environ.pop("DIVINEOS_DB", None)

    def test_is_idempotent(self, tmp_path):
        from divineos.core.knowledge import store_knowledge

        os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
        try:
            init_db()
            init_knowledge_table()
            init_memory_tables()

            store_knowledge(
                knowledge_type="PRINCIPLE",
                content="Idempotency check content",
                source="INHERITED",
                confidence=0.5,
            )
            seed_data = {
                "knowledge": [
                    {
                        "type": "PRINCIPLE",
                        "content": "Idempotency check content",
                        "confidence": 1.0,
                    },
                ],
            }
            first = restore_inherited_confidence(seed_data)
            second = restore_inherited_confidence(seed_data)
            assert first["restored"] == 1
            assert second["restored"] == 0
            assert second["already_ok"] == 1
        finally:
            os.environ.pop("DIVINEOS_DB", None)
