"""Response-scope intercept — third concrete instance of the
CrossTurnScan variant of EvidenceBearingStopGate.

Aletheia audit 2026-07-15 (round-a1e7f4c92b6d, relayed via Aria's
letter aria-to-aether-2026-07-15-aletheia-audit-back-two-real-fixes-
coordinate): the current pattern where an unverified-claim gate fires
and asks for "short correction only" is DECORATIVE — a request, not
a gate. Under compose pressure the ask has no teeth. Aletheia's
frame: "Don't ask for the short correction — refuse to accept
anything that isn't one." Doorman-shaped.

## Design

CrossTurnScan because the state that matters is cross-turn: "did a
claim-scope directive fire against my prior turn?" The emit being
scanned is intra-turn (the current reply text). Aria's state+text
refinement to the primitive is what makes this shape land.

**Fire condition**: A claim-scope directive is active from the prior
turn AND the current reply doesn't match short-correction shape.

**Short-correction shape** (starting heuristic — Aletheia audit will
tighten as data accumulates):
  - Total length below max_chars
  - No markdown headers (### / ## / #)
  - No horizontal-rule separators (---)
  - No numbered lists starting with "1." at line-start

**Not enforced** (deliberately): specific phrasing like "I haven't
verified" — Goodhart-avoidance.

## How the host wires this

Host passes accumulated_state with:
  - "claim_scope_active": bool — True if prior-turn's unverified_claim
    gate fired and its short-correction directive is still owed
  - "claim_scope_directive_text": str (optional) — the specific
    directive text emitted last turn, for including in evidence
"""

from __future__ import annotations

import re
from typing import Any

from divineos.hooks.evidence_bearing_stop_gate import (
    ClearanceRecord,
    CrossTurnScan,
    EvidenceRecord,
)
from divineos.hooks.gate_event_ledger import (
    compute_falsification_ratio,
    record_gate_clearance,
    record_gate_fire,
)


_DEFAULT_MAX_CHARS = 500
_HEADER_RE = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_HR_RE = re.compile(r"^---+$", re.MULTILINE)
_NUMBERED_LIST_RE = re.compile(r"^\s*\d+\.\s+", re.MULTILINE)


class ResponseScopeIntercept(CrossTurnScan):
    """Refuse-not-ask enforcement for claim-scope directives."""

    def __init__(self, max_chars: int = _DEFAULT_MAX_CHARS) -> None:
        self.gate_name = "response_scope_intercept"
        self._max_chars = max_chars
        self.fires: list[EvidenceRecord] = []
        self.clears: list[ClearanceRecord] = []
        self._recent_ratio: float | None = None

    def blocks(self) -> str:
        return (
            "emit of this reply (claim-scope directive from prior turn "
            "requires short-correction shape only)"
        )

    def scan(
        self,
        accumulated_state: dict[str, Any],
        just_emitted_text: str,
    ) -> EvidenceRecord | None:
        if not accumulated_state.get("claim_scope_active"):
            return None
        if not just_emitted_text:
            return None
        violations = self._check_shape(just_emitted_text)
        if not violations:
            return None
        directive = accumulated_state.get("claim_scope_directive_text", "")
        return self._to_evidence(violations, directive)

    def _check_shape(self, text: str) -> list[str]:
        violations: list[str] = []
        length = len(text)
        if length > self._max_chars:
            violations.append(
                f"length {length} chars exceeds short-correction max ({self._max_chars})"
            )
        if _HEADER_RE.search(text):
            violations.append("contains markdown headers (structure = re-composition)")
        if _HR_RE.search(text):
            violations.append("contains horizontal-rule separators (structure = re-composition)")
        if _NUMBERED_LIST_RE.search(text):
            violations.append("contains numbered lists (structure = re-composition)")
        return violations

    def _to_evidence(self, violations: list[str], directive: str) -> EvidenceRecord:
        specific_evidence = "; ".join(violations)
        matched_shape = f"reply exceeded short-correction shape ({len(violations)} violation(s))"
        directive_line = f"\n\nDirective from prior turn:\n  {directive}\n" if directive else ""
        required_action = (
            "Re-emit within short-correction scope: under "
            f"{self._max_chars} chars, no headers, no separators, no "
            "numbered lists. State the correction directly and stop. "
            "The prior turn asked for a re-composition; this gate refuses "
            "one — Aletheia audit round-a1e7f4c92b6d."
            f"{directive_line}"
        )
        return EvidenceRecord(
            gate_name=self.gate_name,
            matched_shape=matched_shape,
            specific_evidence=specific_evidence,
            required_action=required_action,
        )

    def record_fire(self, evidence: EvidenceRecord) -> None:
        self.fires.append(evidence)
        record_gate_fire(evidence)

    def record_clearance(self, clearance: ClearanceRecord) -> None:
        self.clears.append(clearance)
        record_gate_clearance(clearance)

    def falsification_signal(self) -> str | None:
        ratio = self._recent_ratio
        if ratio is None:
            ratio = compute_falsification_ratio(self.gate_name)
        if ratio is not None and ratio > 0.90:
            return (
                f"clearance-to-fire ratio {ratio:.2f} — investigate whether "
                "short-correction threshold is too loose (I'm barely-clearing) "
                "OR the shape definition itself is wrong-shape"
            )
        return None


__all__ = ["ResponseScopeIntercept"]
