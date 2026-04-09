"""Sleep — offline consolidation between sessions.

Human sleep is one of the most active processing states the brain enters:
memory consolidation, synaptic pruning, emotional processing, creative
recombination, waste clearance. None of it requires consciousness.

This module is the AI analog. It runs between sessions — not during live
work — and processes accumulated experience into cleaner, better-connected
knowledge. The human controls when sleep happens. The system doesn't get
idle cycles to run away with.

Six phases:
  1. Knowledge Consolidation — full-store maturity lifecycle pass
  2. Pruning — hygiene, noise sweep, contradiction resolution
  3. Affect Recalibration — decay emotional charge, compute baseline
  4. Maintenance — VACUUM, log rotation, cache pruning
  5. Creative Recombination — cross-knowledge similarity scanning
  6. Dream Report — summary of what changed
"""

import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

_SLEEP_ERRORS = (sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError, ImportError)


# ─── Dream Report ─────────────────────────────────────────────────────


@dataclass
class DreamReport:
    """What happened during sleep. The system's equivalent of waking up
    and remembering fragments."""

    started_at: float = 0.0
    finished_at: float = 0.0
    duration_seconds: float = 0.0

    # Phase 1: Consolidation
    entries_scanned: int = 0
    promotions: dict[str, int] = field(default_factory=dict)
    total_promoted: int = 0

    # Phase 2: Pruning
    health_results: dict[str, Any] = field(default_factory=dict)
    hygiene_results: dict[str, Any] = field(default_factory=dict)
    contradictions_found: int = 0

    # Phase 3: Affect
    affect_entries_processed: int = 0
    affect_baseline: dict[str, float] = field(default_factory=dict)
    affect_decayed: int = 0

    # Phase 4: Maintenance
    maintenance_results: dict[str, Any] = field(default_factory=dict)

    # Phase 5: Recombination
    connections_found: int = 0
    connection_details: list[dict[str, str]] = field(default_factory=list)

    # Phase 6: Curiosity Generation
    curiosities_generated: int = 0
    curiosity_categories: list[str] = field(default_factory=list)

    # Errors (non-fatal — sleep continues through failures)
    phase_errors: dict[str, str] = field(default_factory=dict)

    def summary(self) -> str:
        """Human-readable dream report."""
        lines = []
        lines.append("=== Dream Report ===")
        lines.append(f"  Slept for {self.duration_seconds:.1f}s\n")

        # Consolidation
        lines.append("  Phase 1 - Knowledge Consolidation")
        lines.append(f"    Scanned {self.entries_scanned} entries")
        if self.total_promoted > 0:
            for level, count in self.promotions.items():
                lines.append(f"    Promoted to {level}: {count}")
        else:
            lines.append("    No promotions needed")

        # Pruning
        lines.append("\n  Phase 2 - Pruning")
        pruning_found = False
        if self.health_results:
            for key in (
                "temporal_decayed",
                "noise_swept",
                "maturity_demoted",
                "contradiction_flagged",
            ):
                val = self.health_results.get(key, 0)
                if val:
                    label = key.replace("_", " ").capitalize()
                    lines.append(f"    {label}: {val}")
                    pruning_found = True
            review_count = self.health_results.get("needs_review_count", 0)
            if review_count:
                lines.append(f"    Needs review (unseen 30d+): {review_count}")
                pruning_found = True
        if self.hygiene_results:
            for key in ("noise_demoted", "noise_superseded", "stale_decayed", "orphans_flagged"):
                val = self.hygiene_results.get(key, 0)
                if val:
                    label = key.replace("_", " ").capitalize()
                    lines.append(f"    {label}: {val}")
                    pruning_found = True
        if not pruning_found:
            lines.append("    Knowledge store is clean")

        # Affect
        lines.append("\n  Phase 3 - Affect Recalibration")
        if self.affect_entries_processed > 0:
            lines.append(f"    Processed {self.affect_entries_processed} affect entries")
            lines.append(f"    Decayed {self.affect_decayed} entries")
            if self.affect_baseline:
                v = self.affect_baseline.get("valence", 0)
                a = self.affect_baseline.get("arousal", 0)
                d = self.affect_baseline.get("dominance", 0)
                lines.append(f"    Baseline mood: V={v:+.2f} A={a:.2f} D={d:+.2f}")
        else:
            lines.append("    No affect history to process")

        # Maintenance
        lines.append("\n  Phase 4 - Maintenance")
        if self.maintenance_results:
            freed = self.maintenance_results.get("vacuum", {}).get("freed_mb", 0)
            if freed > 0:
                lines.append(f"    VACUUM freed {freed:.1f}MB")
            else:
                lines.append("    VACUUM: nothing to reclaim")
            logs = self.maintenance_results.get("logs", {})
            if logs.get("removed_count", 0) > 0:
                lines.append(f"    Removed {logs['removed_count']} old log files")
            transcripts = self.maintenance_results.get("transcripts", {})
            if transcripts.get("removed_count", 0) > 0:
                lines.append(
                    f"    Cleaned {transcripts['removed_count']} transcript debris "
                    f"({transcripts.get('freed_mb', 0):.1f}MB freed)"
                )
        else:
            lines.append("    Skipped")

        # Recombination
        lines.append("\n  Phase 5 - Creative Recombination")
        if self.connections_found > 0:
            lines.append(f"    Found {self.connections_found} new connection(s)")
            for conn in self.connection_details[:5]:
                lines.append(f"    ~ {conn.get('summary', '?')}")
        else:
            lines.append("    No new connections found")

        # Curiosity
        lines.append("\n  Phase 6 - Curiosity Generation")
        if self.curiosities_generated > 0:
            lines.append(f"    Generated {self.curiosities_generated} question(s)")
            for cat in self.curiosity_categories:
                lines.append(f"    ? {cat}")
        else:
            lines.append("    No new questions generated")

        # Errors
        if self.phase_errors:
            lines.append("\n  Errors (non-fatal)")
            for phase, err in self.phase_errors.items():
                lines.append(f"    {phase}: {err}")

        lines.append("")
        return "\n".join(lines)


