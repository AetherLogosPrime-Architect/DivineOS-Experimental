"""Tests for knowledge hygiene — audit, stale sweep, orphan detection."""

import time

from divineos.core.knowledge._base import _KNOWLEDGE_COLS, _get_connection, _row_to_dict
from divineos.core.knowledge_maintenance import (
    _audit_types,
    _flag_orphans,
    _reap_dead_entries,
    _sweep_stale,
    format_hygiene_report,
    run_knowledge_hygiene,
)


def _setup(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db_path))
    from divineos.core.knowledge._base import init_knowledge_table

    init_knowledge_table()


def _insert_entry(
    content,
    knowledge_type="PRINCIPLE",
    confidence=0.8,
    created_days_ago=5,
    access_count=0,
    corroboration_count=0,
):
    """Insert a test knowledge entry and return its ID."""
    import hashlib
    import uuid

    kid = str(uuid.uuid4())
    now = time.time()
    created = now - (created_days_ago * 86400)
    content_hash = hashlib.sha256(content.encode()).hexdigest()[:32]
    conn = _get_connection()
    conn.execute(
        "INSERT INTO knowledge (knowledge_id, knowledge_type, content, confidence, "
        "created_at, updated_at, access_count, corroboration_count, maturity, content_hash) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'RAW', ?)",
        (
            kid,
            knowledge_type,
            content,
            confidence,
            created,
            created,
            access_count,
            corroboration_count,
            content_hash,
        ),
    )
    conn.commit()
    conn.close()
    return kid


def _get_entry(kid):
    conn = _get_connection()
    row = conn.execute(
        f"SELECT {_KNOWLEDGE_COLS} FROM knowledge WHERE knowledge_id = ?", (kid,)
    ).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


