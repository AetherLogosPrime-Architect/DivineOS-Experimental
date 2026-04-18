"""Receipt persistence and chain verification.

An ``EvidenceReceipt`` (see ``types.py``) is the durable record
that a claim passed its tier-appropriate burden check. This
module handles the persistence side: storing receipts in
``evidence_receipts`` (a new table in the knowledge DB), fetching
the previous receipt to chain from, and verifying chain integrity
across the whole store.

**Framing (Aria audit, 2026-04-17):** the type was renamed from
``GnosisWarrant`` to ``EvidenceReceipt`` because warrants imply
certified truth; receipts name exactly what the record is. This
module is the ledger — it keeps books, it does not certify.

## The chain

Every receipt carries ``previous_receipt_hash`` — the ``self_hash``
of the receipt issued immediately before it, globally. The first
receipt ever issued has ``previous_receipt_hash = None`` (genesis).
This globally-linked chain mirrors the event ledger's SHA256
hash-chain — tampering with any receipt breaks ``verify_self_hash``
on that receipt AND breaks the forward traversal from genesis on
all subsequent receipts. The chain is self-auditing.

## Verification is a forest traversal, not a timestamp sort

Dijkstra audit finding find-0ea12ad4b5d0: the original design
sorted receipts by ``issued_at ASC`` and walked in that order.
That turned honest concurrent-writer races into tamper-shaped
false positives — two writers reading the same latest_hash both
chain to it, and verification reports "previous_*_hash does not
match" when in fact the chain has honestly forked.

The fix: verification follows ``self_hash -> previous_receipt_hash``
pointers from genesis. Forks become visible events
(``ReceiptForkError``), distinct from tamper events
(``ReceiptChainError``).

## What this module is NOT

Not a policy enforcer. ``issue_receipt`` stores a receipt given a
passed burden check. It does not DECIDE whether the burden was met
— that's the caller's job (usually the validity gate in
``knowledge_maintenance`` consulting ``burden.required_corroboration``).
Keeps responsibilities clean and unit-testable.
"""

from __future__ import annotations

import sqlite3

from loguru import logger

from divineos.core._ledger_base import get_connection as _get_ledger_conn
from divineos.core.empirica.types import (
    ClaimMagnitude,
    EvidenceReceipt,
    ReceiptChainError,
    ReceiptForkError,
    Tier,
)


