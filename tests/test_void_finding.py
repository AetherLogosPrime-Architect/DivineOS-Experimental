"""Tests for VOID Finding dataclass + severity rubric."""

from __future__ import annotations

import pytest

from divineos.core.void.finding import SEVERITY_RUBRIC, Finding, Severity


class TestSeverity:
    def test_parse_canonical(self) -> None:
        assert Severity.parse("HIGH") is Severity.HIGH

    def test_parse_lowercase(self) -> None:
        assert Severity.parse("medium") is Severity.MEDIUM

    def test_parse_with_whitespace(self) -> None:
        assert Severity.parse("  low  ") is Severity.LOW

    def test_parse_unknown_raises(self) -> None:
        with pytest.raises(ValueError):
            Severity.parse("PURPLE")

    def test_all_severities_have_rubric(self) -> None:
        for s in Severity:
            assert s in SEVERITY_RUBRIC
            assert SEVERITY_RUBRIC[s]


class TestFinding:
    def test_minimal_construction(self) -> None:
        f = Finding(
            persona="sycophant",
            target="proposed-change-X",
            severity=Severity.LOW,
            title="Looks great",
            body="This is fine.",
        )
        assert f.evidence == []
        assert f.tags == []

    def test_to_payload_round_trip(self) -> None:
        f = Finding(
            persona="reductio",
            target="claim-42",
            severity=Severity.HIGH,
            title="Fails reductio",
            body="If you take this to its limit, contradiction.",
            evidence=["claim-42", "ledger:abc"],
            tags=["logic"],
        )
        payload = f.to_payload()
        f2 = Finding.from_payload(payload)
        assert f2 == f

    def test_payload_severity_is_string(self) -> None:
        f = Finding(
            persona="mirror",
            target="t",
            severity=Severity.CRITICAL,
            title="x",
            body="y",
        )
        assert f.to_payload()["severity"] == "CRITICAL"

    def test_frozen_dataclass(self) -> None:
        f = Finding(persona="p", target="t", severity=Severity.LOW, title="x", body="y")
        with pytest.raises(Exception):
            f.persona = "other"  # type: ignore[misc]
