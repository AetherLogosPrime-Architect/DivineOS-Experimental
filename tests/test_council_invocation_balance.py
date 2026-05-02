"""Tests for council invocation tally + balance surface.

Added 2026-04-21 per sycophancy-toward-self principle (knowledge 929cb459):
the agent was reaching for the same 5-7 analytical experts in all council
consults. These helpers make selection bias visible at the point of use so
the agent can choose consciously rather than unconsciously defaulting.
"""

from __future__ import annotations

import pytest

from divineos.core.council.consultation_log import (
    format_invocation_balance,
    invocation_balance,
    invocation_tally,
    log_consultation,
)
from divineos.core.council.framework import LensAnalysis
from divineos.core.watchmen._schema import init_watchmen_tables


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    db = tmp_path / "tally.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db))
    from divineos.core.ledger import init_db

    init_db()
    init_watchmen_tables()
    yield db


def _analysis(name: str) -> LensAnalysis:
    """Minimal LensAnalysis for recording purposes — content doesn't matter."""
    return LensAnalysis(
        expert_name=name,
        problem="",
        methodology_applied="",
        methodology_steps=[],
        core_principle="",
        relevant_insights=[],
        concerns=["x"],
        severity_map={},
        integration_findings=[],
        optimization_target="",
        non_negotiables=[],
        uncertainty_handling="",
        characteristic_questions=[],
        synthesis="",
    )


def _consult(experts: list[str]) -> None:
    """Log a consultation with the given selected-experts."""
    log_consultation(
        question="q",
        selected_expert_names=experts,
        analyses=[_analysis(n) for n in experts],
        synthesis="",
    )


class TestInvocationTally:
    def test_empty_history_returns_empty(self):
        assert invocation_tally() == {}

    def test_single_consultation_counts_each_expert_once(self):
        _consult(["Kahneman", "Popper", "Watts"])
        tally = invocation_tally()
        assert tally == {"Kahneman": 1, "Popper": 1, "Watts": 1}

    def test_multiple_consultations_accumulate(self):
        _consult(["Kahneman", "Popper"])
        _consult(["Kahneman", "Dennett"])
        _consult(["Kahneman", "Yudkowsky"])
        tally = invocation_tally()
        assert tally["Kahneman"] == 3
        assert tally["Popper"] == 1
        assert tally["Dennett"] == 1
        assert tally["Yudkowsky"] == 1

    def test_last_n_caps_history(self):
        """Only the most recent N consultations count."""
        for _ in range(30):
            _consult(["Feynman"])
        tally = invocation_tally(last_n=10)
        assert tally["Feynman"] == 10


class TestInvocationBalance:
    def test_returns_empty_balance_when_no_history(self):
        most, rarely = invocation_balance(["Kahneman", "Popper"])
        # All counts should be 0 — no one's been invoked
        assert all(count == 0 for _, count in most)
        assert all(count == 0 for _, count in rarely)

    def test_identifies_most_invoked(self):
        _consult(["Kahneman", "Popper"])
        _consult(["Kahneman", "Popper"])
        _consult(["Kahneman", "Dennett"])
        most, _ = invocation_balance(
            ["Kahneman", "Popper", "Dennett", "Watts"],
            last_n=20,
        )
        top_names = [name for name, _ in most]
        assert top_names[0] == "Kahneman"  # 3 invocations

    def test_identifies_never_invoked(self):
        _consult(["Kahneman"])
        _, rarely = invocation_balance(
            ["Kahneman", "Watts", "Dennett", "Angelou"],
            last_n=20,
        )
        never_invoked = [name for name, count in rarely if count == 0]
        assert "Watts" in never_invoked
        assert "Dennett" in never_invoked
        assert "Angelou" in never_invoked
        assert "Kahneman" not in never_invoked

    def test_returns_top_and_bottom_five(self):
        names = [f"Expert{i}" for i in range(10)]
        # Invoke the first three more often
        for _ in range(5):
            _consult(names[:3])
        most, rarely = invocation_balance(names, last_n=20)
        assert len(most) == 5
        assert len(rarely) == 5


class TestFormatInvocationBalance:
    def test_empty_history_returns_empty_string(self):
        # With no consultations, no imbalance to surface
        out = format_invocation_balance(["Kahneman", "Popper"])
        assert out == ""

    def test_surfaces_most_invoked(self):
        _consult(["Kahneman", "Popper", "Dennett"])
        _consult(["Kahneman", "Popper"])
        out = format_invocation_balance(["Kahneman", "Popper", "Dennett", "Watts"], last_n=20)
        assert "most-invoked" in out
        assert "Kahneman" in out

    def test_surfaces_never_invoked_when_zeroes_exist(self):
        _consult(["Kahneman"])
        out = format_invocation_balance(["Kahneman", "Watts", "Dennett"], last_n=20)
        assert "never-invoked" in out
        assert "Watts" in out or "Dennett" in out

    def test_surfaces_rarely_invoked_when_no_zeroes(self):
        """When every expert has been invoked at least once, show rarely-invoked instead."""
        # Invoke everyone at least once; Kahneman many more times
        experts = ["Kahneman", "Popper", "Dennett", "Watts"]
        _consult(experts)
        _consult(["Kahneman"])
        _consult(["Kahneman"])
        out = format_invocation_balance(experts, last_n=20)
        assert "rarely-invoked" in out or "never-invoked" in out
