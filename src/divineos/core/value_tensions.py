"""Value-Tension Detector — Surfaces recurring competing principles from the decision journal.

When I make decisions, I often face the same tensions repeatedly:
thoroughness vs. speed, safety vs. autonomy, consistency vs. flexibility.
This module detects those patterns and surfaces them so I'm aware of
my recurring trade-offs rather than rediscovering them each session.
"""

import re
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class TensionPattern:
    """A recurring tension between competing values/principles."""

    tension_text: str  # canonical form of the tension
    occurrences: int  # how many decisions involved this tension
    decision_ids: list[str] = field(default_factory=list)
    resolutions: list[str] = field(default_factory=list)  # what I chose each time


@dataclass
class TensionReport:
    """Summary of recurring value tensions across decisions."""

    patterns: list[TensionPattern]
    total_decisions_with_tension: int
    total_decisions: int


def _normalize_tension(text: str) -> str:
    """Normalize tension text for grouping similar tensions."""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    # Strip trailing punctuation
    text = text.rstrip(".,;:!?")
    return text


def _tension_similarity(a: str, b: str) -> float:
    """Word-overlap similarity between two tension strings."""
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0.0
    overlap = words_a & words_b
    return len(overlap) / min(len(words_a), len(words_b))


def _cluster_tensions(
    tensions: list[dict[str, str]],
) -> list[TensionPattern]:
    """Group similar tension strings into patterns.

    Each item in tensions: {"tension": str, "decision_id": str, "content": str}
    """
    if not tensions:
        return []

    # Normalize all tensions
    normalized = []
    for t in tensions:
        norm = _normalize_tension(t["tension"])
        if norm:
            normalized.append({**t, "normalized": norm})

    if not normalized:
        return []

    # Greedy clustering: assign each tension to first cluster with >0.5 similarity
    clusters: list[list[dict[str, str]]] = []
    cluster_keys: list[str] = []

    for item in normalized:
        matched = False
        for i, key in enumerate(cluster_keys):
            if _tension_similarity(item["normalized"], key) > 0.5:
                clusters[i].append(item)
                matched = True
                break
        if not matched:
            clusters.append([item])
            cluster_keys.append(item["normalized"])

    # Convert clusters to TensionPattern objects
    patterns = []
    for cluster in clusters:
        # Use the most common normalized form as the canonical text
        forms = Counter(item["normalized"] for item in cluster)
        canonical = forms.most_common(1)[0][0]
        patterns.append(
            TensionPattern(
                tension_text=canonical,
                occurrences=len(cluster),
                decision_ids=[item["decision_id"] for item in cluster],
                resolutions=[item["content"] for item in cluster],
            )
        )

    # Sort by frequency descending
    patterns.sort(key=lambda p: p.occurrences, reverse=True)
    return patterns


def detect_tension_patterns(limit: int = 10) -> TensionReport:
    """Scan the decision journal for recurring value tensions.

    Returns patterns sorted by frequency — the tensions I face most often.
    """
    from divineos.core.decision_journal import count_decisions, init_decision_journal
    from divineos.core.memory import _get_connection

    init_decision_journal()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT decision_id, content, tension FROM decision_journal "
            "WHERE tension != '' ORDER BY created_at DESC",
        ).fetchall()
        total = count_decisions()
    finally:
        conn.close()

    tensions = [{"decision_id": row[0], "content": row[1], "tension": row[2]} for row in rows]

    patterns = _cluster_tensions(tensions)

    # Only return patterns that recur (2+ occurrences) unless there are few total
    if len(tensions) >= 5:
        recurring = [p for p in patterns if p.occurrences >= 2]
    else:
        recurring = patterns

    return TensionReport(
        patterns=recurring[:limit],
        total_decisions_with_tension=len(tensions),
        total_decisions=total,
    )


def correlate_tensions_with_compass(
    report: TensionReport,
) -> list[dict[str, str]]:
    """Cross-reference tension patterns with compass drift.

    When a tension mentions a spectrum name (e.g. "thoroughness vs speed")
    and that spectrum is drifting, flag it — the tension is playing out
    in observable behavior, not just in decisions.

    Returns list of dicts: {"tension", "spectrum", "drift_direction", "zone"}.
    """
    try:
        from divineos.core.moral_compass import SPECTRUMS, compass_summary
    except ImportError:
        return []

    try:
        cs = compass_summary()
    except Exception:  # noqa: BLE001
        return []

    if not cs.get("drifting") and not cs.get("concerns"):
        return []

    # Build a lookup of active compass issues
    compass_issues: dict[str, dict[str, str]] = {}
    for d in cs.get("drifting", []):
        compass_issues[d["spectrum"]] = {
            "drift_direction": d["direction"],
            "zone": "drifting",
        }
    for c in cs.get("concerns", []):
        compass_issues[c["spectrum"]] = {
            "drift_direction": "",
            "zone": c["zone"],
        }

    correlations: list[dict[str, str]] = []
    spectrum_names = set(SPECTRUMS.keys())

    for pattern in report.patterns:
        tension_words = set(pattern.tension_text.lower().split())
        # Check if any spectrum name appears in the tension text
        for spectrum in spectrum_names:
            if spectrum in tension_words and spectrum in compass_issues:
                issue = compass_issues[spectrum]
                correlations.append(
                    {
                        "tension": pattern.tension_text,
                        "spectrum": spectrum,
                        "drift_direction": issue["drift_direction"],
                        "zone": issue["zone"],
                    }
                )

    return correlations


def format_tension_summary(report: TensionReport) -> str:
    """Format tension patterns for the briefing, including compass correlations."""
    if not report.patterns:
        return ""

    lines = ["### Recurring Value Tensions"]
    lines.append(
        f"({report.total_decisions_with_tension} of {report.total_decisions} "
        f"decisions recorded a tension)"
    )
    lines.append("")

    # Check for compass correlations
    correlations = correlate_tensions_with_compass(report)
    correlation_map: dict[str, dict[str, str]] = {}
    for c in correlations:
        correlation_map[c["tension"]] = c

    for p in report.patterns[:5]:
        marker = "⚡" if p.occurrences >= 3 else "↔"
        lines.append(f"  {marker} {p.tension_text} ({p.occurrences}x)")
        if p.resolutions:
            lines.append(f"    Last chose: {p.resolutions[0][:80]}")
        # Show compass correlation if it exists
        if p.tension_text in correlation_map:
            corr = correlation_map[p.tension_text]
            if corr["drift_direction"]:
                lines.append(
                    f"    ^ compass: {corr['spectrum']} drifting {corr['drift_direction']}"
                )
            else:
                lines.append(f"    ^ compass: {corr['spectrum']} in {corr['zone']} zone")

    return "\n".join(lines)
