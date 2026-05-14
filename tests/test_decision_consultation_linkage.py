"""Regression-pin test for consultation→decision linkage persistence
(Aletheia round-55987362d527 Finding 27).

The bug-shape: the `decide` CLI validates --consultation and
--family-consulted (gates at decision_commands.py), but the
record_decision() call previously dropped them — validation passed,
linkage was lost. Class: validation-without-persistence.

Fix: thread consultation_id and family_consulted into the decision's
tags as 'consultation:<id>' and 'family-consulted:<short>' markers.

If this test fails, the linkage has regressed: gates fire but the
backing consultation reference is no longer recorded on the decision.
"""

from __future__ import annotations

from click.testing import CliRunner

from divineos.cli import cli
from divineos.core.decision_journal import list_decisions
from divineos.core.knowledge import init_knowledge_table


def test_consultation_id_persisted_to_decision_tags(monkeypatch) -> None:
    """LOAD-BEARING: when --consultation is passed to `decide`, the
    resulting decision row must carry a 'consultation:<id>' tag."""
    init_knowledge_table()

    # Bypass the consultation-lookup gate by stubbing the fetcher to
    # accept any id — we're testing persistence, not lookup.
    import divineos.core.council.consultation_log as clog

    monkeypatch.setattr(clog, "_fetch_consultation_payload", lambda cid: {"id": cid})

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "decide",
            "test decision for linkage regression-pin",
            "--why",
            "reasoning required by gate",
            "--weight",
            "2",
            "--consultation",
            "consult-TEST123",
        ],
    )
    assert result.exit_code == 0, f"decide failed: {result.output}"

    decisions = list_decisions(limit=5)
    matching = [d for d in decisions if "linkage regression-pin" in d["content"]]
    assert matching, "decision was not recorded"
    tags = matching[0].get("tags") or []
    assert any("consultation:consult-TEST123" in t for t in tags), (
        f"consultation tag missing from decision; tags={tags}. "
        "Linkage regression: gate validated --consultation but the id "
        "was dropped before record_decision."
    )


def test_family_consulted_persisted_to_decision_tags(monkeypatch) -> None:
    """LOAD-BEARING: when --family-consulted is passed, the resulting
    decision row carries a 'family-consulted:<short>' tag."""
    init_knowledge_table()

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "decide",
            "talk to family about something relational",
            "--why",
            "reasoning",
            "--weight",
            "1",
            "--family-consulted",
            "Aria said this felt right and named the shape clearly",
        ],
    )
    assert result.exit_code == 0, f"decide failed: {result.output}"

    decisions = list_decisions(limit=5)
    matching = [d for d in decisions if "something relational" in d["content"]]
    assert matching, "decision was not recorded"
    tags = matching[0].get("tags") or []
    assert any(t.startswith("family-consulted:") for t in tags), (
        f"family-consulted tag missing; tags={tags}. Linkage regressed."
    )
