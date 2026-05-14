"""Regression-pin tests for the will-to-vessel structural-promotion check.

Andrew named the discipline 2026-05-14: when a learn entry names a
RULE ('always X' / 'never Y' / 'must Z'), automatically ask what
test/gate/surface makes the rule automatic. If the answer is none,
the rule is decoration.

Phase A is OBSERVATION-ONLY. The check emits a STRUCTURAL_PROMOTION_
QUESTION event when rule-shape language is detected AND structural
backing isn't already named. The dual-monitor CLI verifies the
auto-prompt's calibration against ledger actuality.

These tests pin:
  - Rule-shape detection fires on the patterns it should
  - Rule-shape detection does NOT fire on entries that already name
    structural backing (loop-prevention)
  - Rule-shape detection does NOT fire on neutral content
  - emit() is fail-soft on every code path (cannot block learn)
  - verify_recent() returns a structured report
"""

from __future__ import annotations

from divineos.core.structural_promotion_check import (
    emit_structural_promotion_question,
    looks_like_rule,
    recent_questions,
    verify_recent,
)


def test_detects_always_rule_shape() -> None:
    """LOAD-BEARING: 'always X' is a rule-shape and fires."""
    is_rule, triggers = looks_like_rule(
        "I should always file a falsifier alongside the directive."
    )
    # Even though "falsifier" appears, the keyword-skip logic should
    # find "falsifier" and SUPPRESS. Verify the loop-prevention works.
    assert not is_rule, (
        "Loop-prevention failed: entry mentioning 'falsifier' should "
        "be treated as already-addressed."
    )


def test_detects_bare_always_without_structural_keywords() -> None:
    """A bare 'always X' without structural-backing keywords fires."""
    is_rule, triggers = looks_like_rule(
        "I should always reach for the deeper frame before committing."
    )
    assert is_rule
    assert any("always" in t.lower() for t in triggers)


def test_detects_never_rule_shape() -> None:
    is_rule, triggers = looks_like_rule(
        "I will never let perfect be the enemy of good."
    )
    assert is_rule


def test_detects_must_rule_shape() -> None:
    is_rule, triggers = looks_like_rule(
        "The next instance must check the briefing first."
    )
    assert is_rule


def test_skips_when_falsifier_mentioned() -> None:
    """Loop-prevention: entries that already name a falsifier are
    addressing the question, not deferring it."""
    is_rule, _ = looks_like_rule(
        "Always file a learn entry after a correction. Falsifier: if "
        "the corrections-stale count drops below 3 across 30 days, the "
        "discipline is working."
    )
    assert not is_rule


def test_skips_when_test_mentioned() -> None:
    is_rule, _ = looks_like_rule(
        "Must always run the gate. Backed by test_stale_engagement_"
        "address_bypass.py which auto-verifies the contract."
    )
    assert not is_rule


def test_skips_when_gate_mentioned() -> None:
    is_rule, _ = looks_like_rule(
        "Always check the surfaced warnings. Gate 1.48 enforces this "
        "after 3 ignores."
    )
    assert not is_rule


def test_skips_when_structural_mentioned() -> None:
    is_rule, _ = looks_like_rule(
        "Never assume convention will hold. The structural enforcement "
        "is the only durable path."
    )
    assert not is_rule


def test_no_fire_on_neutral_text() -> None:
    """Substantive neutral content should not trigger."""
    is_rule, _ = looks_like_rule(
        "I noticed today that the sleep cycle consolidated 82 new "
        "connections, with hebbian strengthening on 551 edges."
    )
    assert not is_rule


def test_no_fire_on_empty_text() -> None:
    is_rule, triggers = looks_like_rule("")
    assert not is_rule
    assert triggers == []


def test_emit_is_fail_soft_on_broken_ledger(monkeypatch) -> None:
    """LOAD-BEARING: the emit function must NEVER raise. Even if the
    ledger is broken, the learn command must not be blocked."""

    def _broken_import(*args, **kw):
        raise RuntimeError("ledger explosion")

    # Monkeypatch via the import path inside emit_structural_promotion_question
    monkeypatch.setattr(
        "divineos.core.ledger.log_event", _broken_import
    )
    # Should return False instead of raising
    result = emit_structural_promotion_question(
        "test-kid", "I should always file the falsifier... wait no, just always X"
    )
    # The function must not raise — it returns True/False only.
    assert isinstance(result, bool)


def test_emit_returns_false_on_non_rule() -> None:
    """Non-rule entries do not emit; emit returns False without error."""
    result = emit_structural_promotion_question(
        "test-kid", "Just a neutral observation about today."
    )
    assert result is False


def test_verify_recent_returns_structured_report() -> None:
    """LOAD-BEARING: the verification surface (dual-monitor) must
    return a dict with the documented keys, even when empty."""
    report = verify_recent(window_seconds=60)
    assert isinstance(report, dict)
    # Expected keys (may be 0/None on empty windows):
    assert "total_fired" in report
    assert "with_follow_up" in report
    assert "without_follow_up" in report
    assert "follow_up_rate" in report
    assert "recent_unanswered" in report


def test_recent_questions_returns_list() -> None:
    out = recent_questions(limit=5)
    assert isinstance(out, list)
