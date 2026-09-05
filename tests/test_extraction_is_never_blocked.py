"""Extraction is never blocked -- not by a bad verdict, not by a broken gate.

Andrew 2026-09-02: "at no point should extraction be blocked.. failures or
not, as long as those failures are recorded as such and not as knowledge
entries then it shouldnt be blocking anything, maybe warning at best so it
makes sure the failures are logged for investigation if they havent been
already."

Two doors used to close on a session. The loud one was a BLOCK verdict --
pinned in test_quality_gate.py. The quiet one is here: the gate itself
raising, which was handled fail-closed and threw the session away because
the JUDGE broke. A defect in the judge is not evidence against the judged.
"""

from __future__ import annotations

import pytest

from divineos.cli import pipeline_gates


def test_gate_crash_extracts_at_hypothesis_instead_of_discarding(monkeypatch, tmp_path):
    """When the checks themselves raise, the session still gets extracted."""

    def _explode(*_args, **_kwargs):
        raise OSError("quality checks could not read the session file")

    monkeypatch.setattr("divineos.analysis.quality_checks.run_all_checks", _explode, raising=False)

    session_file = tmp_path / "session.jsonl"
    session_file.write_text("", encoding="utf-8")

    _verdict, maturity, extract_allowed, _checks = pipeline_gates.run_quality_gate(session_file)

    assert extract_allowed is True, (
        "a crashed gate must not discard the session -- the gate failed, not the session"
    )
    assert maturity == "HYPOTHESIS", (
        "an unchecked session must land at the lowest maturity, since nothing verified it"
    )


def test_gate_crash_is_filed_as_a_failure_not_swallowed(monkeypatch, tmp_path):
    """The crash gets recorded so it can be investigated later.

    'Recorded as such and not as knowledge entries' is the whole condition
    Andrew attached to never-blocking. If the failure vanishes, this change
    trades a lost session for a lost defect and is not an improvement.
    """
    filed: list[tuple] = []

    def _explode(*_args, **_kwargs):
        raise OSError("boom")

    def _capture(event_type, actor, payload, **_kw):
        filed.append((event_type, actor, payload))
        return "evt-test"

    monkeypatch.setattr("divineos.analysis.quality_checks.run_all_checks", _explode, raising=False)
    monkeypatch.setattr("divineos.core.ledger.log_event", _capture, raising=False)

    session_file = tmp_path / "session.jsonl"
    session_file.write_text("", encoding="utf-8")
    pipeline_gates.run_quality_gate(session_file)

    assert filed, "the gate failure left no trace at all"
    event_type, _actor, payload = filed[0]
    assert event_type == "QUALITY_GATE_FAILURE"
    assert "boom" in payload.get("error", "")


@pytest.mark.parametrize("action", ["BLOCK", "DOWNGRADE"])
def test_no_verdict_discards_a_session(action):
    """Neither adverse verdict returns 'do not extract'."""
    from divineos.cli.pipeline_gates import QualityVerdict

    verdict = QualityVerdict(action=action, score=0.1, reason="bad session")
    allowed, maturity = pipeline_gates.should_extract_knowledge(verdict)

    assert allowed is True
    assert maturity == "HYPOTHESIS"