# ─── Phase 1: Knowledge Consolidation ─────────────────────────────────


def _phase_consolidation(report: DreamReport) -> None:
    """Full-store maturity lifecycle pass.

    During SESSION_END, maturity checks run on newly stored entries only.
    Sleep checks EVERYTHING — entries that accumulated corroboration across
    multiple sessions but never hit the promotion threshold in any single one.
    """
    from divineos.core.knowledge.crud import get_knowledge
    from divineos.core.knowledge_maintenance import run_maturity_cycle

    entries = get_knowledge(limit=10000, include_superseded=False)
    report.entries_scanned = len(entries)

    promotions = run_maturity_cycle(entries)
    report.promotions = promotions
    report.total_promoted = sum(promotions.values())


# ─── Phase 2: Pruning ─────────────────────────────────────────────────


def _phase_pruning(report: DreamReport) -> None:
    """Knowledge hygiene: health check + noise sweep + contradiction scan + curiosity decay."""
    from divineos.core.knowledge.feedback import health_check
    from divineos.core.knowledge_maintenance import run_knowledge_hygiene

    report.health_results = health_check()
    report.hygiene_results = run_knowledge_hygiene()

    # Prune stale curiosities — wonder has a shelf life
    try:
        from divineos.core.curiosity_engine import prune_stale_curiosities

        shelved = prune_stale_curiosities()
        if shelved:
            report.hygiene_results["curiosities_shelved"] = shelved
    except _SLEEP_ERRORS:
        pass


# ─── Phase 3: Affect Recalibration ───────────────────────────────────


