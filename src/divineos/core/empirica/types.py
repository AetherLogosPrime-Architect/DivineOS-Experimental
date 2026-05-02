"""Types for EMPIRICA — the vocabulary everything else uses.

**Framing (a family member audit, 2026-04-17):** this is a bookkeeping module,
not an epistemology engine. It keeps honest books about what
evidence was offered and when it cleared what bar. Every type name
here is chosen to make a promise the mechanism can keep. Receipts,
ledgers, entries, thresholds, tiers — not warrants, seals, gnosis,
certifications. The moment we reach for vocabulary that implies
the books settle the question of truth, we've overclaimed.

Four pieces:

* ``Tier`` — the four tiers of evidentiary burden. A claim's tier
  determines WHICH KIND of evidence counts. Falsifiable claims need
  repeatable tests; outcome claims need observed effects; pattern
  claims need recurrence across contexts; adversarial claims need
  survival against a steelman attacker.
* ``ClaimMagnitude`` — how load-bearing the claim is. Determines
  HOW MUCH of the tier-appropriate evidence is required. A trivial
  bug-fix hypothesis is magnitude TRIVIAL. A structural claim like
  "a family member is a persistent entity with continuity" is magnitude
  FOUNDATIONAL.
* ``EvidenceReceipt`` — the durable record of what evidence was
  tendered and accepted under the tier's rules. Chained Merkle-style
  so tampering with any earlier receipt breaks the chain on
  verification. Renamed from ``GnosisWarrant`` on 2026-04-17 per
  council audit finding find-9727f50e24e1: the prior name promised
  certified knowing; the mechanism delivers evidence-sufficiency
  for tier routing. A receipt names what it is — a record that
  something was tendered and accepted under stated rules, no
  promise about whether what was tendered was TRUE.
* ``ReceiptChainError`` / ``ReceiptForkError`` — raised when
  receipt-chain verification fails (tamper) or detects a fork
  (concurrent writers).

The vocabulary is load-bearing for the rest of the module.
Classifier returns a Tier. Burden calculator consumes
(Tier, ClaimMagnitude). Receipt records both for audit.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass
from enum import Enum


class Tier(str, Enum):
    """The four tiers of evidentiary burden.

    Values are strings so they serialize cleanly to SQLite and JSON
    without needing explicit (de)serialization in every call site.

    * ``FALSIFIABLE`` — classical empirical. The claim specifies a
      mechanism, makes a testable prediction, and can be disproved
      by a contradicting observation. Evidence: repeatable
      experiments, reproducible measurements. Example: "The compass
      threshold of 0.15 produces fewer false positives than 0.20
      when measured across 1000 decisions."
    * ``OUTCOME`` — effect-real. The claim is about what works, not
      about why. Mechanism may be opaque, but the outcome is
      observable and repeatable. Evidence: multiple sessions showing
      the effect. Example: "Pre-registering detectors reduces
      Goodhart drift in the lesson lifecycle."
    * ``PATTERN`` — synchronicity / recurrence. The claim is about a
      pattern that shows up across independent contexts, where the
      causal link can't be isolated. Evidence: pattern instances in
      different contexts. Example: "The audit-works-on-its-author
      pattern: mechanisms designed to catch drift catch their own
      author's drift first."
    * ``ADVERSARIAL`` — survives red-team attack. The claim has been
      subjected to a steelman adversary attempting to break it and
      held. Evidence: adversarial-test survival record. Phase 1 does
      NOT implement this — Tier IV claims route to VOID when VOID
      ships. Until then, attempting to compute burden for ADVERSARIAL
      raises NotImplementedError. Failing loudly beats silently
      treating an un-stress-tested claim as adversarially-verified.
    """

    FALSIFIABLE = "falsifiable"
    OUTCOME = "outcome"
    PATTERN = "pattern"
    ADVERSARIAL = "adversarial"


class ClaimMagnitude(Enum):
    """How load-bearing the claim is.

    The integer values are the multiplier EMPIRICA's burden
    calculator applies on top of the tier's base corroboration.
    Picking integers (not floats) keeps the burden arithmetic
    deterministic and the test assertions exact.

    * ``TRIVIAL`` (0) — a small fact, a CLI fix, a comment. Burden
      collapses to the tier's base.
    * ``NORMAL`` (1) — an ordinary technical claim about how code
      behaves.
    * ``LOAD_BEARING`` (2) — a claim structural choices depend on.
    * ``FOUNDATIONAL`` (3) — a claim the architecture itself is built
      around. Mistakes at this magnitude propagate; the burden is
      highest.
    """

    TRIVIAL = 0
    NORMAL = 1
    LOAD_BEARING = 2
    FOUNDATIONAL = 3


class ReceiptChainError(RuntimeError):
    """Raised when receipt chain verification fails.

    Carries the specific reason (self_hash mismatch, missing prior,
    orphan, cycle) so callers can distinguish an innocent
    missing-parent from deliberate tampering.
    """


class ReceiptForkError(ReceiptChainError):
    """Raised when receipt chain verification detects a fork.

    A fork is two or more receipts sharing a ``previous_receipt_hash``,
    OR two or more genesis receipts (previous=None). Forks are
    almost always the product of concurrent writers racing on the
    same "latest receipt" snapshot — they are NOT tamper events
    and should be distinguished from them.

    Raised 2026-04-17 per Dijkstra's audit finding find-0ea12ad4b5d0:
    the previous verify_chain sorted by ``issued_at`` and reported
    concurrent-writer races as "previous_*_hash does not match" —
    i.e. tamper-shaped false positives on honest concurrency.
    The new traversal follows hash-pointer edges from genesis and
    reports forks explicitly so operators can tell "someone raced"
    from "someone tampered."

    Subclasses ``ReceiptChainError`` so existing callers catching
    the parent keep working. New callers that want to distinguish
    the two can catch ``ReceiptForkError`` separately.
    """


@dataclass(frozen=True)
class EvidenceReceipt:
    """Durable record of what evidence cleared a tier's bar.

    Issued once a claim has passed its tier-appropriate burden check
    (and, for high-magnitude claims, the multi-council ratification
    step). Stored in the ``evidence_receipts`` table; chained
    Merkle-style via ``previous_receipt_hash`` so tampering with any
    earlier receipt breaks verification on all descendants.

    **What a receipt proves:** at the moment of issue, the claim had
    the required evidence for its tier/magnitude, and no recorded
    prior receipt in the chain had been tampered with.

    **What a receipt does NOT prove:** that the claim is TRUE. A
    receipt on a false premise is still a valid receipt (and the
    premise is still false). The distinction is load-bearing —
    callers must never treat ``receipt_id is not None`` as a
    proof-of-truth shortcut. See the falsifier in
    prereg-ce8998194943 for the explicit failure mode.

    This distinction is precisely why the type was renamed from
    ``GnosisWarrant`` on 2026-04-17. the family member's framing from the
    post-audit review: *"Honest bookkeeping is the grand thing.
    The other name was borrowing dignity it hadn't earned."*

    Fields:

    * ``receipt_id`` — UUID. Primary key.
    * ``claim_id`` — reference to the knowledge entry this receipt
      records.
    * ``tier`` — the tier the claim was classified into at issue time.
    * ``magnitude`` — the claim's magnitude at issue time.
    * ``corroboration_count`` — snapshot of the evidence the claim
      had when the receipt was issued. Stored because the knowledge
      entry's corroboration_count can change after; the receipt
      preserves the state at issue time.
    * ``council_count`` — how many councils ratified the claim.
      Zero for low-magnitude claims that don't require council
      review.
    * ``issued_at`` — timestamp.
    * ``artifact_pointer`` — structured reference to unfakeable
      evidence the caller cited at issue time (test name, commit,
      decision-journal ID, pre-reg ID, event ID, or knowledge ID).
      Required for PATTERN or FALSIFIABLE tier per the family member's rule in
      prereg-e210f5fb78c9; None for OUTCOME claims that don't
      require a pointer. Phase 1.5 stores the pointer verbatim; a
      future phase will validate that the referenced artifact
      actually exists.
    * ``previous_receipt_hash_global`` — self_hash of the prior
      receipt in the GLOBAL chain (or None for the genesis receipt
      of the entire system). The global chain is the system's
      self-integrity statement: tampering with any receipt breaks
      forward traversal from genesis.
    * ``previous_receipt_hash_in_claim`` — self_hash of the prior
      receipt FOR THIS SAME CLAIM_ID (or None if this is the first
      receipt ever issued for this claim). The per-claim chain is
      the honest scope for what this receipt MEANS about its
      claim. Added 2026-04-17 per Hofstadter audit finding
      find-f2284f22d795: picking either chain alone amputates the
      other's meaning. Walking per-claim is O(k) on k receipts for
      the claim — independent of system size.
    * ``self_hash`` — SHA256 of all content fields including BOTH
      previous-hash fields and the artifact_pointer. Tampering with
      any field post-issue breaks self-hash verification.
    """

    receipt_id: str
    claim_id: str
    tier: Tier
    magnitude: ClaimMagnitude
    corroboration_count: int
    council_count: int
    issued_at: float
    artifact_pointer: str | None
    previous_receipt_hash_global: str | None
    previous_receipt_hash_in_claim: str | None
    self_hash: str

    @staticmethod
    def _compute_self_hash(
        claim_id: str,
        tier: Tier,
        magnitude: ClaimMagnitude,
        corroboration_count: int,
        council_count: int,
        issued_at: float,
        artifact_pointer: str | None,
        previous_receipt_hash_global: str | None,
        previous_receipt_hash_in_claim: str | None,
    ) -> str:
        """Compute the self_hash over all receipt fields.

        Uses SHA256 (matches the rest of the DivineOS ledger) of a
        canonical string concatenation. Field order is fixed —
        changing it is a wire-format break and must bump a schema
        version, not silently change hashes for existing receipts.

        Both previous-hash fields (global and per-claim) are
        included so tampering with either chain link is detectable.
        """
        canonical = "|".join(
            [
                claim_id,
                tier.value,
                str(magnitude.value),
                str(corroboration_count),
                str(council_count),
                f"{issued_at:.6f}",
                artifact_pointer or "NO_POINTER",
                previous_receipt_hash_global or "GENESIS_GLOBAL",
                previous_receipt_hash_in_claim or "GENESIS_CLAIM",
            ]
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @classmethod
    def issue(
        cls,
        claim_id: str,
        tier: Tier,
        magnitude: ClaimMagnitude,
        corroboration_count: int,
        council_count: int,
        previous_receipt_hash_global: str | None,
        previous_receipt_hash_in_claim: str | None,
        artifact_pointer: str | None = None,
    ) -> EvidenceReceipt:
        """Construct a receipt with computed self_hash.

        Prefer this over direct __init__ — it guarantees self_hash
        is computed from the canonical field values rather than
        passed (and potentially tampered) by the caller.

        Both previous-hash fields are required parameters (no
        default) so callers must explicitly think about whether the
        receipt is genesis-for-global (None) and/or
        genesis-for-this-claim (None).
        """
        issued_at = time.time()
        receipt_id = f"receipt-{uuid.uuid4().hex[:12]}"
        self_hash = cls._compute_self_hash(
            claim_id=claim_id,
            tier=tier,
            magnitude=magnitude,
            corroboration_count=corroboration_count,
            council_count=council_count,
            issued_at=issued_at,
            artifact_pointer=artifact_pointer,
            previous_receipt_hash_global=previous_receipt_hash_global,
            previous_receipt_hash_in_claim=previous_receipt_hash_in_claim,
        )
        return cls(
            receipt_id=receipt_id,
            claim_id=claim_id,
            tier=tier,
            magnitude=magnitude,
            corroboration_count=corroboration_count,
            council_count=council_count,
            issued_at=issued_at,
            artifact_pointer=artifact_pointer,
            previous_receipt_hash_global=previous_receipt_hash_global,
            previous_receipt_hash_in_claim=previous_receipt_hash_in_claim,
            self_hash=self_hash,
        )

    def verify_self_hash(self) -> bool:
        """Return True if self_hash matches the current field values.

        If this returns False, the receipt has been tampered with
        since issue — either the hash field or one of the content
        fields was changed after construction. Both chain hashes
        (global and per-claim) participate in the signature so
        tampering with either is detectable.
        """
        expected = self._compute_self_hash(
            claim_id=self.claim_id,
            tier=self.tier,
            magnitude=self.magnitude,
            corroboration_count=self.corroboration_count,
            council_count=self.council_count,
            issued_at=self.issued_at,
            artifact_pointer=self.artifact_pointer,
            previous_receipt_hash_global=self.previous_receipt_hash_global,
            previous_receipt_hash_in_claim=self.previous_receipt_hash_in_claim,
        )
        return expected == self.self_hash


__all__ = [
    "ClaimMagnitude",
    "EvidenceReceipt",
    "ReceiptChainError",
    "ReceiptForkError",
    "Tier",
]
