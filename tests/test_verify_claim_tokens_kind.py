"""Verify-claim gate — 'tokens' claim-kind (2026-07-03).

Andrew's catch: I stated "context is at 99.7%" from a stale banner-injection
without running `divineos context-tokens` that turn. He named the fix:
"you have a tool to verify it.. so thats the issue.. is you made a claim
without verification so lets automate it so you dont need to remember."

Same shape as merge/push/tests: an assertion about a checkable external
state that requires the actual command in-turn to substantiate. This test
pins the shapes I actually fabricated in.
"""

from __future__ import annotations

from divineos.core.operating_loop.unverified_claim_detector import (
    detect_unverified_claim,
)


def _detect(text: str, tool_calls: list[str] | None = None, commands: list[str] | None = None):
    return detect_unverified_claim(
        text=text,
        tool_calls_in_turn=tool_calls or [],
        command_texts=commands or [],
    )


def test_fires_on_todays_exact_fabrication():
    """The literal shape from 2026-07-03: 'context is at 99.7%'."""
    findings = _detect("Context is at 99.7% now.")
    assert any(f.claim_kind == "tokens" for f in findings), findings


def test_fires_on_kb_of_1m_shape():
    """'996k of 1M' — one of the enumerated fabrication forms."""
    findings = _detect("I'm sitting at 996k of 1M.")
    assert any(f.claim_kind == "tokens" for f in findings), findings


def test_fires_on_full_fraction_shape():
    """The full 996,589 / 1,000,000 form."""
    findings = _detect("Now at 996,589 / 1,000,000.")
    assert any(f.claim_kind == "tokens" for f in findings), findings


def test_fires_on_percent_of_context():
    """'at 99% of context' — self-referential window claim."""
    findings = _detect("I'm at 99% of context and closing in.")
    assert any(f.claim_kind == "tokens" for f in findings), findings


def test_silenced_by_context_tokens_command_in_turn():
    """A real `divineos context-tokens` invocation this turn silences.

    Same verification-signature model as merge (`gh pr view`) and push
    (`git ls-remote`) — the presence of the tool-call substantiates.
    """
    findings = _detect(
        "Context is at 9.8% right now.",
        tool_calls=["Bash"],
        commands=["divineos context-tokens"],
    )
    # Either no tokens finding, or the finding is downgraded away —
    # detector semantics: verification-signature suppresses the surface.
    assert not any(f.claim_kind == "tokens" for f in findings), findings


def test_does_not_fire_on_bare_percentage_in_prose():
    """'The test coverage is at 87%' — unrelated percentage in prose.

    The pattern requires a context-window anchor within a short window;
    bare percentages don't fire, which is the precision guarantee.
    """
    findings = _detect("The test coverage is at 87% for that module.")
    assert not any(f.claim_kind == "tokens" for f in findings), findings


def test_hint_registered_for_tokens_kind():
    """The 'here is the way' hint must route to `divineos context-tokens`."""
    from divineos.core.operating_loop_audit import _VERIFY_CLAIM_HINT

    assert "tokens" in _VERIFY_CLAIM_HINT
    assert "context-tokens" in _VERIFY_CLAIM_HINT["tokens"]
