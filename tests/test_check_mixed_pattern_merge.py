"""Tests for the mixed-pattern-merge gate (claim ec844fcf)."""

from __future__ import annotations

import importlib.util
from pathlib import Path


# Load the script as a module so we can call its functions directly.
_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "check_mixed_pattern_merge.py"
_spec = importlib.util.spec_from_file_location("check_mixed_pattern_merge", _SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


# ─── _classify_subsystem_changes ────────────────────────────────────


class TestClassifySubsystemChanges:
    def test_add_in_core_subsystem_buckets_correctly(self):
        entries = [("A", "src/divineos/core/family/access_check.py")]
        result = _mod._classify_subsystem_changes(entries)
        assert "family" in result
        assert result["family"]["A"] == ["src/divineos/core/family/access_check.py"]
        assert result["family"]["D"] == []

    def test_delete_in_core_subsystem_buckets_correctly(self):
        entries = [("D", "src/divineos/core/council/expert.py")]
        result = _mod._classify_subsystem_changes(entries)
        assert "council" in result
        assert result["council"]["D"] == ["src/divineos/core/council/expert.py"]
        assert result["council"]["A"] == []

    def test_modify_status_ignored(self):
        entries = [("M", "src/divineos/core/family/access_check.py")]
        result = _mod._classify_subsystem_changes(entries)
        # M is not tracked
        assert result == {}

    def test_rename_status_ignored(self):
        entries = [("R", "src/divineos/core/family/new_path.py")]
        result = _mod._classify_subsystem_changes(entries)
        # R is not tracked (v1 boundary)
        assert result == {}

    def test_non_core_paths_ignored(self):
        entries = [
            ("A", "src/divineos/cli/new_command.py"),
            ("D", "tests/test_old.py"),
            ("A", "docs/note.md"),
        ]
        result = _mod._classify_subsystem_changes(entries)
        assert result == {}

    def test_core_top_level_files_ignored(self):
        # core/ledger.py is not under a subsystem — it's directly in core/.
        # The pattern requires core/<subsystem>/<file>.
        entries = [("A", "src/divineos/core/ledger.py")]
        result = _mod._classify_subsystem_changes(entries)
        assert result == {}

    def test_multiple_subsystems_separately_bucketed(self):
        entries = [
            ("A", "src/divineos/core/family/new.py"),
            ("D", "src/divineos/core/council/old.py"),
        ]
        result = _mod._classify_subsystem_changes(entries)
        assert set(result.keys()) == {"family", "council"}
        assert result["family"]["A"] == ["src/divineos/core/family/new.py"]
        assert result["council"]["D"] == ["src/divineos/core/council/old.py"]


# ─── _detect_mixed_pattern ──────────────────────────────────────────


class TestDetectMixedPattern:
    def test_pure_add_no_violation(self):
        buckets = {
            "family": {"A": ["src/divineos/core/family/new.py"], "D": []},
        }
        assert _mod._detect_mixed_pattern(buckets) == []

    def test_pure_delete_no_violation(self):
        buckets = {
            "family": {"A": [], "D": ["src/divineos/core/family/old.py"]},
        }
        assert _mod._detect_mixed_pattern(buckets) == []

    def test_mixed_pattern_in_one_subsystem_flags(self):
        buckets = {
            "family": {
                "A": ["src/divineos/core/family/new.py"],
                "D": ["src/divineos/core/family/old.py"],
            },
        }
        assert _mod._detect_mixed_pattern(buckets) == ["family"]

    def test_cross_subsystem_add_and_delete_no_violation(self):
        # Add in family, delete in council — different subsystems, OK.
        buckets = {
            "family": {"A": ["src/divineos/core/family/new.py"], "D": []},
            "council": {"A": [], "D": ["src/divineos/core/council/old.py"]},
        }
        assert _mod._detect_mixed_pattern(buckets) == []

    def test_multiple_subsystems_both_violating(self):
        buckets = {
            "family": {
                "A": ["src/divineos/core/family/new.py"],
                "D": ["src/divineos/core/family/old.py"],
            },
            "council": {
                "A": ["src/divineos/core/council/new.py"],
                "D": ["src/divineos/core/council/old.py"],
            },
        }
        assert sorted(_mod._detect_mixed_pattern(buckets)) == ["council", "family"]


# ─── PR #230 reproduction case ──────────────────────────────────────


class TestPr230NamedAdversary:
    """The named adversary: PR #230 stripped core/family/ + core/council/
    while adding template improvements to those same subsystems. Verify
    the gate catches this exact shape."""

    def test_pr230_shape_blocked(self):
        # Reproduces the PR #230 pattern: family stripped + new family
        # template files added in same PR.
        entries = [
            # Family strip (selected files from the actual strip commit)
            ("D", "src/divineos/core/family/access_check.py"),
            ("D", "src/divineos/core/family/costly_disagreement.py"),
            ("D", "src/divineos/core/family/planted_contradiction.py"),
            # Template improvement added to family in same PR
            ("A", "src/divineos/core/family/voice.py"),
        ]
        buckets = _mod._classify_subsystem_changes(entries)
        violations = _mod._detect_mixed_pattern(buckets)
        assert "family" in violations

    def test_pure_strip_pr_passes_gate(self):
        # A PR that ONLY strips (no additions) should pass — the gate
        # is for mixed patterns. Pure strips are detected by other
        # mechanisms (multi-party-review, ADR requirement).
        entries = [
            ("D", "src/divineos/core/family/access_check.py"),
            ("D", "src/divineos/core/family/costly_disagreement.py"),
        ]
        buckets = _mod._classify_subsystem_changes(entries)
        violations = _mod._detect_mixed_pattern(buckets)
        assert violations == []

    def test_pure_template_improvement_pr_passes_gate(self):
        # A PR that adds template files without stripping anything should
        # pass cleanly.
        entries = [
            ("A", "src/divineos/core/family/voice.py"),
            ("A", "src/divineos/core/family/queue.py"),
        ]
        buckets = _mod._classify_subsystem_changes(entries)
        violations = _mod._detect_mixed_pattern(buckets)
        assert violations == []