def init_receipt_table() -> None:
    """Create the ``evidence_receipts`` table if missing. Idempotent.

    Also handles the 2026-04-17 rename migration: if an older
    ``gnosis_warrants`` table exists (from pre-rename PR #126
    development DBs) and ``evidence_receipts`` does not, perform
    an ALTER TABLE rename. This is an additive migration — no data
    loss. Production databases do not have either table yet since
    PR #126 has not merged, so this primarily handles development
    and test environments.
    """
    conn = _get_ledger_conn()
    try:
        # Migration path: rename legacy table + columns if they exist.
        try:
            existing_tables = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if "gnosis_warrants" in existing_tables and "evidence_receipts" not in existing_tables:
                conn.execute("ALTER TABLE gnosis_warrants RENAME TO evidence_receipts")
                logger.info("Migrated gnosis_warrants table -> evidence_receipts")
                # SQLite 3.25+ supports RENAME COLUMN. Each column rename
                # is independently try-excepted because the schema may
                # have partial legacy state.
                try:
                    conn.execute(
                        "ALTER TABLE evidence_receipts RENAME COLUMN warrant_id TO receipt_id"
                    )
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute(
                        "ALTER TABLE evidence_receipts "
                        "RENAME COLUMN previous_warrant_hash TO previous_receipt_hash"
                    )
                except sqlite3.OperationalError:
                    pass
                conn.commit()
        except sqlite3.OperationalError as e:
            logger.debug(f"Legacy table rename skipped: {e}")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS evidence_receipts (
                receipt_id             TEXT PRIMARY KEY,
                claim_id               TEXT NOT NULL,
                tier                   TEXT NOT NULL,
                magnitude              INTEGER NOT NULL,
                corroboration_count    INTEGER NOT NULL,
                council_count          INTEGER NOT NULL,
                issued_at              REAL NOT NULL,
                artifact_pointer       TEXT,
                previous_receipt_hash  TEXT,
                self_hash              TEXT NOT NULL UNIQUE
            )
            """
        )
        # Additive migration: add artifact_pointer column if missing
        # (for databases created before prereg-e210f5fb78c9).
        try:
            conn.execute("ALTER TABLE evidence_receipts ADD COLUMN artifact_pointer TEXT")
        except sqlite3.OperationalError:
            pass  # column already exists
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_evidence_receipts_claim ON evidence_receipts(claim_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_evidence_receipts_issued "
            "ON evidence_receipts(issued_at)"
        )
        conn.commit()
    except sqlite3.OperationalError as e:
        logger.debug(f"evidence_receipts setup: {e}")
    finally:
        conn.close()


def _latest_receipt_hash() -> str | None:
    """Return the ``self_hash`` of the most recently issued receipt.

    Used to compute ``previous_receipt_hash`` for the next receipt.
    Returns None if no receipts exist yet (the first receipt is
    genesis).
    """
    init_receipt_table()
    conn = _get_ledger_conn()
    try:
        row = conn.execute(
            "SELECT self_hash FROM evidence_receipts ORDER BY issued_at DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def issue_receipt(
    claim_id: str,
    tier: Tier,
    magnitude: ClaimMagnitude,
    corroboration_count: int,
    council_count: int = 0,
    artifact_pointer: str | None = None,
) -> EvidenceReceipt:
    """Issue a receipt for a claim that has passed burden check.

    Caller is responsible for having verified that
    ``corroboration_count`` meets
    ``required_corroboration(tier, magnitude)`` BEFORE calling this.
    This function stores; it does not decide.

    Writes the receipt to ``evidence_receipts`` with
    ``previous_receipt_hash`` automatically set to the latest
    receipt's ``self_hash`` (chain link). Returns the constructed
    ``EvidenceReceipt``.
    """
    init_receipt_table()
    previous_hash = _latest_receipt_hash()
    receipt = EvidenceReceipt.issue(
        claim_id=claim_id,
        tier=tier,
        magnitude=magnitude,
        corroboration_count=corroboration_count,
        council_count=council_count,
        artifact_pointer=artifact_pointer,
        previous_receipt_hash=previous_hash,
    )

    conn = _get_ledger_conn()
    try:
        conn.execute(
            """
            INSERT INTO evidence_receipts (
                receipt_id, claim_id, tier, magnitude, corroboration_count,
                council_count, issued_at, artifact_pointer,
                previous_receipt_hash, self_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                receipt.receipt_id,
                receipt.claim_id,
                receipt.tier.value,
                receipt.magnitude.value,
                receipt.corroboration_count,
                receipt.council_count,
                receipt.issued_at,
                receipt.artifact_pointer,
                receipt.previous_receipt_hash,
                receipt.self_hash,
            ),
        )
        conn.commit()
        logger.info(
            "Issued receipt {} for claim {} (tier={}, magnitude={}, corroboration={})",
            receipt.receipt_id,
            claim_id[:12],
            tier.value,
            magnitude.name,
            corroboration_count,
        )
        return receipt
    finally:
        conn.close()


