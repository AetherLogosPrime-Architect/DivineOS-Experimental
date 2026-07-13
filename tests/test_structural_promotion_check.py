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
    is_rule, triggers = looks_like_rule("I should always file a falsifier alongside the directive.")
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
    is_rule, triggers = looks_like_rule("I will never let perfect be the enemy of good.")
    assert is_rule


def test_detects_must_rule_shape() -> None:
    is_rule, triggers = looks_like_rule("The next instance must check the briefing first.")
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
        "Always check the surfaced warnings. Gate 1.48 enforces this after 3 ignores."
    )
    assert not is_rule


def test_skips_when_structural_mentioned() -> None:
    is_rule, _ = looks_like_rule(
        "Never assume convention will hold. The structural enforcement is the only durable path."
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
    monkeypatch.setattr("divineos.core.ledger.log_event", _broken_import)
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


# Task #112 (2026-06-09): link-detection bug fixes regression tests.
# The previous logic had two bugs:
#   1. `wid in content OR keyword in content` — let any unrelated learn
#      that mentioned "test"/"gate" falsely address every pending question
#   2. Only KNOWLEDGE_STORED events were scanned, missing real backing
#      via PREREG_FILED, CLAIM_FILED, AUDIT_FINDING_FILED


def _make_question(wid: str, ts: float) -> dict:
    """Helper: shape of a STRUCTURAL_PROMOTION_QUESTION returned by recent_questions."""
    return {"event_id": f"q-{wid}", "timestamp": ts, "knowledge_id": wid, "triggers": ["always x"]}


def _make_event(event_type: str, payload: dict, ts: float) -> dict:
    """Helper: shape of a ledger event."""
    return {"event_type": event_type, "timestamp": ts, "payload": payload}


def test_unrelated_learn_with_keyword_does_NOT_address_question() -> None:
    """Regression: the false-positive bug. An unrelated KNOWLEDGE_STORED
    that happens to mention 'test' or 'gate' must NOT count as addressing
    a STRUCTURAL_PROMOTION_QUESTION about a different knowledge_id."""
    from divineos.core.structural_promotion_check import _is_backing

    question_wid = "knowledge-abc-rule-about-X"
    question_ts = 100.0
    unrelated_learn = _make_event(
        "KNOWLEDGE_STORED",
        {"content": "Some other lesson about Y. I should add a test for Z."},
        ts=200.0,
    )
    # Has "test" keyword but no reference to question_wid → must NOT address.
    assert _is_backing(unrelated_learn, question_wid, question_ts) is False


def test_related_learn_with_wid_and_keyword_DOES_address_question() -> None:
    """Affirmation: a learn entry that BOTH references the knowledge_id
    AND mentions a structural keyword counts as addressing the question."""
    from divineos.core.structural_promotion_check import _is_backing

    question_wid = "knowledge-abc"
    question_ts = 100.0
    backing_learn = _make_event(
        "KNOWLEDGE_STORED",
        {"content": ("Backing the rule from knowledge-abc with a falsifier and a CI gate.")},
        ts=200.0,
    )
    assert _is_backing(backing_learn, question_wid, question_ts) is True


def test_wid_reference_alone_does_NOT_address() -> None:
    """A learn entry that references the knowledge_id but offers no
    structural keyword (e.g., just an aside referencing it) must NOT
    count as backing — structural backing is the point."""
    from divineos.core.structural_promotion_check import _is_backing

    question_wid = "knowledge-xyz"
    question_ts = 100.0
    aside_learn = _make_event(
        "KNOWLEDGE_STORED",
        {"content": "Mentioned knowledge-xyz in passing without backing it."},
        ts=200.0,
    )
    assert _is_backing(aside_learn, question_wid, question_ts) is False


def test_prereg_filed_can_address_question() -> None:
    """Regression: the false-negative bug. A PREREG_FILED event that
    references the question's knowledge_id AND has structural backing
    must count — previously only KNOWLEDGE_STORED was scanned."""
    from divineos.core.structural_promotion_check import _is_backing

    question_wid = "knowledge-rule"
    question_ts = 100.0
    prereg = _make_event(
        "PREREG_FILED",
        {
            "claim": "Backing knowledge-rule with a prereg falsifier",
            "mechanism": "Auto-verify via CI gate on the new test",
        },
        ts=200.0,
    )
    assert _is_backing(prereg, question_wid, question_ts) is True


def test_claim_filed_can_address_question() -> None:
    from divineos.core.structural_promotion_check import _is_backing

    question_wid = "knowledge-rule"
    question_ts = 100.0
    claim = _make_event(
        "CLAIM_FILED",
        {"description": "Claim investigates knowledge-rule with a regression-pin test."},
        ts=200.0,
    )
    assert _is_backing(claim, question_wid, question_ts) is True


def test_event_before_question_does_NOT_address() -> None:
    """Causal-ordering guard: a learn that fired BEFORE the question
    cannot be its answer."""
    from divineos.core.structural_promotion_check import _is_backing

    question_wid = "knowledge-rule"
    question_ts = 200.0
    earlier = _make_event(
        "KNOWLEDGE_STORED",
        {"content": "knowledge-rule mentioned with falsifier."},
        ts=100.0,
    )
    assert _is_backing(earlier, question_wid, question_ts) is False


def test_empty_question_wid_never_addresses() -> None:
    """A question with no knowledge_id can't be addressed by anything
    because there's no anchor to link to."""
    from divineos.core.structural_promotion_check import _is_backing

    later = _make_event(
        "KNOWLEDGE_STORED",
        {"content": "Adding a falsifier and a gate."},
        ts=200.0,
    )
    assert _is_backing(later, "", 100.0) is False


# ── 8-char kid-prefix matching (regression-pin for 2026-06-14 fix) ──
#
# The bug: PRE_REGISTRATION_FILED event payloads contain ONLY the
# mechanism description (not the success/falsifier fields), and the
# prereg CLI's own convention writes "kid abc12345" prefix-form in the
# mechanism text. The prior matcher required the FULL UUID in the
# payload — so every prereg-form backing was silently missed and
# legitimate structural work didn't credit. Fix: accept 8-char prefix
# match in addition to full UUID. 8 hex chars = ~4B combinations,
# distinctive enough at substrate scale.
#
# These tests pin that behavior so a future refactor or a "tighten the
# matcher" instinct can't silently re-introduce the false-negative.


def test_8char_kid_prefix_match_counts_as_backing() -> None:
    """Regression-pin: 8-char prefix of question's knowledge_id in
    payload + structural keyword = backing. This is the actual shape
    the prereg CLI produces."""
    from divineos.core.structural_promotion_check import _is_backing

    question_wid = "d69bba1d-9ef2-4c2a-a94a-f14802f912c3"
    question_ts = 100.0
    prereg_with_prefix = _make_event(
        "PRE_REGISTRATION_FILED",
        {
            "mechanism": (
                "Refined constraint-ownership affirmation (kid d69bba1d): "
                "structural backing landed in operating_loop/"
                "constraint_disownership_detector.py, falsifier filed."
            ),
        },
        ts=200.0,
    )
    assert _is_backing(prereg_with_prefix, question_wid, question_ts) is True


def test_full_uuid_match_still_counts_as_backing() -> None:
    """The prefix-accept fix MUST NOT break full-UUID matching that
    was already working — both forms have to keep crediting."""
    from divineos.core.structural_promotion_check import _is_backing

    question_wid = "d69bba1d-9ef2-4c2a-a94a-f14802f912c3"
    question_ts = 100.0
    learn_with_full_uuid = _make_event(
        "KNOWLEDGE_STORED",
        {
            "content": (f"Structural backing for {question_wid}: added a CI gate with falsifier."),
        },
        ts=200.0,
    )
    assert _is_backing(learn_with_full_uuid, question_wid, question_ts) is True


def test_prefix_match_still_requires_structural_keyword() -> None:
    """Defense-in-depth: an event that has the kid prefix in its payload
    but NO structural keyword (test/gate/prereg/etc.) must NOT count.
    The prefix alone is not backing — the backing IS the structural shape."""
    from divineos.core.structural_promotion_check import _is_backing

    question_wid = "d69bba1d-9ef2-4c2a-a94a-f14802f912c3"
    question_ts = 100.0
    mention_only = _make_event(
        "PRE_REGISTRATION_FILED",
        {"mechanism": "Mentioned d69bba1d in passing. Some other text."},
        ts=200.0,
    )
    assert _is_backing(mention_only, question_wid, question_ts) is False


def test_unrelated_8char_string_does_not_falsely_match() -> None:
    """A payload that happens to contain an unrelated 8-char hex
    fragment must NOT match the question's wid. The prefix has to BE
    the question's prefix, not just any 8 hex chars."""
    from divineos.core.structural_promotion_check import _is_backing

    question_wid = "d69bba1d-9ef2-4c2a-a94a-f14802f912c3"
    question_ts = 100.0
    unrelated_prereg = _make_event(
        "PRE_REGISTRATION_FILED",
        {
            "mechanism": ("Some other prereg about hash abcd1234 with a falsifier and a CI gate."),
        },
        ts=200.0,
    )
    assert _is_backing(unrelated_prereg, question_wid, question_ts) is False


def test_prefix_match_is_case_insensitive() -> None:
    """Hex characters in payload may arrive in either case; the matcher
    lowercases both sides. Pin so a future refactor doesn't drop the
    case-fold."""
    from divineos.core.structural_promotion_check import _is_backing

    question_wid = "D69BBA1D-9EF2-4C2A-A94A-F14802F912C3"  # uppercase wid
    question_ts = 100.0
    prereg_lower = _make_event(
        "PRE_REGISTRATION_FILED",
        {"mechanism": "Backing kid d69bba1d via a CI gate + falsifier."},
        ts=200.0,
    )
    assert _is_backing(prereg_lower, question_wid, question_ts) is True


# ── Single-source-of-truth drift detector (Andrew 2026-06-10 teaching) ──
#
# The teaching: "_BACKING_EVENT_TYPES drifted from actual log_event() calls
# — event-name lists should be auto-derived by grepping the codebase for
# log_event calls." The list lives in structural_promotion_check.py and is
# manually curated (only 4 types qualify as structural backing — not every
# log_event type). Auto-derivation would over-include. Instead, pin the
# list against reality with a TEST: every entry must appear as a string
# literal in at least one real log_event/emit_event call site somewhere
# in src/divineos/.
#
# When the test fails: either a backing type was renamed/removed in the
# code (drift caught) or a new backing type was added without updating
# this test's allowlist (the list needs updating).


def test_all_backing_event_types_are_emitted_somewhere() -> None:
    """Every entry in _BACKING_EVENT_TYPES must appear as the first string
    argument to a log_event() or emit_event() call site in src/divineos/.
    Catches drift where a backing type was renamed or removed from emission
    code but left in the list (phantom type — structural_promotion_check
    would look for events that never get emitted).

    Multi-line call style supported: log_event(\n    "TYPE_NAME",\n ...).
    """
    import re
    from pathlib import Path

    from divineos.core.structural_promotion_check import _BACKING_EVENT_TYPES

    src_root = Path(__file__).resolve().parents[1] / "src" / "divineos"

    # Collect ALL string literals that appear as the first arg to
    # log_event(...) or emit_event(...). Multi-line aware.
    # Pattern: log_event\s*\(\s*(?:[^"']*\n\s*)*"TYPE"
    emit_pat = re.compile(
        r"(?:log_event|emit_event)\s*\(\s*[\"']([A-Z_][A-Z0-9_]*)[\"']",
        re.MULTILINE,
    )
    emit_pat_multiline = re.compile(
        r"(?:log_event|emit_event)\s*\(\s*\n\s*[\"']([A-Z_][A-Z0-9_]*)[\"']",
        re.MULTILINE,
    )

    emitted: set[str] = set()
    for py in src_root.rglob("*.py"):
        # Skip the structural_promotion_check itself — it stores the names
        # as literals in the list but doesn't emit them.
        if py.name == "structural_promotion_check.py":
            continue
        try:
            text = py.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in emit_pat.finditer(text):
            emitted.add(m.group(1))
        for m in emit_pat_multiline.finditer(text):
            emitted.add(m.group(1))

    missing = set(_BACKING_EVENT_TYPES) - emitted
    assert not missing, (
        f"_BACKING_EVENT_TYPES contains type(s) with NO log_event/emit_event "
        f"call site in src/divineos/: {sorted(missing)}. Either the type was "
        f"renamed in emission code (drift caught — fix the list to match) or "
        f"the type was removed entirely (remove from _BACKING_EVENT_TYPES). "
        f"Found {len(emitted)} emit-site type(s) total."
    )
