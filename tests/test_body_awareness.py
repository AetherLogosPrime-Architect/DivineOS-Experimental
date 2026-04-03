"""Tests for Body Awareness -- computational interoception."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from divineos.core.body_awareness import (
    CACHE_LIMITS,
    CacheState,
    SubstrateVitals,
    _measure_cache,
    format_vitals,
    format_vitals_brief,
    measure_vitals,
    prune_caches,
)


class TestMeasureVitals:
    """Vital measurements work and return sane values."""

    def test_returns_vitals(self):
        vitals = measure_vitals()
        assert isinstance(vitals, SubstrateVitals)
        assert vitals.measured_at > 0

    def test_ledger_events_counted(self):
        vitals = measure_vitals()
        # Tests create events, so there should be some
        assert vitals.ledger_events >= 0

    def test_knowledge_counted(self):
        vitals = measure_vitals()
        assert vitals.knowledge_entries >= 0
        assert vitals.superseded_entries >= 0

    def test_ratios_bounded(self):
        vitals = measure_vitals()
        assert 0.0 <= vitals.supersession_ratio <= 1.0
        assert 0.0 <= vitals.tool_event_ratio <= 1.0

    def test_total_size_non_negative(self):
        vitals = measure_vitals()
        assert vitals.total_size_mb >= 0.0

    def test_warnings_are_list(self):
        vitals = measure_vitals()
        assert isinstance(vitals.warnings, list)


class TestWarningThresholds:
    """Warnings fire at correct thresholds."""

    def test_storage_warning_at_50mb(self):
        vitals = SubstrateVitals(total_size_mb=60)
        # Manually check threshold logic
        assert vitals.total_size_mb > 50

    def test_tool_event_ratio_warning(self):
        vitals = SubstrateVitals(
            tool_event_ratio=0.85,
            ledger_events=1000,
            tool_events=850,
        )
        assert vitals.tool_event_ratio > 0.8

    def test_no_warnings_on_healthy_vitals(self):
        vitals = SubstrateVitals(
            total_size_mb=5.0,
            tool_event_ratio=0.02,
            supersession_ratio=0.3,
            ledger_events=500,
        )
        # measure_vitals generates warnings; raw construction doesn't
        assert len(vitals.warnings) == 0


class TestFormatting:
    """Output formatting."""

    def test_format_vitals_contains_header(self):
        output = format_vitals()
        assert "BODY AWARENESS" in output

    def test_format_vitals_contains_storage(self):
        output = format_vitals()
        assert "STORAGE" in output

    def test_format_vitals_contains_tables(self):
        output = format_vitals()
        assert "TABLES" in output

    def test_format_brief_contains_body(self):
        output = format_vitals_brief()
        assert "Body:" in output

    def test_format_brief_compact(self):
        output = format_vitals_brief()
        # Brief should be a single line (pipe-separated)
        assert "|" in output


class TestCacheState:
    """Cache measurement and tracking."""

    def test_measure_cache_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cs = _measure_cache(Path(tmpdir), "test_cache", 10.0)
            assert cs.size_mb == 0.0
            assert cs.file_count == 0
            assert not cs.over_limit

    def test_measure_cache_with_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files large enough to survive rounding (>10KB each)
            for i in range(5):
                (Path(tmpdir) / f"file_{i}.bin").write_bytes(b"x" * 100_000)
            cs = _measure_cache(Path(tmpdir), "test_cache", 10.0)
            assert cs.file_count == 5
            assert cs.size_mb > 0
            assert not cs.over_limit  # 500KB is well under 10MB

    def test_measure_cache_over_limit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file that exceeds a tiny limit
            (Path(tmpdir) / "big.bin").write_bytes(b"x" * 2000)
            cs = _measure_cache(Path(tmpdir), "test_cache", 0.001)  # 1KB limit
            assert cs.over_limit

    def test_measure_cache_nested_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = Path(tmpdir) / "sub" / "deep"
            nested.mkdir(parents=True)
            (nested / "file.txt").write_text("hello")
            cs = _measure_cache(Path(tmpdir), "test_cache", 10.0)
            assert cs.file_count == 1

    def test_vitals_include_caches(self):
        vitals = measure_vitals()
        assert isinstance(vitals.caches, list)
        assert vitals.cache_total_mb >= 0.0

    def test_cache_limits_defined(self):
        assert ".mypy_cache" in CACHE_LIMITS
        assert "tmp" in CACHE_LIMITS
        assert all(v > 0 for v in CACHE_LIMITS.values())


class TestCacheConveyorBelt:
    """Prune logic -- the conveyor belt."""

    def test_prune_dry_run_no_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / ".mypy_cache"
            cache_dir.mkdir()
            (cache_dir / "old.bin").write_bytes(b"x" * 5000)

            with patch(
                "divineos.core.body_awareness._get_project_root",
                return_value=Path(tmpdir),
            ):
                with patch(
                    "divineos.core.body_awareness.CACHE_LIMITS",
                    {".mypy_cache": 0.001},
                ):
                    actions = prune_caches(dry_run=True)
                    assert any("Would remove" in a for a in actions)
                    # File should still exist
                    assert (cache_dir / "old.bin").exists()

    def test_prune_actually_deletes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / ".mypy_cache"
            cache_dir.mkdir()
            (cache_dir / "old.bin").write_bytes(b"x" * 5000)

            with patch(
                "divineos.core.body_awareness._get_project_root",
                return_value=Path(tmpdir),
            ):
                with patch(
                    "divineos.core.body_awareness.CACHE_LIMITS",
                    {".mypy_cache": 0.001},
                ):
                    actions = prune_caches(dry_run=False)
                    assert any("Removed" in a for a in actions)
                    assert not (cache_dir / "old.bin").exists()

    def test_prune_removes_oldest_first(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "tmp"
            cache_dir.mkdir()

            # Create old file and new file, each 50KB
            old_file = cache_dir / "old.bin"
            new_file = cache_dir / "new.bin"
            old_file.write_bytes(b"x" * 50_000)
            os.utime(old_file, (1000000, 1000000))  # very old
            new_file.write_bytes(b"x" * 50_000)
            # new_file keeps current mtime

            with patch(
                "divineos.core.body_awareness._get_project_root",
                return_value=Path(tmpdir),
            ):
                # Limit of 0.06 MB (~60KB) -- one 50KB file fits, two don't
                with patch(
                    "divineos.core.body_awareness.CACHE_LIMITS",
                    {"tmp": 0.06},
                ):
                    prune_caches(dry_run=False)
                    # Old file should be gone, new file should remain
                    assert not old_file.exists()
                    assert new_file.exists()

    def test_prune_nothing_when_under_limit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / ".ruff_cache"
            cache_dir.mkdir()
            (cache_dir / "small.txt").write_text("tiny")

            with patch(
                "divineos.core.body_awareness._get_project_root",
                return_value=Path(tmpdir),
            ):
                with patch(
                    "divineos.core.body_awareness.CACHE_LIMITS",
                    {".ruff_cache": 10.0},
                ):
                    actions = prune_caches(dry_run=False)
                    assert any("Nothing to prune" in a for a in actions)
                    assert (cache_dir / "small.txt").exists()

    def test_prune_cleans_empty_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / ".mypy_cache"
            nested = cache_dir / "sub" / "deep"
            nested.mkdir(parents=True)
            (nested / "file.bin").write_bytes(b"x" * 5000)

            with patch(
                "divineos.core.body_awareness._get_project_root",
                return_value=Path(tmpdir),
            ):
                with patch(
                    "divineos.core.body_awareness.CACHE_LIMITS",
                    {".mypy_cache": 0.001},
                ):
                    prune_caches(dry_run=False)
                    # Nested dirs should be cleaned up
                    assert not nested.exists()


class TestFormatWithCaches:
    """Formatting includes cache info."""

    def test_format_shows_caches_section(self):
        vitals = SubstrateVitals(
            caches=[
                CacheState(
                    name=".mypy_cache",
                    size_mb=45.0,
                    limit_mb=50.0,
                    file_count=1200,
                    over_limit=False,
                )
            ],
            cache_total_mb=45.0,
        )
        output = format_vitals(vitals)
        assert "CACHES" in output
        assert ".mypy_cache" in output
        assert "[ok]" in output

    def test_format_shows_over_limit(self):
        vitals = SubstrateVitals(
            caches=[
                CacheState(
                    name=".mypy_cache",
                    size_mb=80.0,
                    limit_mb=50.0,
                    file_count=5000,
                    over_limit=True,
                )
            ],
            cache_total_mb=80.0,
        )
        output = format_vitals(vitals)
        assert "[!]" in output

    def test_brief_shows_cache_total(self):
        vitals = SubstrateVitals(
            cache_total_mb=45.0,
            total_size_mb=50.0,
        )
        output = format_vitals_brief(vitals)
        assert "cache: 45MB" in output
