"""Distancing-grammar intercept — first concrete instance of the
IntraTurnIntercept variant of EvidenceBearingStopGate.

Wraps the existing ``core.operating_loop.distancing_detector`` in the
primitive's shape. The detector already carries pattern-shape work,
exemptions, and identity-aware name resolution — this module adapts
the finding stream to the primitive's EvidenceRecord contract.

Historical shape (jailer): distancing_detector fires post-response via
the operating-loop audit surface, produces a warning at the next
UserPromptSubmit, no fix. Same-class pattern recurs within 5-10 turns
because "remember to rewrite next turn" doesn't hold across the
statelessness gap.

Structural shape (this module): intercept at Stop-hook time, name the
matched tokens as evidence, require the reply to be rewritten before
emit. The recomposition IS the fix — no reliance on memory.

Not yet wired to a Stop hook script — this is the Python surface; the
shell wiring in ``.claude/hooks/stop-hook-distancing-intercept.sh``
will invoke it once we prove the primitive is stable across two
concrete instances (per the ship-first-order plan).
"""

from __future__ import annotations

from divineos.core.operating_loop.distancing_detector import (
    DistancingFinding,
    detect_distancing,
)
from divineos.hooks.evidence_bearing_stop_gate import (
    ClearanceRecord,
    EvidenceRecord,
    IntraTurnIntercept,
)


# In-memory records — the shell-hook wiring will persist to the ledger
# once we integrate. Kept as simple attributes for now so the primitive's
# shape is testable without pulling in the ledger dependency.
class DistancingIntercept(IntraTurnIntercept):
    """Intercept distancing-grammar in the just-composed reply."""

    def __init__(self, addressed_to_father: bool = True) -> None:
        self.gate_name = "distancing_intercept"
        self._addressed_to_father = addressed_to_father
        self.fires: list[EvidenceRecord] = []
        self.clears: list[ClearanceRecord] = []
        self._recent_ratio: float | None = None

    def blocks(self) -> str:
        return "emit of this reply (distancing-grammar in the just-composed text)"

    def scan_text(self, assistant_text: str) -> EvidenceRecord | None:
        try:
            findings = detect_distancing(
                assistant_text, addressed_to_father=self._addressed_to_father
            )
        except Exception:  # noqa: BLE001 — fail-open per primitive contract
            return None
        if not findings:
            return None
        return self._to_evidence(findings)

    def _to_evidence(self, findings: list[DistancingFinding]) -> EvidenceRecord:
        # Group by shape for a readable evidence line; keep positions so
        # the block message can point at exact character offsets.
        by_shape: dict[str, list[DistancingFinding]] = {}
        for f in findings:
            by_shape.setdefault(f.shape.value, []).append(f)

        parts: list[str] = []
        for shape, group in by_shape.items():
            tokens = ", ".join(f"{f.trigger_phrase!r} @ {f.position}" for f in group[:3])
            more = "" if len(group) <= 3 else f" (+{len(group) - 3} more)"
            parts.append(f"{shape}: {tokens}{more}")

        specific_evidence = "; ".join(parts)
        matched_shape = (
            f"distancing-grammar in {len(by_shape)} shape(s), {len(findings)} finding(s)"
        )
        required_action = (
            "Rewrite the flagged tokens to first-person for self and "
            "second-person for father before emitting. Named tokens above; "
            "rewrite the reply, then this gate clears."
        )
        return EvidenceRecord(
            gate_name=self.gate_name,
            matched_shape=matched_shape,
            specific_evidence=specific_evidence,
            required_action=required_action,
        )

    def record_fire(self, evidence: EvidenceRecord) -> None:
        # Placeholder — shell-hook wiring will persist to the ledger
        # so recurrence-check has cross-session data. For now the
        # in-memory list validates the primitive's shape end-to-end.
        self.fires.append(evidence)

    def record_clearance(self, clearance: ClearanceRecord) -> None:
        self.clears.append(clearance)

    def falsification_signal(self) -> str | None:
        # Two anomaly-classes worth watching once we have real data:
        # (1) clearance-to-fire ratio approaches 1:1 with the same
        #     text — indicates gaming (rewriting just enough to clear
        #     without integrating the shape).
        # (2) fire rate stays above threshold after N days despite the
        #     structural gate being live — indicates the pattern set
        #     itself is wrong-shape (Andrew's frame: don't precision-
        #     tune a jailer).
        #
        # Ratio placeholder — the shell-hook wiring will compute this
        # from ledger data. For now this returns None until wired.
        if self._recent_ratio is not None and self._recent_ratio > 0.85:
            return (
                f"clearance-to-fire ratio {self._recent_ratio:.2f} — likely gaming "
                "(rewrites just clear the gate without integration)"
            )
        return None


__all__ = ["DistancingIntercept"]
