"""Tests for knowledge_voids — Pillar VI cosmic-voids pull."""

from __future__ import annotations

import json

from divineos.core.knowledge_voids import (
    TagVoid,
    TypeVoid,
    VoidReport,
    _median,
    detect_voids,
)


def _entry(kid: str, ktype: str, content: str = "x", tags=None) -> tuple[str, str, str, str]:
    return (kid, ktype, content, json.dumps(tags or []))


class TestMedian:
    def test_empty(self):
        assert _median([]) == 0.0

    def test_odd_length(self):
        assert _median([1, 5, 3]) == 3.0

    def test_even_length(self):
        assert _median([1, 2, 3, 4]) == 2.5


class TestTypeVoids:
    def test_present_balanced_types_not_flagged(self):
        entries = [_entry(f"k{i}", "FACT") for i in range(10)] + [
            _entry(f"j{i}", "PROCEDURE") for i in range(10)
        ]
        r = detect_voids(entries=entries)
        # FACT and PROCEDURE are at the median, not below — not voids.
        # (Missing KNOWLEDGE_TYPES are voids by design; the operator
        # decides whether to fill them.)
        flagged = {tv.knowledge_type for tv in r.type_voids}
        assert "FACT" not in flagged
        assert "PROCEDURE" not in flagged

    def test_void_when_count_far_below_median(self):
        entries = (
            [_entry(f"a{i}", "FACT") for i in range(20)]
            + [_entry(f"b{i}", "PROCEDURE") for i in range(20)]
            + [_entry("c1", "PRINCIPLE")]
        )
        r = detect_voids(entries=entries)
        void_types = {tv.knowledge_type for tv in r.type_voids}
        assert "PRINCIPLE" in void_types

    def test_threshold_controls_sensitivity(self):
        entries = [_entry(f"a{i}", "FACT") for i in range(10)] + [
            _entry(f"b{i}", "PROCEDURE") for i in range(3)
        ]
        # Strict threshold (0.5) should flag PROCEDURE; loose (0.1) shouldn't
        strict = detect_voids(entries=entries, void_threshold_ratio=0.5)
        loose = detect_voids(entries=entries, void_threshold_ratio=0.1)
        strict_types = {tv.knowledge_type for tv in strict.type_voids}
        loose_types = {tv.knowledge_type for tv in loose.type_voids}
        assert "PROCEDURE" in strict_types
        assert "PROCEDURE" not in loose_types


class TestTagVoids:
    def test_singleton_tag_flagged(self):
        entries = [
            _entry("a", "FACT", tags=["common", "rare"]),
            _entry("b", "FACT", tags=["common"]),
            _entry("c", "FACT", tags=["common"]),
        ]
        r = detect_voids(entries=entries)
        tag_names = {tv.tag for tv in r.tag_voids}
        assert "rare" in tag_names
        assert "common" not in tag_names

    def test_sample_id_included(self):
        entries = [_entry("kid-1", "FACT", "Hello world", tags=["unique"])]
        r = detect_voids(entries=entries)
        assert len(r.tag_voids) == 1
        assert r.tag_voids[0].tag == "unique"
        assert r.tag_voids[0].sample_id == "kid-1"
        assert "Hello world" in r.tag_voids[0].sample_content


class TestVoidReportShape:
    def test_total_counts(self):
        entries = [
            _entry("a", "FACT", tags=["x"]),
            _entry("b", "PROCEDURE", tags=["x", "y"]),
        ]
        r = detect_voids(entries=entries)
        assert r.total_entries == 2
        assert r.total_unique_tags == 2

    def test_type_counts_dict(self):
        entries = [_entry("a", "FACT"), _entry("b", "FACT"), _entry("c", "PROCEDURE")]
        r = detect_voids(entries=entries)
        assert r.type_counts["FACT"] == 2
        assert r.type_counts["PROCEDURE"] == 1

    def test_immutable_dataclasses(self):
        tv = TypeVoid(knowledge_type="FACT", count=1, median=10.0)
        try:
            tv.count = 99  # type: ignore[misc]
        except Exception:
            return
        raise AssertionError("TypeVoid should be frozen")

    def test_handles_malformed_tags_json(self):
        entries = [
            ("a", "FACT", "content", "not-valid-json"),
            ("b", "FACT", "content", "{}"),  # not a list
        ]
        r = detect_voids(entries=entries)
        # Should not crash; both entries counted, no tags extracted
        assert r.total_entries == 2
        assert r.tag_voids == []

    def test_empty_store(self):
        r = detect_voids(entries=[])
        assert r.total_entries == 0
        assert r.type_voids == []
        assert r.tag_voids == []


class TestPublicAPI:
    def test_void_report_is_dataclass(self):
        r = detect_voids(entries=[])
        assert isinstance(r, VoidReport)

    def test_tag_void_dataclass(self):
        tv = TagVoid(tag="x", sample_id="id1", sample_content="hello")
        assert tv.tag == "x"