class TestAuditTypes:
    """Re-running the noise filter on existing PRINCIPLE/BOUNDARY entries."""

    def test_pure_noise_gets_superseded(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        # "yes lets do it" is pure affirmation noise
        kid = _insert_entry("yes lets do it", "PRINCIPLE", created_days_ago=3)
        entries = [_get_entry(kid)]
        cutoff = time.time() - 86400  # 1 day ago
        result = _audit_types(entries, cutoff)
        assert result["superseded"] >= 1
        entry = _get_entry(kid)
        assert entry["superseded_by"] == "hygiene-audit"

    def test_prescriptive_principle_kept(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        kid = _insert_entry(
            "I should always run tests before committing code to avoid regressions",
            "PRINCIPLE",
            created_days_ago=3,
        )
        entries = [_get_entry(kid)]
        cutoff = time.time() - 86400
        result = _audit_types(entries, cutoff)
        assert result["superseded"] == 0
        assert result["demoted"] == 0

    def test_recent_entries_skipped(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        kid = _insert_entry("yes go ahead", "PRINCIPLE", created_days_ago=0)
        entries = [_get_entry(kid)]
        cutoff = time.time() - 86400  # 1 day ago — entry is newer
        result = _audit_types(entries, cutoff)
        assert result["superseded"] == 0

    def test_high_corroboration_skipped(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        kid = _insert_entry(
            "yes lets do it", "PRINCIPLE", created_days_ago=3, corroboration_count=5
        )
        entries = [_get_entry(kid)]
        cutoff = time.time() - 86400
        result = _audit_types(entries, cutoff)
        assert result["superseded"] == 0

    def test_no_prescriptive_signal_superseded(self, tmp_path, monkeypatch):
        """Long content without prescriptive signal → superseded as noise."""
        _setup(tmp_path, monkeypatch)
        kid = _insert_entry(
            "The project has a lot of files and directories and modules and packages "
            "and it uses Python and SQLite for data storage and click for CLI",
            "PRINCIPLE",
            created_days_ago=3,
        )
        entries = [_get_entry(kid)]
        cutoff = time.time() - 86400
        result = _audit_types(entries, cutoff)
        assert result["superseded"] >= 1
        entry = _get_entry(kid)
        assert entry["superseded_by"] == "hygiene-audit"

    def test_noisy_observation_gets_superseded(self, tmp_path, monkeypatch):
        """Noise detection now covers all types, not just PRINCIPLE/BOUNDARY."""
        _setup(tmp_path, monkeypatch)
        kid = _insert_entry("yes lets do it", "OBSERVATION", created_days_ago=3)
        entries = [_get_entry(kid)]
        cutoff = time.time() - 86400
        result = _audit_types(entries, cutoff)
        assert result["superseded"] >= 1

    def test_clean_observation_kept(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        kid = _insert_entry(
            "The knowledge store uses SQLite for persistence with content hashing",
            "OBSERVATION",
            created_days_ago=3,
        )
        entries = [_get_entry(kid)]
        cutoff = time.time() - 86400
        result = _audit_types(entries, cutoff)
        assert result["superseded"] == 0


class TestSweepStale:
    """Entries with temporal markers that are old get confidence decay."""

    def test_temporal_old_entry_decays(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        kid = _insert_entry(
            "The API is currently broken and returning 500 errors",
            "OBSERVATION",
            confidence=0.8,
            created_days_ago=20,
        )
        entries = [_get_entry(kid)]
        result = _sweep_stale(entries, time.time(), stale_age_days=14.0)
        assert result["decayed"] >= 1
        entry = _get_entry(kid)
        assert entry["confidence"] < 0.8

    def test_recent_temporal_not_decayed(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        kid = _insert_entry(
            "The API is currently broken", "OBSERVATION", confidence=0.8, created_days_ago=3
        )
        entries = [_get_entry(kid)]
        result = _sweep_stale(entries, time.time(), stale_age_days=14.0)
        assert result["decayed"] == 0

    def test_directive_immune(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        kid = _insert_entry(
            "Currently focus on knowledge quality",
            "DIRECTIVE",
            confidence=0.9,
            created_days_ago=20,
        )
        entries = [_get_entry(kid)]
        result = _sweep_stale(entries, time.time(), stale_age_days=14.0)
        assert result["decayed"] == 0

    def test_no_temporal_markers_not_decayed(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        kid = _insert_entry(
            "Python uses indentation for blocks",
            "OBSERVATION",
            confidence=0.8,
            created_days_ago=20,
        )
        entries = [_get_entry(kid)]
        result = _sweep_stale(entries, time.time(), stale_age_days=14.0)
        assert result["decayed"] == 0

    def test_at_floor_gets_superseded(self, tmp_path, monkeypatch):
        """Temporal entries at the decay floor get superseded, not left in limbo."""
        _setup(tmp_path, monkeypatch)
        kid = _insert_entry(
            "This is currently failing", "OBSERVATION", confidence=0.3, created_days_ago=20
        )
        entries = [_get_entry(kid)]
        result = _sweep_stale(entries, time.time(), stale_age_days=14.0)
        assert result["superseded"] >= 1
        entry = _get_entry(kid)
        assert entry["superseded_by"] == "temporal-stale"

    def test_corroborated_temporal_not_superseded(self, tmp_path, monkeypatch):
        """Temporal entries with corroboration are preserved even at floor."""
        _setup(tmp_path, monkeypatch)
        kid = _insert_entry(
            "This is currently failing",
            "OBSERVATION",
            confidence=0.3,
            created_days_ago=20,
            corroboration_count=3,
        )
        entries = [_get_entry(kid)]
        result = _sweep_stale(entries, time.time(), stale_age_days=14.0)
        assert result["superseded"] == 0
        assert result["decayed"] == 0


class TestFlagOrphans:
    """Entries never accessed and never corroborated get demoted."""

    def test_zero_access_high_confidence_demoted(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        kid = _insert_entry(
            "Something nobody looked at",
            "OBSERVATION",
            confidence=0.8,
            access_count=0,
            corroboration_count=0,
        )
        entries = [_get_entry(kid)]
        result = _flag_orphans(entries, min_sessions=3)
        assert result["flagged"] >= 1
        entry = _get_entry(kid)
        assert entry["confidence"] == 0.5

    def test_accessed_entry_not_flagged(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        kid = _insert_entry(
            "Something that was accessed",
            "OBSERVATION",
            confidence=0.8,
            access_count=3,
            corroboration_count=0,
        )
        entries = [_get_entry(kid)]
        result = _flag_orphans(entries, min_sessions=3)
        assert result["flagged"] == 0

    def test_corroborated_entry_not_flagged(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        kid = _insert_entry(
            "Corroborated entry",
            "OBSERVATION",
            confidence=0.8,
            access_count=0,
            corroboration_count=1,
        )
        entries = [_get_entry(kid)]
        result = _flag_orphans(entries, min_sessions=3)
        assert result["flagged"] == 0

    def test_directive_immune(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        kid = _insert_entry(
            "A directive nobody accessed",
            "DIRECTIVE",
            confidence=0.9,
            access_count=0,
            corroboration_count=0,
        )
        entries = [_get_entry(kid)]
        result = _flag_orphans(entries, min_sessions=3)
        assert result["flagged"] == 0

    def test_low_confidence_not_flagged(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        kid = _insert_entry(
            "Already low confidence",
            "OBSERVATION",
            confidence=0.4,
            access_count=0,
            corroboration_count=0,
        )
        entries = [_get_entry(kid)]
        result = _flag_orphans(entries, min_sessions=3)
        assert result["flagged"] == 0  # Already below threshold


class TestReapDeadEntries:
    """Entries below CONFIDENCE_SUPERSEDE_FLOOR get superseded by the reaper."""

    def test_below_floor_gets_reaped(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        kid = _insert_entry(
            "Some garbage that got penalized to 0.1", "FACT", confidence=0.1, created_days_ago=10
        )
        entries = [_get_entry(kid)]
        result = _reap_dead_entries(entries)
        assert result["reaped"] >= 1
        entry = _get_entry(kid)
        assert entry["superseded_by"] == "hygiene-reaper"

    def test_above_floor_not_reaped(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        kid = _insert_entry(
            "Decent entry at moderate confidence", "FACT", confidence=0.5, created_days_ago=10
        )
        entries = [_get_entry(kid)]
        result = _reap_dead_entries(entries)
        assert result["reaped"] == 0

    def test_directive_immune_to_reaper(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        kid = _insert_entry(
            "A directive at low confidence", "DIRECTIVE", confidence=0.1, created_days_ago=10
        )
        entries = [_get_entry(kid)]
        result = _reap_dead_entries(entries)
        assert result["reaped"] == 0


class TestRunKnowledgeHygiene:
    """Integration test for the full hygiene run."""

    def test_full_run_returns_report(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        report = run_knowledge_hygiene()
        assert "entries_scanned" in report
        assert "noise_demoted" in report
        assert "stale_decayed" in report
        assert "stale_superseded" in report
        assert "orphans_flagged" in report
        assert "reaped" in report
        assert isinstance(report["details"], list)

    def test_clean_store_no_actions(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        # Insert a well-formed entry
        _insert_entry(
            "I should always validate input before processing to prevent errors",
            "PRINCIPLE",
            confidence=0.8,
            created_days_ago=3,
            access_count=5,
            corroboration_count=2,
        )
        report = run_knowledge_hygiene()
        total = (
            report["noise_demoted"]
            + report["noise_superseded"]
            + report["stale_decayed"]
            + report["orphans_flagged"]
        )
        assert total == 0


class TestFormatReport:
    def test_clean_report(self):
        report = {
            "entries_scanned": 10,
            "noise_demoted": 0,
            "noise_superseded": 0,
            "stale_decayed": 0,
            "orphans_flagged": 0,
            "details": [],
        }
        text = format_hygiene_report(report)
        assert "clean" in text.lower()

    def test_report_with_actions(self):
        report = {
            "entries_scanned": 50,
            "noise_demoted": 3,
            "noise_superseded": 2,
            "stale_decayed": 1,
            "orphans_flagged": 4,
            "details": ["Demoted to OBSERVATION: test..."],
        }
        text = format_hygiene_report(report)
        assert "3" in text
        assert "OBSERVATION" in text