def get_receipt(receipt_id: str) -> EvidenceReceipt | None:
    """Fetch a receipt by ID, or None if not found."""
    init_receipt_table()
    conn = _get_ledger_conn()
    try:
        row = conn.execute(
            "SELECT receipt_id, claim_id, tier, magnitude, corroboration_count, "
            "council_count, issued_at, artifact_pointer, previous_receipt_hash, self_hash "
            "FROM evidence_receipts WHERE receipt_id = ?",
            (receipt_id,),
        ).fetchone()
        if not row:
            return None
        return EvidenceReceipt(
            receipt_id=row[0],
            claim_id=row[1],
            tier=Tier(row[2]),
            magnitude=ClaimMagnitude(row[3]),
            corroboration_count=int(row[4]),
            council_count=int(row[5]),
            issued_at=float(row[6]),
            artifact_pointer=row[7],
            previous_receipt_hash=row[8],
            self_hash=row[9],
        )
    finally:
        conn.close()


def get_receipts_for_claim(claim_id: str) -> list[EvidenceReceipt]:
    """Return all receipts issued for a given claim, oldest first.

    A single claim may have multiple receipts over time — e.g., a
    supersession event may issue a new receipt on the replacement
    claim with the old claim_id, or a re-corroboration may record
    a receipt at higher magnitude. Return order is chronological.
    """
    init_receipt_table()
    conn = _get_ledger_conn()
    try:
        rows = conn.execute(
            "SELECT receipt_id, claim_id, tier, magnitude, corroboration_count, "
            "council_count, issued_at, artifact_pointer, previous_receipt_hash, self_hash "
            "FROM evidence_receipts WHERE claim_id = ? ORDER BY issued_at ASC",
            (claim_id,),
        ).fetchall()
        return [
            EvidenceReceipt(
                receipt_id=r[0],
                claim_id=r[1],
                tier=Tier(r[2]),
                magnitude=ClaimMagnitude(r[3]),
                corroboration_count=int(r[4]),
                council_count=int(r[5]),
                issued_at=float(r[6]),
                artifact_pointer=r[7],
                previous_receipt_hash=r[8],
                self_hash=r[9],
            )
            for r in rows
        ]
    finally:
        conn.close()


