"""Knowledge Hygiene — audit and clean the knowledge store.

The store accumulates noise over time: raw user quotes stored as
PRINCIPLE, stale entries with temporal markers, entries never accessed.
This module runs periodic cleanup to keep the store useful.

Three hygiene operations:

1. TYPE AUDIT: Re-run the noise filter on existing entries. Anything
   that would be rejected today gets demoted or superseded.

2. STALE SWEEP: Entries with temporal markers ("currently", "is broken")
   older than a threshold get confidence decay applied.

3. ORPHAN DETECTION: Entries with zero access after N sessions are
   likely noise that slipped through. Flag them for review.
"""

import time
from typing import Any

from divineos.core.knowledge._base import _get_connection, _KNOWLEDGE_COLS, _row_to_dict
from divineos.core.knowledge._noise import (
    _has_prescriptive_signal,
    _has_temporal_markers,
    _is_extraction_noise,
)


def run_knowledge_hygiene(
    demote_noise: bool = True,
    decay_stale: bool = True,
    flag_orphans: bool = True,
    min_age_days: float = 1.0,
    stale_age_days: float = 14.0,
    orphan_min_sessions: int = 3,
) -> dict[str, Any]:
    """Run all hygiene operations on the knowledge store.

    Returns a report of actions taken.
    """
    report: dict[str, Any] = {
        "noise_demoted": 0,
        "noise_superseded": 0,
        "stale_decayed": 0,
        "orphans_flagged": 0,
        "entries_scanned": 0,
        "details": [],
    }

    conn = _get_connection()
    try:
        rows = conn.execute(
            f"SELECT {_KNOWLEDGE_COLS} FROM knowledge "
            "WHERE superseded_by IS NULL AND confidence >= 0.2 "
            "ORDER BY updated_at DESC"
        ).fetchall()
        entries = [_row_to_dict(row) for row in rows]
        report["entries_scanned"] = len(entries)
    finally:
        conn.close()

    now = time.time()
    cutoff = now - (min_age_days * 86400)

    if demote_noise:
        noise_report = _audit_types(entries, cutoff)
        report["noise_demoted"] = noise_report["demoted"]
        report["noise_superseded"] = noise_report["superseded"]
        report["details"].extend(noise_report["details"])

    if decay_stale:
        stale_report = _sweep_stale(entries, now, stale_age_days)
        report["stale_decayed"] = stale_report["decayed"]
        report["details"].extend(stale_report["details"])

    if flag_orphans:
        orphan_report = _flag_orphans(entries, orphan_min_sessions)
        report["orphans_flagged"] = orphan_report["flagged"]
        report["details"].extend(orphan_report["details"])

    return report


def _audit_types(entries: list[dict[str, Any]], cutoff: float) -> dict[str, Any]:
    """Re-run noise filter on existing PRINCIPLE/BOUNDARY entries.

    Entries that would be rejected by today's filter get demoted to
    OBSERVATION (if they have some value) or superseded (if pure noise).
    """
    result: dict[str, Any] = {"demoted": 0, "superseded": 0, "details": []}
    conn = _get_connection()

    try:
        for entry in entries:
            kid = entry["knowledge_id"]
            ktype = entry.get("knowledge_type", "")
            content = entry.get("content", "")
            created = entry.get("created_at", 0)

            # Only audit PRINCIPLE and BOUNDARY types — others are fine
            if ktype not in ("PRINCIPLE", "BOUNDARY"):
                continue
            # Don't touch recent entries — give them time to prove value
            if created > cutoff:
                continue
            # Don't touch high-corroboration entries — they proved useful
            if entry.get("corroboration_count", 0) >= 3:
                continue
            # Don't touch pinned entries
            if entry.get("pinned"):
                continue

            # Would today's filter reject this?
            if _is_extraction_noise(content, ktype):
                # Pure noise — supersede it
                conn.execute(
                    "UPDATE knowledge SET superseded_by = 'hygiene-audit', "
                    "confidence = 0.1 WHERE knowledge_id = ?",
                    (kid,),
                )
                result["superseded"] += 1
                result["details"].append(f"Superseded {ktype}: {content[:60]}...")
                continue

            # Has no prescriptive signal — demote to OBSERVATION
            content_lower = content.lower()
            if not _has_prescriptive_signal(content_lower):
                conn.execute(
                    "UPDATE knowledge SET knowledge_type = 'OBSERVATION', "
                    "confidence = CASE WHEN confidence > 0.6 THEN 0.6 ELSE confidence END "
                    "WHERE knowledge_id = ?",
                    (kid,),
                )
                result["demoted"] += 1
                result["details"].append(f"Demoted to OBSERVATION: {content[:60]}...")

        conn.commit()
    finally:
        conn.close()

    return result