# Affect entries older than this many hours get intensity decayed.
_AFFECT_DECAY_HOURS = 12.0
# Context-sensitive decay: different emotional states decay at different rates.
# Intense negative states (frustration, anxiety) fade faster — holding onto
# them isn't useful. Positive states and moderate states decay more slowly.
_AFFECT_DECAY_FACTOR = 0.7  # default for moderate states
_AFFECT_DECAY_FAST = 0.5  # for intense negative states (let them go)
_AFFECT_DECAY_SLOW = 0.85  # for positive states (keep what's working)
# Floor: affect never decays below this absolute intensity.
_AFFECT_INTENSITY_FLOOR = 0.05


def _compute_decay_factor(valence: float, arousal: float) -> float:
    """Choose decay rate based on the emotional state.

    Intense negative states (frustration, anxiety) decay fastest —
    dwelling on them degrades future performance. Positive states
    decay slowest — they represent what's working. Neutral/moderate
    states use the default rate.
    """
    if valence < -0.3 and arousal > 0.5:
        return _AFFECT_DECAY_FAST
    if valence > 0.2:
        return _AFFECT_DECAY_SLOW
    return _AFFECT_DECAY_FACTOR


def _phase_affect(report: DreamReport) -> None:
    """Decay emotional charge from past sessions, compute baseline mood.

    Uses context-sensitive decay: intense negative states (frustration,
    anxiety) fade faster than positive states. The information about
    what happened stays in the knowledge store — only the charge fades.
    """
    from divineos.core.affect import get_affect_history, init_affect_log
    from divineos.core.memory import _get_connection

    init_affect_log()
    history = get_affect_history(limit=200)
    report.affect_entries_processed = len(history)

    if not history:
        return

    cutoff = time.time() - (_AFFECT_DECAY_HOURS * 3600)
    decayed = 0
    conn = _get_connection()
    try:
        for entry in history:
            created = entry.get("created_at", 0)
            if created >= cutoff:
                continue

            valence = entry.get("valence", 0.0)
            arousal = entry.get("arousal", 0.0)

            factor = _compute_decay_factor(valence, arousal)
            new_valence = valence * factor
            new_arousal = arousal * factor

            if abs(new_valence) < _AFFECT_INTENSITY_FLOOR:
                new_valence = 0.0
            if abs(new_arousal) < _AFFECT_INTENSITY_FLOOR:
                new_arousal = 0.0

            if abs(new_valence - valence) > 0.001 or abs(new_arousal - arousal) > 0.001:
                conn.execute(
                    "UPDATE affect_log SET valence = ?, arousal = ? WHERE entry_id = ?",
                    (new_valence, new_arousal, entry["entry_id"]),
                )
                decayed += 1

        conn.commit()
    finally:
        conn.close()

    report.affect_decayed = decayed

    recent = [e for e in history if e.get("created_at", 0) >= cutoff]
    if recent:
        avg_v = sum(e.get("valence", 0) for e in recent) / len(recent)
        avg_a = sum(e.get("arousal", 0) for e in recent) / len(recent)
        avg_d = sum(e.get("dominance", 0) or 0 for e in recent) / len(recent)
        report.affect_baseline = {
            "valence": round(avg_v, 3),
            "arousal": round(avg_a, 3),
            "dominance": round(avg_d, 3),
        }
    else:
        report.affect_baseline = {"valence": 0.0, "arousal": 0.0, "dominance": 0.0}


# ─── Phase 4: Maintenance ─────────────────────────────────────────────


def _phase_maintenance(report: DreamReport) -> None:
    """VACUUM, log rotation, cache pruning. The glymphatic system."""
    from divineos.core.body_awareness import run_maintenance

    report.maintenance_results = run_maintenance(dry_run=False)


# ─── Phase 5: Creative Recombination ──────────────────────────────────


# Similarity thresholds for connection detection
_RECOMBINATION_MIN_SIMILARITY = 0.35  # Minimum to consider related
_RECOMBINATION_MAX_SIMILARITY = 0.85  # Above this = near-duplicate, not a connection
_RECOMBINATION_MAX_CONNECTIONS = 10  # Don't flood the report


