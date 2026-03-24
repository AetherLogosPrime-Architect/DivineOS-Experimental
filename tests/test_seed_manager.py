"""Tests for seed versioning and validation."""

import os

from divineos.core.seed_manager import (
    apply_seed,
    get_applied_seed_version,
    set_applied_seed_version,
    should_reseed,
    validate_seed,
)
from divineos.core.consolidation import init_knowledge_table
from divineos.core.ledger import init_db
from divineos.core.memory import init_memory_tables


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
