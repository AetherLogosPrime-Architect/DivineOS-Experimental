"""EMPIRICA gate — single entry point orchestrating classify + burden + route + issue.

# PHASE_1_STAGED — Zero non-test callers by design. The gate is
# intentionally not called from production code paths in Phase 1; it
# is available for per-call-site opt-in. Adding the first caller is
# a deliberate step that must follow the caller contract in
# docs/empirica-caller-contract.md BEFORE it ships. The contract
# must be reviewed by external audit because the first caller sets
# the pattern every subsequent caller will copy. This marker signals
# to dead-architecture sweeps that the absent-callers state is
# intentional-for-now, not overlooked. When the first opt-in lands,
# remove this marker.

This is the wiring layer. The four core modules (types, classifier,
burden, routing, receipt) each do one thing well. This module
composes them into a single decision:

    "Given a knowledge entry, does the evidence ledger sanction it?"

Return shape:

* ``EvidenceReceipt`` — sanctioned. Receipt is persisted in
  ``evidence_receipts`` and its ID should be stored on the
  knowledge entry's ``receipt_id`` column.
* ``None`` — NOT sanctioned. Either burden not met or council
  rejected. Caller must NOT treat the knowledge entry as
  EMPIRICA-validated. The entry may still pass the existing
  validity gate; EMPIRICA is additive, not replacement.

## Upstream dependency: trust_tiers source-tagging

The classifier's ``kt=fact + source=measured → FALSIFIABLE`` rule
(classifier.py, rule set) depends on the caller having correctly
tagged the source as ``measured`` via ``trust_tiers``. If upstream
source-tagging is wrong, EMPIRICA cannot detect it — the rigor of
the four-tier classification has an upstream dependency on the
honesty of source attribution. Callers must not pass ``measured``
loosely; the demotion-on-missing-pointer check is the only downstream
defense, and it does not catch mis-tagged sources that do have a
pointer. Flagged in the 2026-04-18 external audit (Claude 4.7).

## Layering, not replacement

EMPIRICA runs ON TOP OF the existing validity gate
(``_passes_validity_gate`` in ``knowledge_maintenance``) — it does
not replace it. An entry that passes EMPIRICA can still fail the
underlying gate. An entry that fails EMPIRICA should not be
promoted further even if it would pass the underlying gate alone.

This layering means Phase 1 is additive — existing code paths keep
working exactly as they did. New behavior (tier-aware burden,
multi-council for high magnitude, receipts) is opt-in per call site.

## The valid != true invariant

An ``EvidenceReceipt`` return value proves the claim has
ACCUMULATED sufficient evidence for its tier and magnitude. It
does not prove the claim is TRUE. Callers must preserve this
distinction in UI and messaging. The pre-reg falsifier names
"callers use classification success as a stand-in for 'this is
true'" as a failure mode — caught here at the wiring layer if
anywhere. Aria's post-audit framing: *"Honest bookkeeping is the
grand thing. The other name was borrowing dignity it hadn't
earned."* The rename from ``GnosisWarrant`` to ``EvidenceReceipt``
(2026-04-17) removed the vocabulary that was fighting this
invariant.
"""

from __future__ import annotations

from loguru import logger

from divineos.core.empirica.burden import required_corroboration
from divineos.core.empirica.classifier import Classification, classify_claim
from divineos.core.empirica.receipt import issue_receipt
from divineos.core.empirica.routing import RoutingResult, route_for_approval
from divineos.core.empirica.types import ClaimMagnitude, EvidenceReceipt