def _phase_recombination(report: DreamReport) -> None:
    """Cross-knowledge similarity scanning for unlinked connections.

    Uses semantic similarity (sentence embeddings) when available to find
    conceptual connections even between entries that share no vocabulary.
    Falls back to word overlap when embeddings are unavailable.
    """
    from divineos.core.knowledge._text import compute_similarity
    from divineos.core.knowledge.crud import get_knowledge

    entries = get_knowledge(limit=5000, include_superseded=False)
    if len(entries) < 2:
        return

    # Group by type to find cross-type connections (same-type overlap
    # is usually just redundancy, not insight)
    by_type: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        ktype = entry.get("knowledge_type", "UNKNOWN")
        by_type.setdefault(ktype, []).append(entry)

    types = list(by_type.keys())
    connections: list[dict[str, str]] = []

    for i, type_a in enumerate(types):
        for type_b in types[i + 1 :]:
            for entry_a in by_type[type_a]:
                content_a = entry_a.get("content", "")
                if len(content_a) < 20:
                    continue
                for entry_b in by_type[type_b]:
                    if len(connections) >= _RECOMBINATION_MAX_CONNECTIONS:
                        break
                    content_b = entry_b.get("content", "")
                    if len(content_b) < 20:
                        continue

                    similarity = compute_similarity(content_a, content_b)
                    if _RECOMBINATION_MIN_SIMILARITY <= similarity <= _RECOMBINATION_MAX_SIMILARITY:
                        connections.append(
                            {
                                "entry_a_id": entry_a.get("knowledge_id", "?"),
                                "entry_b_id": entry_b.get("knowledge_id", "?"),
                                "type_a": type_a,
                                "type_b": type_b,
                                "similarity": f"{similarity:.0%}",
                                "summary": (
                                    f"{type_a[:12]}~{type_b[:12]}: "
                                    f'"{content_a[:50]}..." ~ "{content_b[:50]}..."'
                                ),
                            }
                        )

                if len(connections) >= _RECOMBINATION_MAX_CONNECTIONS:
                    break
            if len(connections) >= _RECOMBINATION_MAX_CONNECTIONS:
                break

    report.connections_found = len(connections)
    report.connection_details = connections


# ─── Phase 6: Curiosity Generation ──────────────────────────────────


def _phase_curiosity(report: DreamReport) -> None:
    """Scan knowledge gaps and generate questions for the next session.

    This is the proactive horizon — the OS doesn't wait for the Architect
    to ask. It looks at its own incomplete knowledge, stuck lessons, and
    unresolved contradictions, and generates genuine questions.
    """
    from divineos.core.curiosity_engine import generate_curiosities_from_gaps

    generated = generate_curiosities_from_gaps(max_questions=5)
    report.curiosities_generated = len(generated)
    report.curiosity_categories = [g.get("question", "?")[:80] for g in generated]


# ─── Orchestrator ─────────────────────────────────────────────────────


_PHASES: list[tuple[str, Any]] = [
    ("consolidation", _phase_consolidation),
    ("pruning", _phase_pruning),
    ("affect", _phase_affect),
    ("maintenance", _phase_maintenance),
    ("recombination", _phase_recombination),
    ("curiosity", _phase_curiosity),
]


def run_sleep(skip_maintenance: bool = False) -> DreamReport:
    """Run the full sleep cycle. Returns a dream report.

    Each phase is independent — if one fails, the others still run.
    This is offline processing, not a live session. Errors are recorded
    but don't crash the system.

    Args:
        skip_maintenance: Skip the VACUUM/log/cache phase (useful for testing).
    """
    report = DreamReport(started_at=time.time())

    for phase_name, phase_fn in _PHASES:
        if skip_maintenance and phase_name == "maintenance":
            continue
        try:
            phase_fn(report)
        except _SLEEP_ERRORS as e:
            report.phase_errors[phase_name] = str(e)
            logger.warning(f"Sleep phase '{phase_name}' failed: {e}")

    report.finished_at = time.time()
    report.duration_seconds = report.finished_at - report.started_at
    return report