def _sweep_stale(
    entries: list[dict[str, Any]], now: float, stale_age_days: float
) -> dict[str, Any]:
    """Decay confidence on entries with temporal markers that are old."""
    result: dict[str, Any] = {"decayed": 0, "details": []}
    conn = _get_connection()
    stale_cutoff = now - (stale_age_days * 86400)

    try:
        for entry in entries:
            kid = entry["knowledge_id"]
            ktype = entry.get("knowledge_type", "")
            content = entry.get("content", "")
            updated = entry.get("updated_at", 0)
            confidence = entry.get("confidence", 0.5)

            # Directives are permanent by design
            if ktype == "DIRECTIVE":
                continue
            # Only decay old entries with temporal markers
            if updated > stale_cutoff:
                continue
            if not _has_temporal_markers(content):
                continue
            # Don't decay below floor
            if confidence <= 0.3:
                continue

            new_confidence = max(confidence - 0.1, 0.3)
            conn.execute(
                "UPDATE knowledge SET confidence = ? WHERE knowledge_id = ?",
                (new_confidence, kid),
            )
            result["decayed"] += 1
            result["details"].append(
                f"Decayed ({confidence:.1f}→{new_confidence:.1f}): {content[:60]}..."
            )

        conn.commit()
    finally:
        conn.close()

    return result


def _flag_orphans(entries: list[dict[str, Any]], min_sessions: int) -> dict[str, Any]:
    """Flag entries that were never accessed and are old enough to judge."""
    result: dict[str, Any] = {"flagged": 0, "details": []}
    conn = _get_connection()

    try:
        for entry in entries:
            kid = entry["knowledge_id"]
            ktype = entry.get("knowledge_type", "")
            content = entry.get("content", "")
            access_count = entry.get("access_count", 0)
            corroboration = entry.get("corroboration_count", 0)

            # Directives and pinned entries are exempt
            if ktype == "DIRECTIVE" or entry.get("pinned"):
                continue
            # Only flag entries that have never been accessed or corroborated
            if access_count >= 2 or corroboration >= 1:
                continue

            # Demote orphaned entries to low confidence
            confidence = entry.get("confidence", 0.5)
            if confidence > 0.5:
                new_confidence = 0.5
                conn.execute(
                    "UPDATE knowledge SET confidence = ? WHERE knowledge_id = ?",
                    (new_confidence, kid),
                )
                result["flagged"] += 1
                result["details"].append(f"Orphan ({access_count} accesses): {content[:60]}...")

        conn.commit()
    finally:
        conn.close()

    return result


def format_hygiene_report(report: dict[str, Any]) -> str:
    """Format hygiene report for display."""
    lines = [f"Knowledge Hygiene Report ({report['entries_scanned']} entries scanned):"]

    if report["noise_demoted"]:
        lines.append(f"  Demoted {report['noise_demoted']} noisy entries to OBSERVATION")
    if report["noise_superseded"]:
        lines.append(f"  Superseded {report['noise_superseded']} pure noise entries")
    if report["stale_decayed"]:
        lines.append(f"  Decayed {report['stale_decayed']} stale entries with temporal markers")
    if report["orphans_flagged"]:
        lines.append(f"  Flagged {report['orphans_flagged']} orphan entries (never accessed)")

    total = (
        report["noise_demoted"]
        + report["noise_superseded"]
        + report["stale_decayed"]
        + report["orphans_flagged"]
    )
    if total == 0:
        lines.append("  Knowledge store is clean. No action needed.")

    if report["details"]:
        lines.append("")
        lines.append("Details:")
        for detail in report["details"][:20]:
            lines.append(f"  {detail}")
        if len(report["details"]) > 20:
            lines.append(f"  ... and {len(report['details']) - 20} more")

    return "\n".join(lines)
