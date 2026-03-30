"""SESSION_END logic pass — runs consistency, inference, and defeat scanning.

Called once per SESSION_END, after knowledge extraction and maturity cycle.
Orchestrates the logic layer modules and returns stats for display.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import sqlite3

from loguru import logger

_SL_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


@dataclass
class LogicPassResult:
    """Results from running the logic layer on a session's knowledge."""

    contradictions_found: int = 0
    warrants_created: int = 0
    inferences_made: int = 0
    defeats_triggered: int = 0
    entries_checked: int = 0
    defeated_only_count: int = 0
    lessons_from_defeats: int = 0
    details: list[str] = field(default_factory=list)


def run_session_logic_pass(
    new_knowledge_ids: list[str],
    promoted_ids: list[str] | None = None,
    session_id: str | None = None,
    max_entries: int = 50,
) -> LogicPassResult:
    """Run the logic layer on newly extracted and promoted knowledge.

    Steps:
    1. For each new entry, run consistency check
       - If contradictions found, register them
    2. For each promoted entry, run inference propagation
    3. Scan for defeated-only entries
    """
    result = LogicPassResult()
    ids_to_check = new_knowledge_ids[:max_entries]
    result.entries_checked = len(ids_to_check)

    # Step 1: Consistency checks on new entries
    try:
        from divineos.core.logic.consistency import check_consistency, register_contradiction

        for kid in ids_to_check:
            inconsistencies = check_consistency(kid, max_depth=2)
            for inc in inconsistencies:
                if inc.confidence >= 0.5:
                    register_contradiction(
                        inc.entry_a,
                        inc.entry_b,
                        confidence=inc.confidence,
                        notes=f"Detected during session {session_id or 'unknown'}",
                    )
                    result.contradictions_found += 1
                    result.details.append(
                        f"Contradiction: {inc.entry_a[:8]}..↔{inc.entry_b[:8]}.. ({inc.contradiction_type})"
                    )
    except _SL_ERRORS as e:
        logger.warning(f"Consistency check failed: {e}")

    # Step 2: Inference propagation on promoted entries
    if promoted_ids:
        try:
            from divineos.core.logic.inference import propagate_from

            for kid in promoted_ids[:max_entries]:
                derivations = propagate_from(kid, source_session=session_id)
                if derivations:
                    result.inferences_made += len(derivations)
                    result.warrants_created += len(derivations)
                    result.details.append(f"Inferred {len(derivations)} from {kid[:8]}.. promotion")
        except _SL_ERRORS as e:
            logger.warning(f"Inference propagation failed: {e}")

    # Step 3: Scan for defeated-only entries
    try:
        from divineos.core.logic.defeat_lessons import scan_defeated_only_entries

        defeated = scan_defeated_only_entries(limit=50)
        result.defeated_only_count = len(defeated)
    except _SL_ERRORS as e:
        logger.warning(f"Defeated-only scan failed: {e}")

    return result


def format_logic_summary(result: LogicPassResult) -> str:
    """Format a one-line summary for SESSION_END output."""
    parts: list[str] = []
    if result.contradictions_found:
        parts.append(f"{result.contradictions_found} contradictions")
    if result.inferences_made:
        parts.append(f"{result.inferences_made} inferences")
    if result.defeated_only_count:
        parts.append(f"{result.defeated_only_count} unjustified entries")
    if not parts:
        parts.append(f"{result.entries_checked} entries checked, clean")
    return "Logic: " + ", ".join(parts)
