"""Epistemic Status ��� distinguish what I observed vs inferred vs was told.

Butlin et al. (2023) Indicator 14: The system must distinguish between
internally generated content (inference, imagination) and externally
sourced content (observation, testimony).

The warrant system already tracks this! Every knowledge entry has a
warrant type: EMPIRICAL, TESTIMONIAL, INFERENTIAL, INHERITED. And the
claims engine has 5 epistemic tiers.

This module SURFACES that information as a coherent epistemic report:
What do I know, and HOW do I know it?

Four epistemic channels:
1. OBSERVED: I saw this happen (test output, tool results, session events)
2. INFERRED: I derived this from other knowledge (logical relations, synthesis)
3. TOLD: The user told me this (corrections, preferences, directives)
4. INHERITED: This came from seed data (no session evidence)
"""

import sqlite3
from typing import Any

from loguru import logger

_ES_ERRORS = (sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


# ─── Epistemic Report ─────────────────���────────────────────────────


def build_epistemic_report() -> dict[str, Any]:
    """Build a report of knowledge grouped by epistemic source.

    This is the clean view that answers: for each thing I believe,
    HOW do I know it?
    """
    report: dict[str, Any] = {
        "observed": [],
        "inferred": [],
        "told": [],
        "inherited": [],
        "unwarranted": [],
        "summary": {},
    }

    # Get all active knowledge
    try:
        from divineos.core.knowledge import get_knowledge

        all_knowledge = get_knowledge(limit=10000)
    except _ES_ERRORS as e:
        logger.debug("Epistemic report failed to get knowledge: %s", e)
        return report

    # Get warrants for each entry
    try:
        from divineos.core.logic.warrants import get_warrants
    except _ES_ERRORS as e:
        logger.debug("Epistemic report failed to import warrants: %s", e)
        # Fall back to source field
        return _build_from_source_field(all_knowledge)

    for entry in all_knowledge:
        if entry.get("superseded_by"):
            continue

        kid = entry["knowledge_id"]
        warrants = []
        try:
            warrants = get_warrants(kid, status="ACTIVE")
        except _ES_ERRORS:
            pass

        item = {
            "knowledge_id": kid,
            "type": entry["knowledge_type"],
            "content": entry["content"][:120],
            "confidence": entry.get("confidence", 0.5),
            "maturity": entry.get("maturity", "RAW"),
        }

        if not warrants:
            # No warrant — check source field as fallback
            source = entry.get("source", "")
            channel = _source_to_channel(source)
            report[channel].append(item)
        else:
            # Use the strongest warrant type
            channel = _warrant_to_channel(warrants[0].warrant_type)
            item["warrant_grounds"] = warrants[0].grounds[:80]
            item["warrant_count"] = len(warrants)
            report[channel].append(item)

    # Summary statistics
    report["summary"] = {
        "observed": len(report["observed"]),
        "inferred": len(report["inferred"]),
        "told": len(report["told"]),
        "inherited": len(report["inherited"]),
        "unwarranted": len(report["unwarranted"]),
        "total": sum(
            len(report[ch]) for ch in ("observed", "inferred", "told", "inherited", "unwarranted")
        ),
    }

    return report


def _build_from_source_field(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Fallback: build epistemic report from the source field."""
    report: dict[str, Any] = {
        "observed": [],
        "inferred": [],
        "told": [],
        "inherited": [],
        "unwarranted": [],
        "summary": {},
    }

    for entry in entries:
        if entry.get("superseded_by"):
            continue
        source = entry.get("source", "")
        channel = _source_to_channel(source)
        report[channel].append(
            {
                "knowledge_id": entry["knowledge_id"],
                "type": entry["knowledge_type"],
                "content": entry["content"][:120],
                "confidence": entry.get("confidence", 0.5),
                "maturity": entry.get("maturity", "RAW"),
            }
        )

    report["summary"] = {
        ch: len(report[ch]) for ch in ("observed", "inferred", "told", "inherited", "unwarranted")
    }
    report["summary"]["total"] = sum(report["summary"].values())
    return report


def _warrant_to_channel(warrant_type: str) -> str:
    """Map warrant type to epistemic channel."""
    return {
        "EMPIRICAL": "observed",
        "TESTIMONIAL": "told",
        "INFERENTIAL": "inferred",
        "INHERITED": "inherited",
    }.get(warrant_type, "unwarranted")


def _source_to_channel(source: str) -> str:
    """Map knowledge source to epistemic channel."""
    return {
        "DEMONSTRATED": "observed",
        "CORRECTED": "told",
        "STATED": "told",
        "SYNTHESIZED": "inferred",
        "INHERITED": "inherited",
    }.get(source, "unwarranted")


# ���── Epistemic Confidence ─────��────────────────────────────────────


def epistemic_source_modifier(source: str) -> float:
    """Return a small score modifier based on the epistemic channel of a source.

    This is the lightweight version used in active memory importance scoring.
    No DB calls -- just maps the source field to a modifier.

    Observed (DEMONSTRATED) gets a small boost because empirical evidence
    is most trustworthy. Inherited (seed) gets a small penalty because it
    has no session evidence behind it. Everything else is neutral or
    slightly positive.
    """
    from divineos.core.constants import (
        EPISTEMIC_BOOST_OBSERVED,
        EPISTEMIC_BOOST_TOLD,
        EPISTEMIC_PENALTY_INHERITED,
    )

    return {
        "DEMONSTRATED": EPISTEMIC_BOOST_OBSERVED,
        "CORRECTED": EPISTEMIC_BOOST_TOLD,
        "STATED": EPISTEMIC_BOOST_TOLD,
        "SYNTHESIZED": 0.0,
        "INHERITED": EPISTEMIC_PENALTY_INHERITED,
    }.get(source, 0.0)


def assess_epistemic_confidence(knowledge_id: str) -> dict[str, Any]:
    """For a single knowledge entry, assess how well-grounded it is.

    Returns the epistemic channel, warrant chain, and an overall
    grounding score.
    """
    try:
        from divineos.core.knowledge import _get_connection
        from divineos.core.logic.warrants import get_warrants

        conn = _get_connection()
        try:
            row = conn.execute(
                "SELECT knowledge_type, content, confidence, maturity, source "
                "FROM knowledge WHERE knowledge_id = ?",
                (knowledge_id,),
            ).fetchone()
        finally:
            conn.close()

        if not row:
            return {"error": "Knowledge entry not found"}

        entry = {
            "knowledge_type": row[0],
            "content": row[1],
            "confidence": row[2],
            "maturity": row[3],
            "source": row[4] or "",
        }
        if not entry["content"]:
            return {"error": "Knowledge entry not found"}

        warrants = get_warrants(knowledge_id, status="ACTIVE")

        # Grounding score: empirical > testimonial > inferential > inherited
        grounding_weights = {
            "EMPIRICAL": 1.0,
            "TESTIMONIAL": 0.8,
            "INFERENTIAL": 0.6,
            "INHERITED": 0.3,
        }

        if not warrants:
            grounding = 0.1
            channel = _source_to_channel(entry.get("source", ""))
        else:
            best_warrant = max(
                warrants,
                key=lambda w: grounding_weights.get(w.warrant_type, 0.0),
            )
            grounding = grounding_weights.get(best_warrant.warrant_type, 0.1)
            channel = _warrant_to_channel(best_warrant.warrant_type)

        return {
            "knowledge_id": knowledge_id,
            "content": entry["content"][:120],
            "channel": channel,
            "grounding_score": grounding,
            "warrant_count": len(warrants),
            "confidence": entry.get("confidence", 0.5),
            "maturity": entry.get("maturity", "RAW"),
            "combined_confidence": entry.get("confidence", 0.5) * grounding,
        }
    except _ES_ERRORS as e:
        logger.debug("Epistemic confidence assessment failed: %s", e)
        return {"error": str(e)}


# ─── Display ──────────────���──────────────��────────────────────────


def format_epistemic_report(report: dict[str, Any] | None = None) -> str:
    """Format the epistemic report for display."""
    if report is None:
        report = build_epistemic_report()

    lines: list[str] = []
    summary = report.get("summary", {})

    lines.append("# Epistemic Status — How I Know What I Know")
    lines.append("")
    lines.append(
        f"  Observed: {summary.get('observed', 0)}  |  "
        f"Told: {summary.get('told', 0)}  |  "
        f"Inferred: {summary.get('inferred', 0)}  |  "
        f"Inherited: {summary.get('inherited', 0)}  |  "
        f"Unwarranted: {summary.get('unwarranted', 0)}"
    )
    lines.append(f"  Total: {summary.get('total', 0)} active entries")

    # Observed — strongest epistemic grounding
    observed = report.get("observed", [])
    if observed:
        lines.append("\n## Observed (I saw this happen)")
        for item in observed[:10]:
            lines.append(f"  [{item['maturity']}] {item['type']}: {item['content']}")

    # Told — user is trusted source
    told = report.get("told", [])
    if told:
        lines.append("\n## Told (you told me this)")
        for item in told[:10]:
            lines.append(f"  [{item['maturity']}] {item['type']}: {item['content']}")

    # Inferred — derived, check the chain
    inferred = report.get("inferred", [])
    if inferred:
        lines.append("\n## Inferred (I derived this)")
        for item in inferred[:10]:
            grounds = item.get("warrant_grounds", "")
            suffix = f" -- grounds: {grounds}" if grounds else ""
            lines.append(f"  [{item['maturity']}] {item['type']}: {item['content']}{suffix}")

    # Inherited — seed data, no evidence
    inherited = report.get("inherited", [])
    if inherited:
        lines.append("\n## Inherited (I was born knowing this — no session evidence yet)")
        for item in inherited[:10]:
            lines.append(f"  [{item['maturity']}] {item['type']}: {item['content']}")

    # Unwarranted — gaps in justification
    unwarranted = report.get("unwarranted", [])
    if unwarranted:
        lines.append(
            f"\n## Unwarranted (I hold {len(unwarranted)} beliefs without clear justification)"
        )
        for item in unwarranted[:5]:
            lines.append(f"  [!] {item['type']}: {item['content']}")

    return "\n".join(lines)