def verify_chain() -> None:
    """Walk the receipt chain by HASH POINTERS and verify integrity.

    Traversal is a forest walk starting from genesis receipts (those
    with ``previous_receipt_hash = None``). We do NOT sort by
    ``issued_at`` — that was the bug Dijkstra flagged in audit
    finding find-0ea12ad4b5d0. In a Merkle chain, hashes define
    order; order does not define which hashes must match. Reversing
    that dependency turned honest concurrent-writer races into
    tamper-shaped false positives.

    Invariants checked (in order):

    1. Every receipt's ``self_hash`` recomputes from its current
       field values (no content tampering).
    2. Every ``self_hash`` is unique in the store.
    3. Exactly one genesis receipt exists. Two or more is a fork
       at the root — usually concurrent writers on an empty store.
    4. Walking from genesis following ``self_hash ->
       previous_receipt_hash`` edges, every node has exactly one
       child. Two or more children is a fork at that position —
       usually concurrent writers racing on the same
       latest-receipt snapshot. Zero children is end-of-chain.
    5. The traversal reaches every receipt in the store. Any
       receipt not reached is orphaned — its
       ``previous_receipt_hash`` points to a hash that doesn't
       exist in the store (stale or tampered reference).
    6. No cycles — a receipt whose traversal revisits a hash
       already in the chain.

    Raises:

    * ``ReceiptForkError`` (subclass of ``ReceiptChainError``)
      when invariants 3 or 4 fail — distinguishes honest
      concurrent-writer forks from tamper events so operators
      can diagnose correctly.
    * ``ReceiptChainError`` when invariants 1, 2, 5, or 6 fail.

    Silent on success.
    """
    init_receipt_table()
    conn = _get_ledger_conn()
    try:
        rows = conn.execute(
            "SELECT receipt_id, claim_id, tier, magnitude, corroboration_count, "
            "council_count, issued_at, artifact_pointer, previous_receipt_hash, self_hash "
            "FROM evidence_receipts"
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return  # empty store is valid

    # Invariants 1 + 2: verify every receipt's self_hash, build
    # by_self_hash index, build children_of adjacency.
    by_self_hash: dict[str, EvidenceReceipt] = {}
    children_of: dict[str | None, list[EvidenceReceipt]] = {}
    for r in rows:
        receipt = EvidenceReceipt(
            receipt_id=r[0],
            claim_id=r[1],
            tier=Tier(r[2]),
            magnitude=ClaimMagnitude(r[3]),
            corroboration_count=int(r[4]),
            council_count=int(r[5]),
            issued_at=float(r[6]),
            artifact_pointer=r[7],
            previous_receipt_hash=r[8],
            self_hash=r[9],
        )
        if not receipt.verify_self_hash():
            raise ReceiptChainError(
                f"Receipt {receipt.receipt_id}: self_hash mismatch — "
                f"content fields have been tampered since issue."
            )
        if receipt.self_hash in by_self_hash:
            prior = by_self_hash[receipt.self_hash]
            raise ReceiptChainError(
                f"Duplicate self_hash {receipt.self_hash[:16]}... appears "
                f"on receipts {prior.receipt_id} and {receipt.receipt_id}. "
                f"Hash collisions should not occur for this field set."
            )
        by_self_hash[receipt.self_hash] = receipt
        children_of.setdefault(receipt.previous_receipt_hash, []).append(receipt)

    # Invariant 3: exactly one genesis receipt.
    genesis = children_of.get(None, [])
    if not genesis:
        raise ReceiptChainError(
            "No genesis receipt found (every receipt has a "
            "previous_receipt_hash). Chain has no root — all previous "
            "links must eventually terminate at a genesis receipt."
        )
    if len(genesis) > 1:
        ids = ", ".join(r.receipt_id for r in genesis)
        raise ReceiptForkError(
            f"Multiple genesis receipts found ({len(genesis)}): {ids}. "
            f"Chain has forked at the root — likely concurrent writers "
            f"on an empty store. Each genesis receipt is valid on its "
            f"own; the fork needs operator intervention to pick the "
            f"canonical history."
        )

    # Invariant 4 + 6: walk forward from genesis, one child per node,
    # no cycles.
    current = genesis[0]
    visited: set[str] = {current.self_hash}
    while True:
        kids = children_of.get(current.self_hash, [])
        if len(kids) == 0:
            break
        if len(kids) > 1:
            ids = ", ".join(r.receipt_id for r in kids)
            raise ReceiptForkError(
                f"Fork at receipt {current.receipt_id} "
                f"({current.self_hash[:16]}...): {len(kids)} receipts "
                f"chain to its self_hash: {ids}. Likely concurrent "
                f"writers racing on the same latest-receipt snapshot. "
                f"Investigate the race and consider adding a write-side "
                f"lock or compare-and-swap on the previous hash."
            )
        current = kids[0]
        if current.self_hash in visited:
            raise ReceiptChainError(
                f"Cycle detected at receipt {current.receipt_id}: "
                f"traversal revisits self_hash already in the chain. "
                f"This should be structurally impossible unless a "
                f"receipt was manually inserted with a crafted hash."
            )
        visited.add(current.self_hash)

    # Invariant 5: every receipt reached from the genesis walk.
    unvisited = set(by_self_hash.keys()) - visited
    if unvisited:
        orphans = sorted(by_self_hash[h].receipt_id for h in unvisited)
        sample = ", ".join(orphans[:5])
        suffix = f" (and {len(orphans) - 5} more)" if len(orphans) > 5 else ""
        raise ReceiptChainError(
            f"Orphan receipts not reached from genesis traversal: "
            f"{sample}{suffix}. Their previous_receipt_hash references "
            f"point to self_hashes that do not exist in the store — "
            f"either stale (a prior receipt was deleted) or tampered "
            f"(a previous_receipt_hash was edited to a fake value)."
        )


__all__ = [
    "get_receipt",
    "get_receipts_for_claim",
    "init_receipt_table",
    "issue_receipt",
    "verify_chain",
]
