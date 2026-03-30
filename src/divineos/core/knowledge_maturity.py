"""Knowledge Maturity Lifecycle — promotes knowledge through trust levels.

Maturity levels represent how much we trust a piece of knowledge:
- RAW: just extracted, unverified
- HYPOTHESIS: plausible but not confirmed
- TESTED: seen in 2+ sessions (corroboration_count >= 2)
- CONFIRMED: reliable knowledge (corroboration_count >= 5 AND confidence >= 0.8)
- REVISED: superseded by newer knowledge

Promotion requires two gates:
1. Corroboration gate — enough re-encounters across sessions
2. Validity gate — warrant-based justification (HYPOTHESIS→TESTED needs 1 warrant,
   TESTED→CONFIRMED needs 2+ warrants from different types)

Demotion happens when knowledge is superseded.
"""

from __future__ import annotations

import time
from typing import Any
import sqlite3

from loguru import logger

from divineos.core.knowledge import get_connection

_KM_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


# Promotion rules: (from_maturity, min_corroboration, min_confidence) → to_maturity
# Confidence floors prevent noise-penalized entries from being promoted
# by inflated corroboration counts from the old feedback loop era.
_PROMOTION_RULES: list[tuple[str, int, float, str]] = [
    ("RAW", 1, 0.4, "HYPOTHESIS"),
    ("HYPOTHESIS", 2, 0.5, "TESTED"),
    ("TESTED", 5, 0.8, "CONFIRMED"),
]


def check_promotion(entry: dict[str, Any]) -> str | None:
    """Check if an entry qualifies for maturity promotion.

    Returns the new maturity level, or None if no promotion is warranted.
    """
    current = entry.get("maturity", "RAW")
    corroboration = entry.get("corroboration_count", 0)
    confidence = entry.get("confidence", 0.5)

    for from_level, min_corrob, min_conf, to_level in _PROMOTION_RULES:
        if current == from_level and corroboration >= min_corrob and confidence >= min_conf:
            return to_level

    return None


def _passes_validity_gate(knowledge_id: str, current: str, target: str) -> bool:
    """Check if the validity gate allows this promotion.

    Fails gracefully if logic tables aren't initialized yet.
    """
    try:
        from divineos.core.logic.validity_gate import can_promote

        return can_promote(knowledge_id, current, target)
    except _KM_ERRORS:
        # Logic tables may not exist yet — allow promotion (backward compat)
        return True


def promote_maturity(knowledge_id: str) -> str | None:
    """Check and apply maturity promotion for a knowledge entry.

    Both corroboration AND validity gates must pass.
    Returns the new maturity level if promoted, None otherwise.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT maturity, corroboration_count, confidence FROM knowledge WHERE knowledge_id = ? AND superseded_by IS NULL",
            (knowledge_id,),
        ).fetchone()
        if not row:
            return None

        entry = {
            "maturity": row[0],
            "corroboration_count": row[1],
            "confidence": row[2],
        }

        new_maturity = check_promotion(entry)
        if not new_maturity:
            return None

        # Second gate: warrant-based validity
        if not _passes_validity_gate(knowledge_id, entry["maturity"], new_maturity):
            logger.debug(
                "Validity gate blocked promotion of {}: {} -> {}",
                knowledge_id[:12],
                entry["maturity"],
                new_maturity,
            )
            return None

        conn.execute(
            "UPDATE knowledge SET maturity = ?, updated_at = ? WHERE knowledge_id = ?",
            (new_maturity, time.time(), knowledge_id),
        )
        conn.commit()
        logger.info(f"Promoted {knowledge_id[:12]}: {entry['maturity']} -> {new_maturity}")
        return new_maturity
    finally:
        conn.close()


def increment_corroboration(knowledge_id: str) -> int:
    """Increment corroboration count for a knowledge entry.

    Called when knowledge is re-encountered in a new session.
    Returns the new corroboration count.
    """
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE knowledge SET corroboration_count = corroboration_count + 1, updated_at = ? WHERE knowledge_id = ?",
            (time.time(), knowledge_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT corroboration_count FROM knowledge WHERE knowledge_id = ?",
            (knowledge_id,),
        ).fetchone()
        count = row[0] if row else 0
        logger.debug(f"Corroboration for {knowledge_id[:12]}: {count}")
        return count
    finally:
        conn.close()


def run_maturity_cycle(entries: list[dict[str, Any]]) -> dict[str, int]:
    """Batch check for maturity promotions across entries.

    Both corroboration AND validity gates must pass.
    Returns counts of promotions by type.
    """
    promotions: dict[str, int] = {}
    for entry in entries:
        kid = entry.get("knowledge_id", "")
        if not kid:
            continue
        # Skip already superseded
        if entry.get("superseded_by"):
            continue

        new_maturity = check_promotion(entry)
        if not new_maturity:
            continue

        # Second gate: warrant-based validity
        if not _passes_validity_gate(kid, entry["maturity"], new_maturity):
            logger.debug(
                "Validity gate blocked batch promotion of {}: {} -> {}",
                kid[:12],
                entry["maturity"],
                new_maturity,
            )
            continue

        conn = get_connection()
        try:
            conn.execute(
                "UPDATE knowledge SET maturity = ?, updated_at = ? WHERE knowledge_id = ?",
                (new_maturity, time.time(), kid),
            )
            conn.commit()
        finally:
            conn.close()

        promotions[new_maturity] = promotions.get(new_maturity, 0) + 1
        logger.info(f"Batch promoted {kid[:12]}: {entry['maturity']} -> {new_maturity}")

    return promotions
