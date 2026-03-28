"""Knowledge Maturity Lifecycle — promotes knowledge through trust levels.

Maturity levels represent how much we trust a piece of knowledge:
- RAW: just extracted, unverified
- HYPOTHESIS: plausible but not confirmed
- TESTED: seen in 2+ sessions (corroboration_count >= 2)
- CONFIRMED: reliable knowledge (corroboration_count >= 5 AND confidence >= 0.8)
- REVISED: superseded by newer knowledge

Promotion is based on corroboration (how many times the knowledge has been
re-encountered across sessions) and confidence score. Demotion happens
when knowledge is superseded.
"""

from __future__ import annotations

import time
from typing import Any

from loguru import logger


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


def promote_maturity(knowledge_id: str) -> str | None:
    """Check and apply maturity promotion for a knowledge entry.

    Returns the new maturity level if promoted, None otherwise.
    """
    from divineos.core.knowledge import _get_connection

    conn = _get_connection()
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
        if new_maturity:
            conn.execute(
                "UPDATE knowledge SET maturity = ?, updated_at = ? WHERE knowledge_id = ?",
                (new_maturity, time.time(), knowledge_id),
            )
            conn.commit()
            logger.info(f"Promoted {knowledge_id[:12]}: {entry['maturity']} -> {new_maturity}")
            return new_maturity
        return None
    finally:
        conn.close()


def increment_corroboration(knowledge_id: str) -> int:
    """Increment corroboration count for a knowledge entry.

    Called when knowledge is re-encountered in a new session.
    Returns the new corroboration count.
    """
    from divineos.core.knowledge import _get_connection

    conn = _get_connection()
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
        if new_maturity:
            from divineos.core.knowledge import _get_connection

            conn = _get_connection()
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