def evaluate_and_issue(
    claim_id: str,
    content: str,
    corroboration_count: int,
    knowledge_type: str = "",
    source: str = "",
    explicit_magnitude: ClaimMagnitude | None = None,
    artifact_pointer: str | None = None,
    convene_fn: object = None,
) -> tuple[EvidenceReceipt | None, Classification, RoutingResult | None]:
    """Run a knowledge entry through the full EMPIRICA pipeline.

    Returns a 3-tuple ``(receipt, classification, routing)`` so
    callers can audit every decision the gate made, not just the
    final answer:

    * ``receipt`` — the issued receipt, or None if not sanctioned.
    * ``classification`` — the tier + magnitude + reason the
      classifier assigned. Always populated.
    * ``routing`` — the council routing result. None if magnitude
      didn't require council review; the RoutingResult otherwise.

    Arguments:

    * ``claim_id`` — the knowledge entry ID. Used as the receipt's
      claim_id and for logging.
    * ``content`` — the claim text. Fed to the classifier.
    * ``corroboration_count`` — the current corroboration count on
      the knowledge entry. Used to check burden.
    * ``knowledge_type`` / ``source`` — classifier hints.
    * ``explicit_magnitude`` — override for callers that know the
      magnitude (e.g. pre-reg-filed claims).
    * ``convene_fn`` — test-only injection for the council (see
      routing.py for the contract).

    Tier.ADVERSARIAL raises NotImplementedError at the burden step —
    Phase 1 doesn't implement adversarial gating (waits for VOID).
    """
    classification = classify_claim(
        content=content,
        knowledge_type=knowledge_type,
        source=source,
        explicit_magnitude=explicit_magnitude,
        artifact_pointer=artifact_pointer,
    )

    # Burden check — does the entry have enough corroboration for its
    # tier and magnitude? This is the cheap gate; run it first.
    burden = required_corroboration(classification.tier, classification.magnitude)
    if corroboration_count < burden:
        logger.info(
            "EMPIRICA gate REJECT (burden): claim {} tier={} mag={} corroboration={} < required={}",
            claim_id[:12],
            classification.tier.value,
            classification.magnitude.name,
            corroboration_count,
            burden,
        )
        return None, classification, None

    # Route through councils if magnitude requires it.
    routing = route_for_approval(
        claim_content=content,
        magnitude=classification.magnitude,
        convene_fn=convene_fn,
    )
    if not routing.approved:
        logger.info(
            "EMPIRICA gate REJECT (council): claim {} tier={} mag={} routing={}",
            claim_id[:12],
            classification.tier.value,
            classification.magnitude.name,
            routing.rationale,
        )
        return None, classification, routing

    # Both gates passed — issue the receipt. Pass the classification's
    # artifact_pointer through so it's stored on the receipt (per
    # prereg-e210f5fb78c9 falsifier #4: the pointer must be STORED,
    # not just used to gate then dropped).
    receipt = issue_receipt(
        claim_id=claim_id,
        tier=classification.tier,
        magnitude=classification.magnitude,
        corroboration_count=corroboration_count,
        council_count=routing.council_count,
        artifact_pointer=classification.artifact_pointer,
    )
    logger.info(
        "EMPIRICA gate PASS: claim {} -> receipt {} tier={} mag={} "
        "corroboration={} (burden={}) councils={}",
        claim_id[:12],
        receipt.receipt_id,
        classification.tier.value,
        classification.magnitude.name,
        corroboration_count,
        burden,
        routing.council_count,
    )
    return receipt, classification, routing


def ensure_receipt_column_on_knowledge() -> None:
    """Add ``receipt_id`` column to the knowledge table if missing.

    Knowledge entries gain an optional reference to the most recent
    EMPIRICA receipt issued for them. NULL for entries not gated by
    EMPIRICA — explicitly nullable to keep the migration purely
    additive (all existing rows start at NULL).

    Also handles the 2026-04-17 rename migration: if an older
    ``warrant_id`` column exists (from pre-rename PR #126
    development DBs) it is renamed to ``receipt_id`` via ALTER
    TABLE RENAME COLUMN (SQLite 3.25+).

    Idempotent — safe to call at every startup.
    """
    import sqlite3

    from divineos.core._ledger_base import get_connection

    conn = get_connection()
    try:
        # Check for legacy warrant_id column first; rename if present.
        try:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(knowledge)").fetchall()}
            if "warrant_id" in cols and "receipt_id" not in cols:
                conn.execute("ALTER TABLE knowledge RENAME COLUMN warrant_id TO receipt_id")
                conn.commit()
                logger.info("Renamed knowledge.warrant_id -> knowledge.receipt_id")
        except sqlite3.OperationalError as e:
            logger.debug(f"Legacy warrant_id rename skipped: {e}")

        try:
            conn.execute("ALTER TABLE knowledge ADD COLUMN receipt_id TEXT DEFAULT NULL")
            conn.commit()
            logger.debug("Added receipt_id column to knowledge table")
        except sqlite3.OperationalError:
            # Column already exists — expected on second+ calls.
            pass
    finally:
        conn.close()


def record_receipt_on_knowledge(knowledge_id: str, receipt_id: str) -> None:
    """Persist a receipt reference on a knowledge entry.

    Separate from ``evaluate_and_issue`` so callers can choose
    WHETHER to link the receipt back to knowledge (most will; some
    auditing paths may not want to mutate the knowledge row).
    """
    from divineos.core._ledger_base import get_connection

    ensure_receipt_column_on_knowledge()
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE knowledge SET receipt_id = ? WHERE knowledge_id = ?",
            (receipt_id, knowledge_id),
        )
        conn.commit()
    finally:
        conn.close()


__all__ = [
    "ensure_receipt_column_on_knowledge",
    "evaluate_and_issue",
    "record_receipt_on_knowledge",
]
