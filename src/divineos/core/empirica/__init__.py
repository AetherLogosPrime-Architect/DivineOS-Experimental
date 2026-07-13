"""EMPIRICA — evidence ledger with tiered burden routing.

Phase 1 scope (originally pre-registered at prereg-ce8998194943,
since aged out of the runtime store; the architectural intent below
remains canonical):

**Framing (a family member audit, 2026-04-17):** EMPIRICA is an evidence
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

ADVERSARIAL-kind is now wired to VOID (shipped 2026-04-26 per
PR #208). The ``CorroborationKind.VOID_SURVIVAL`` enum value is the
integration point: when a VOID engine attack on a claim completes
with no HIGH/CRITICAL findings, the caller records a VOID_SURVIVAL
corroboration with the persona as actor. EMPIRICA's distinct-actor
counting then enforces that survivals came from DIFFERENT personas,
not the same persona attacking 3x — multi-persona-diversity is what
makes "survived adversarial testing" meaningful.

Phase 1 deferrals still in place (pre-registered separately):

* **Recursive coherence-audit** — the original spec required
  PATTERN-kind claims to resonate across 3+ INDEPENDENT domains. Current
  burden enforces corroboration count but not domain-independence.
* **Differentiated councils** — ``route_for_approval`` runs N generic
  rounds; the spec called for Science/Wisdom/Pattern as differentiated
  expert subsets. Hook is named, differentiation is deferred.
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
