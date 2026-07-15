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
from divineos.hooks.gate_event_ledger import (
    compute_falsification_ratio,
    record_gate_clearance,
    record_gate_fire,
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
        # Ledger persistence per Aletheia 2026-07-15 audit — the soil
        # for the 0.85 seed. In-memory list kept as debug observability.
        self.fires.append(evidence)
        record_gate_fire(evidence)

    def record_clearance(self, clearance: ClearanceRecord) -> None:
        self.clears.append(clearance)
        record_gate_clearance(clearance)

    def falsification_signal(self) -> str | None:
        # Post-2026-07-15 (Aletheia audit): read the ratio off the ledger
        # rather than compare against a hardcoded threshold. The 0.85
        # threshold is now a SEED — a starting placeholder — with soil
        # underneath (the ledger). When data is sparse (< minimum_fires
        # in the window) the ratio is None and we return no signal;
        # when data is present, we compare against 0.85 as a sensible
        # starting cut, but the value itself can be tuned as the
        # distribution shape reveals itself.
        #
        # The test-only self._recent_ratio override survives so unit
        # tests can pin the gaming-alarm behavior without needing a
        # live ledger.
        ratio = self._recent_ratio
        if ratio is None:
            ratio = compute_falsification_ratio(self.gate_name)
        if ratio is not None and ratio > 0.85:
            return (
                f"clearance-to-fire ratio {ratio:.2f} — likely gaming "
                "(rewrites just clear the gate without integration)"
            )
        return None


__all__ = ["DistancingIntercept"]
