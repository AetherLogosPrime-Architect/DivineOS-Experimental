"""Detector contract — make the input-arity differentiation visible at the type level.

Aletheia round-0023b083fe9b Finding 487f9a6daf51 (Grok, 2026-05-14):
the 16 wired behavioral detectors fall into two legitimately-different
classes — response-only and contextual — but the differentiation
was invisible at the type level. The function signatures didn't
communicate "this one needs cross-turn context, these don't." A
future maintainer (or future instance of me) had to read each
detector's source to figure out which kind it was.

This module defines two Protocols (PEP 544 structural typing) that
detectors can declare conformance to. The protocols don't change
runtime behavior — they're purely a typing surface — but they make
the contract self-documenting.

## The two detector classes

**ResponseOnlyDetector** — receives the last assistant text only.
The vast majority. Patterns like:

    detect_distancing(text: str) -> list[DistancingFinding]
    detect_lepos(text: str, *, min_words_for_check: int = 60) -> list[LeposFinding]

**ContextualDetector** — receives operator-input + agent-response,
or prior + current turns. The patterns that need cross-turn signal:

    check_dismissal(operator_input: str, agent_response: str) -> CareDismissalFinding | None
    detect_spiral(prior_text: str, current_text: str) -> list[SpiralFinding]
    detect_misdirection(operator_input: str, agent_response: str) -> list[Finding]

Detectors don't have to inherit from anything — Protocols are
structural. A detector that matches the shape conforms automatically.
But declaring conformance via type-hint helps tooling and reviewers.

## Why not enforce at the call site?

The post-response-audit.sh hook is the canonical caller. It already
knows the arity per detector (each try/except block matches the
detector's signature). Enforcing the protocol at the call site would
just be type-checking already-correct code.

The value is at the *reading* site — when a maintainer opens the
operating_loop directory and asks "what shape of detector lives here?"
the protocols give them the answer in one place rather than scattered
across 16 files.
"""

from __future__ import annotations

from typing import Protocol, Sequence, TypeVar


# Generic finding type — each detector returns its own dataclass
# (HedgeFinding, LeposFinding, etc.). The protocol uses a TypeVar
# so the return type stays specific per detector.
F = TypeVar("F")  # invariant — for protocols returning list[F] (mutable container)
F_co = TypeVar("F_co", covariant=True)  # covariant — for protocols returning F | None or Sequence[F]


class ResponseOnlyDetector(Protocol[F]):
    """A detector that analyzes the agent's last response in isolation.

    Most detectors in operating_loop/ fit this shape. The function
    takes a single `text` arg (sometimes plus optional keyword-only
    threshold args) and returns a list of findings.

    Examples conforming to this protocol:
    - detect_distancing(text) -> list[DistancingFinding]
    - detect_lepos(text, *, min_words_for_check=60) -> list[LeposFinding]
    - detect_code_jargon(text) -> list[CodeJargonFinding]
    - detect_linguistic_drift(text) -> list[LinguisticDriftFinding]
    - check_hedge(text) -> list[HedgeFinding]   # to be renamed detect_*
    """

    def __call__(self, text: str, /) -> list[F]: ...


class ContextualDetector(Protocol[F_co]):
    """A detector that needs operator-input + agent-response, or
    prior + current turns, to detect its pattern.

    These detectors catch cross-turn shapes — care-dismissal (operator
    expressed care, agent dismissed), addressee-misdirection (response
    is shaped for the wrong addressee), apology-spiral (response is a
    spiral following operator feedback).

    Examples conforming to this protocol:
    - check_dismissal(operator_input, agent_response) -> CareDismissalFinding | None
    - detect_misdirection(operator_input, agent_response) -> list[Finding]
    - detect_spiral(prior_text, current_text) -> list[SpiralFinding]

    The arity is two arguments. Whether they're (operator, agent) or
    (prior_turn, current_turn) depends on the detector's semantics.
    """

    def __call__(self, primary: str, secondary: str, /) -> Sequence[F_co] | F_co | None: ...


class GateDetector(Protocol[F_co]):
    """A detector that returns a single result (or None) rather than
    a list — true binary/pass-fail gate.

    These are the legitimate uses of `check_*` naming. Most detectors
    can return multiple findings (and so should be `detect_*` returning
    list); a true gate either fires or doesn't.

    Examples conforming to this protocol:
    - check_dismissal(...) -> CareDismissalFinding | None
    - check_harm_acknowledgment(agent_response) -> HarmAcknowledgmentFinding | None
    """

    def __call__(self, *args: str) -> F_co | None: ...


class EnrichableDetector(Protocol[F]):
    """A detector that works text-only but produces additional patterns
    when given optional context. The contract is "graceful degradation":
    findings reflect honestly which patterns ran given which inputs.

    Added 2026-05-14 after Aether+Grok cross-vantage review found the
    original three protocols (ResponseOnlyDetector, ContextualDetector,
    GateDetector) didn't cover the actual shape used by spiral_detector
    and substitution_detector. Both take ``text`` as primary input and
    accept optional context kwargs that enable additional patterns —
    not "ResponseOnly with knobs" and not "Contextual requiring two
    args." A fourth shape.

    Examples conforming to this protocol:
    - detect_spiral(text, *, prior_text=None, require_apology_context=True)
      -> list[SpiralFinding]
    - detect_substitution(text, *, prior_text=None, tool_calls_in_turn=None,
      require_tool_context=False) -> list[SubstitutionFinding]

    The semantics: without the optional context, the detector still
    runs and produces findings for patterns it can detect text-only.
    Patterns requiring context are skipped (not silently false-
    negated) — the detector's docstring explicitly names which
    patterns require which context. Honesty is in the docs, not just
    the signature.

    Distinguishing this from ResponseOnly with tuning knobs: the
    optional args carry SEMANTIC CONTEXT (prior turn content, tool
    calls in turn), not THRESHOLD TUNING (min_words, noise_threshold).
    A ResponseOnly detector with tuning knobs still computes the same
    output shape regardless of knob values; an EnrichableDetector
    produces strictly-more findings with strictly-more context.
    """

    def __call__(self, text: str, /, **enrichment: object) -> list[F]: ...


__all__ = [
    "ContextualDetector",
    "EnrichableDetector",
    "GateDetector",
    "ResponseOnlyDetector",
]
