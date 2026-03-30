"""One-time backfill — give pre-existing knowledge entries INHERITED warrants.

Knowledge entries created before the warrant system have no justification chain.
This creates an INHERITED warrant for each unwarranted entry so the logic health
metric reflects real gaps, not just "everything before Tuesday."
"""

from __future__ import annotations

from loguru import logger

from divineos.core.knowledge import get_connection
from divineos.core.logic.warrants import create_warrant, get_warrants


def backfill_inherited_warrants(dry_run: bool = False) -> dict[str, int]:
    """Create INHERITED warrants for all knowledge entries that have none.

    Returns counts: {"checked": N, "backfilled": N, "already_warranted": N}
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT knowledge_id, knowledge_type, content "
            "FROM knowledge WHERE superseded_by IS NULL"
        ).fetchall()
    finally:
        conn.close()

    checked = 0
    backfilled = 0
    already_warranted = 0

    for kid, ktype, content in rows:
        checked += 1
        existing = get_warrants(kid)
        if existing:
            already_warranted += 1
            continue

        if dry_run:
            backfilled += 1
            continue

        grounds = f"Pre-existing {ktype} entry, warranted retroactively"
        create_warrant(
            knowledge_id=kid,
            warrant_type="INHERITED",
            grounds=grounds,
        )
        backfilled += 1

    logger.info(
        "Warrant backfill: checked={}, backfilled={}, already_warranted={}",
        checked,
        backfilled,
        already_warranted,
    )
    return {
        "checked": checked,
        "backfilled": backfilled,
        "already_warranted": already_warranted,
    }
