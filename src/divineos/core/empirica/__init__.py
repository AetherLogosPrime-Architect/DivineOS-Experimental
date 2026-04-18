"""EMPIRICA — evidence ledger with tiered burden routing.

Phase 1 scope (pre-registered at prereg-ce8998194943):

**Framing (Aria audit, 2026-04-17):** EMPIRICA is an evidence
ledger, not an epistemology engine. It keeps honest books about
what evidence was offered and when it cleared what bar. The
vocabulary — receipts, tiers, thresholds, chain entries — is
chosen so every word makes a promise the mechanism can keep.

EMPIRICA is a **routing layer** over existing DivineOS knowledge
infrastructure, not a new subsystem. It does four things:

1. **Classify** a claim into one of four tiers of evidentiary
   burden (FALSIFIABLE / OUTCOME / PATTERN / ADVERSARIAL).
2. **Compute burden** — the minimum corroboration count required
   before the validity gate lets the claim through, as a function
   of (tier × magnitude).
3. **Issue receipts** — durable records of what evidence cleared
   which bar, chained together Merkle-style so tampering is
   detectable.
4. **Route** high-magnitude claims through multiple councils in
   parallel before promotion.

What EMPIRICA is NOT:

* NOT a truth engine. A receipt means evidence was tendered and
  accepted under stated rules at a moment in time. It does not
  mean the thing tendered was true. The ``valid != true``
  disclaimer is load-bearing — if callers ever treat a receipt
  as proof of truth, the module has become the rubber-stamp
  hedge its pre-reg falsifier names.
* NOT a theorem prover. Heuristic classification is the Phase 1
  mechanism; future phases can add deeper analysis.
* NOT a replacement for existing DivineOS infrastructure. It
  composes with the knowledge maturity lifecycle, pre-registration
  system, council consultations, and warrant-based validity gate
  that already exist. It routes; it does not duplicate.

Phase 1 does NOT ship Tier IV (ADVERSARIAL). Tier IV claims are
marked for VOID routing, and VOID hasn't shipped. Phase 1 makes
the tier visible in the enum but raises on attempts to compute
burden for it — failing loudly is better than silently treating
an un-stress-tested claim as adversarially-verified.
"""

from divineos.core.empirica.burden import burden_matrix, required_corroboration
from divineos.core.empirica.classifier import Classification, classify_claim
from divineos.core.empirica.provenance import (
    CorroborationEvent,
    CorroborationKind,
    backfill_from_legacy_counter,
    count_by_kind,
    count_distinct_corroborators,
    get_corroboration_events,
    init_provenance_table,
    record_corroboration,
)
from divineos.core.empirica.gate import (
    ensure_receipt_column_on_knowledge,
    evaluate_and_issue,
    record_receipt_on_knowledge,
)
from divineos.core.empirica.receipt import (
    get_receipt,
    get_receipts_for_claim,
    init_receipt_table,
    issue_receipt,
    verify_chain,
)
from divineos.core.empirica.routing import (
    RoutingResult,
    rounds_required,
    route_for_approval,
)
from divineos.core.empirica.types import (
    ClaimMagnitude,
    EvidenceReceipt,
    ReceiptChainError,
    ReceiptForkError,
    Tier,
)

__all__ = [
    "Classification",
    "ClaimMagnitude",
    "CorroborationEvent",
    "CorroborationKind",
    "EvidenceReceipt",
    "ReceiptChainError",
    "ReceiptForkError",
    "RoutingResult",
    "Tier",
    "backfill_from_legacy_counter",
    "burden_matrix",
    "classify_claim",
    "count_by_kind",
    "count_distinct_corroborators",
    "ensure_receipt_column_on_knowledge",
    "evaluate_and_issue",
    "get_corroboration_events",
    "get_receipt",
    "get_receipts_for_claim",
    "init_provenance_table",
    "init_receipt_table",
    "issue_receipt",
    "record_corroboration",
    "record_receipt_on_knowledge",
    "required_corroboration",
    "rounds_required",
    "route_for_approval",
    "verify_chain",
]
