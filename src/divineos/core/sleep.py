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

import re
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

# Pre-compiled at module load: detects "(session abcd1234)" suffix used by
# tone-shift extraction in lessons.py. Used by _phase_recombination to skip
# session-specific entries from cross-knowledge mining.
_SESSION_SUFFIX_PATTERN = re.compile(r"\(session [a-f0-9]{6,16}\)")

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
    lessons_resolved: list[str] = field(default_factory=list)
    # Lessons that transitioned improving → dormant this cycle (quiet but
    # unproven — distinct from resolved, per the 2026-04-16 Popper audit).
    lessons_dormant: list[str] = field(default_factory=list)

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
    # `connections_found` used to mean "pairs in the similarity band"
    # regardless of whether we'd surfaced them before. That was
    # Goodhart-shape: the same 10 pairs could report as "new" every
    # sleep indefinitely. Split per 2026-04-24 audit — the report
    # now distinguishes genuinely-new connections from re-encountered
    # pairs (which have existing RELATED_TO edges from prior sleeps).
    connections_found: int = 0  # total pairs in similarity band (new + already-known)
    connections_new: int = 0  # pairs with no existing RELATED_TO edge — novel this sleep
    connections_already_known: int = 0  # pairs already in graph from prior sleeps
    connection_details: list[dict[str, str]] = field(default_factory=list)

    # Phase 6: Curiosity Generation
    curiosities_generated: int = 0
    lessons_rehearsed: int = 0
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
        if self.lessons_resolved:
            lines.append(f"    Lessons resolved: {', '.join(self.lessons_resolved)}")
        if self.lessons_dormant:
            lines.append(
                f"    Lessons dormant (quiet, not proven): {', '.join(self.lessons_dormant)}"
            )

        # Pruning
        lines.append("\n  Phase 2 - Pruning")
        pruning_found = False
        if self.health_results:
            for key in (
                "temporal_decayed",
                "noise_penalized",
                "noise_superseded",
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
            for key in (
                "noise_demoted",
                "noise_superseded",
                "stale_decayed",
                "stale_superseded",
                "orphans_flagged",
                "reaped",
            ):
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
            pytest_tmp = self.maintenance_results.get("pytest_tmp", {})
            if pytest_tmp.get("removed", 0) > 0:
                lines.append(
                    f"    Cleaned {pytest_tmp['removed']} pytest run dirs "
                    f"({pytest_tmp.get('freed_mb', 0):.1f}MB freed)"
                )
        else:
            lines.append("    Skipped")

        # Recombination — honest counts (2026-04-24 fix)
        lines.append("\n  Phase 5 - Creative Recombination")
        if self.connections_new > 0:
            if self.connections_already_known > 0:
                lines.append(
                    f"    Found {self.connections_new} new connection(s) "
                    f"({self.connections_already_known} already-known skipped)"
                )
            else:
                lines.append(f"    Found {self.connections_new} new connection(s)")
            for conn in self.connection_details[:5]:
                lines.append(f"    ~ {conn.get('summary', '?')}")
        elif self.connections_already_known > 0:
            lines.append(
                f"    No new connections — {self.connections_already_known} "
                "already-known pairs skipped (similarity space may be saturating)"
            )
        else:
            lines.append("    No connections found in similarity band")

        # Curiosity
        lines.append("\n  Phase 6 - Curiosity Maintenance")
        if self.curiosity_categories:
            for cat in self.curiosity_categories:
                lines.append(f"    {cat}")
        else:
            lines.append("    Nothing to prune")

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

    Also runs lesson resolution: lessons are maturity too. A lesson that has
    been 'improving' long enough with zero regressions earns RESOLVED status.
    SESSION_END phase 8q only runs on explicit triggers; sleep ensures
    absence-as-success still gets counted when the full pipeline doesn't fire.
    """
    from divineos.core.knowledge.crud import get_knowledge
    from divineos.core.knowledge.lessons import (
        STATUS_DORMANT,
        STATUS_RESOLVED,
        auto_resolve_lessons,
    )
    from divineos.core.knowledge_maintenance import run_maturity_cycle

    entries = get_knowledge(limit=10000, include_superseded=False)
    report.entries_scanned = len(entries)

    promotions = run_maturity_cycle(entries)
    report.promotions = promotions
    report.total_promoted = sum(promotions.values())

    # auto_resolve_lessons now returns transitions of two kinds
    # (2026-04-16 Kahneman/Popper audit):
    #   - improving → resolved when positive counterfactual evidence exists
    #   - improving → dormant when quiet but unproven
    # Split them in the dream report so the summary doesn't claim resolution
    # it didn't earn.
    transitions = auto_resolve_lessons()
    report.lessons_resolved = [
        r["category"] for r in transitions if r.get("status") == STATUS_RESOLVED
    ]
    report.lessons_dormant = [
        r["category"] for r in transitions if r.get("status") == STATUS_DORMANT
    ]


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

    # Age the holding room — things that sit too long go stale
    try:
        from divineos.core.holding import age_holding

        newly_stale = age_holding()
        if newly_stale:
            report.hygiene_results["holding_items_stale"] = newly_stale
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
            new_valence = max(-1.0, min(1.0, valence * factor))
            new_arousal = max(0.0, min(1.0, arousal * factor))

            if abs(new_valence) < _AFFECT_INTENSITY_FLOOR:
                new_valence = 0.0
            if new_arousal < _AFFECT_INTENSITY_FLOOR:
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
#
# 2026-05-01 tightening: split the MIN threshold by metric because cosine
# (semantic embeddings) and Sørensen-Dice (word overlap) produce different
# distributions. The 0.30 floor was set for Dice when compute_similarity
# only had Dice. Now compute_similarity prefers embeddings; embeddings at
# 30-40% surface noise pairs sharing only thematic tokens. 0.45 is the
# empirical sweet spot for cosine. Dice still uses 0.30 (preserves the
# original calibration when embeddings unavailable).
#
# Also added MIN_WORD_OVERLAP (lexical anchoring) — semantic similarity
# alone produces false positives via shared common-vocabulary; requiring
# at least 10% word-overlap ensures the connection has lexical grounding,
# not just thematic resonance.
_RECOMBINATION_MIN_SIMILARITY_COSINE = 0.45  # When semantic embeddings available
_RECOMBINATION_MIN_SIMILARITY_DICE = 0.30  # Fallback when embeddings unavailable
_RECOMBINATION_MAX_SIMILARITY = 0.65  # Above this = near-duplicate, not a connection
_RECOMBINATION_MIN_WORD_OVERLAP = 0.10  # Lexical anchoring floor (added 2026-05-01)
_RECOMBINATION_MAX_WORD_OVERLAP = 0.50  # Skip pairs that share >50% key terms (same topic)
_RECOMBINATION_MAX_CONNECTIONS = 10  # Don't flood the report


def _phase_recombination(report: DreamReport) -> None:
    """Cross-knowledge similarity scanning for unlinked connections.

    Finds genuinely surprising connections between entries that are
    semantically related but topically distinct. Filters out obvious
    same-topic pairs (e.g. MISTAKE about tests + DIRECTION about tests)
    by checking word overlap in key terms.

    **2026-04-24 honesty fix** (claim tbd): the discovery loop now
    checks `find_edge` before counting a pair. If a RELATED_TO edge
    already exists from a prior sleep, the pair is counted as
    "already-known" and does NOT count toward the MAX_CONNECTIONS
    display cap. Before this fix, the same 10 pairs could report as
    "new" every sleep indefinitely — the `create_edge` call was
    idempotent at the DB layer but the discovery loop was blind to
    that. Report now distinguishes new vs. re-encountered.
    """
    from divineos.core.knowledge._text import (
        _compute_overlap,
        _ensure_embedding_model,
        compute_similarity,
    )
    from divineos.core.knowledge.crud import get_knowledge
    from divineos.core.knowledge.edges import find_edge

    # Pick the threshold based on which similarity metric will be used.
    # compute_similarity prefers semantic embeddings if available, falls
    # back to Sørensen-Dice. The two metrics have different distributions
    # so the noise floor is different.
    _min_similarity = (
        _RECOMBINATION_MIN_SIMILARITY_COSINE
        if _ensure_embedding_model()
        else _RECOMBINATION_MIN_SIMILARITY_DICE
    )

    entries = get_knowledge(limit=5000, include_superseded=False)
    if len(entries) < 2:
        return

    # 2026-05-01 fix: exclude entries that are NOT timeless-knowledge-claims
    # from cross-knowledge recombination. Two pollution categories caught:
    #
    # 1. Session-specific entries (tone-shift PATTERN/MISTAKE from lessons.py)
    #    — embed verbatim user text and "(session abc12345)" suffix; they
    #    cluster with each other AND unrelated FACTs via shared boilerplate
    #    tokens.
    #
    # 2. Reference-only entries (code/file digests from `divineos digest`)
    #    — boilerplate prefix "File: X (N lines) Purpose: ..." shares
    #    high-frequency project-vocabulary with most knowledge entries,
    #    making the digest-FACT a connection-magnet for unrelated content.
    #
    # Both classes serve real purposes (lesson tracking, file search) but
    # they should not be mined for cross-knowledge connections. Recombination
    # is supposed to surface TIMELESS knowledge-claim connections.
    def _excluded_from_recombination(entry: dict[str, Any]) -> bool:
        tags = entry.get("tags", []) or []
        # Session-specific (tone-shift, session-tagged)
        if any(isinstance(t, str) and t.startswith("session-") for t in tags):
            return True
        if any(isinstance(t, str) and t in {"tone_shift", "tone_recovery"} for t in tags):
            return True
        # Reference-only (code/file digests, file inventories)
        if any(isinstance(t, str) and t in {"reference_only", "digest"} for t in tags):
            return True
        # Content-pattern fallback for entries that lost their tags
        content = entry.get("content") or ""
        if _SESSION_SUFFIX_PATTERN.search(content.lower()):
            return True
        return False

    pre_filter_count = len(entries)
    entries = [e for e in entries if not _excluded_from_recombination(e)]
    if pre_filter_count - len(entries) > 0:
        logger.debug(
            f"Recombination: filtered {pre_filter_count - len(entries)} non-knowledge-claim entries",
        )

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
    already_known_count = 0
    total_band_pairs = 0  # pairs in similarity band regardless of novelty

    def _first_sentence(text: str, cap: int = 140) -> str:
        for delim in (". ", "! ", "? "):
            idx = text.find(delim)
            if 0 < idx < cap:
                return text[: idx + 1]
        return text[:cap] + "..." if len(text) > cap else text

    for i, type_a in enumerate(types):
        for type_b in types[i + 1 :]:
            for entry_a in by_type[type_a]:
                content_a = entry_a.get("content", "")
                if len(content_a) < 30:
                    continue
                for entry_b in by_type[type_b]:
                    if len(connections) >= _RECOMBINATION_MAX_CONNECTIONS:
                        break
                    content_b = entry_b.get("content", "")
                    if len(content_b) < 30:
                        continue

                    # Skip pairs that share too many key words -- these are
                    # the same topic wearing different type labels, not
                    # creative connections.
                    word_overlap = _compute_overlap(content_a, content_b)
                    if word_overlap > _RECOMBINATION_MAX_WORD_OVERLAP:
                        continue
                    # 2026-05-01: also require minimum lexical anchoring.
                    # Semantic similarity alone produces false positives via
                    # shared common-vocabulary; some word overlap proves the
                    # match has real lexical grounding.
                    if word_overlap < _RECOMBINATION_MIN_WORD_OVERLAP:
                        continue

                    similarity = compute_similarity(content_a, content_b)
                    if _min_similarity <= similarity <= _RECOMBINATION_MAX_SIMILARITY:
                        total_band_pairs += 1
                        aid = entry_a.get("knowledge_id", "?")
                        bid = entry_b.get("knowledge_id", "?")

                        # 2026-04-24 honesty fix: skip pairs that
                        # already have a RELATED_TO edge from a prior
                        # sleep. These are "re-encountered," not
                        # "new." Count them separately so the report
                        # can distinguish saturation (mostly already-
                        # known) from genuine novelty (mostly new).
                        try:
                            existing = find_edge(aid, bid, "RELATED_TO")
                        except Exception:  # noqa: BLE001
                            existing = None
                        if existing is None and aid != "?" and bid != "?":
                            # Also check the reverse direction — edges
                            # are direction-neutral for RELATED_TO.
                            try:
                                existing = find_edge(bid, aid, "RELATED_TO")
                            except Exception:  # noqa: BLE001
                                existing = None
                        if existing is not None:
                            already_known_count += 1
                            continue

                        connections.append(
                            {
                                "entry_a_id": aid,
                                "entry_b_id": bid,
                                "type_a": type_a,
                                "type_b": type_b,
                                "similarity": f"{similarity:.0%}",
                                "summary": (
                                    f"({similarity:.0%}) {type_a}+{type_b}: "
                                    f"{_first_sentence(content_a)} <> "
                                    f"{_first_sentence(content_b)}"
                                ),
                            }
                        )

                if len(connections) >= _RECOMBINATION_MAX_CONNECTIONS:
                    break
            if len(connections) >= _RECOMBINATION_MAX_CONNECTIONS:
                break

    # Honest counts (2026-04-24 fix):
    # - connections_new: pairs genuinely new this sleep (capped at
    #   _RECOMBINATION_MAX_CONNECTIONS)
    # - connections_already_known: pairs in the similarity band that
    #   already have a RELATED_TO edge from prior sleeps
    # - connections_found: total band-pairs encountered (new +
    #   already-known). Preserved for backward-compat with existing
    #   HUD/dream-report callers that read this field.
    report.connections_new = len(connections)
    report.connections_already_known = already_known_count
    report.connections_found = total_band_pairs
    report.connection_details = connections

    # Persist connections as RELATED_TO edges in the knowledge graph.
    # Without this, recombination insights are ephemeral — lost after
    # the dream report scrolls off screen.
    if connections:
        try:
            from divineos.core.knowledge.edges import create_edge

            for conn in connections:
                aid = conn.get("entry_a_id", "")
                bid = conn.get("entry_b_id", "")
                if aid and bid and aid != "?" and bid != "?":
                    create_edge(
                        source_id=aid,
                        target_id=bid,
                        edge_type="RELATED_TO",
                        confidence=0.6,
                        notes=f"sleep recombination: {conn.get('similarity', '?')} similarity",
                    )
        except _SLEEP_ERRORS as e:
            logger.debug(f"Failed to persist recombination edges: {e}")


# ─── Phase 6: Curiosity Maintenance ─────────────────────────────────


def _phase_curiosity(report: DreamReport) -> None:
    """Prune stale curiosities and generate new ones from recombination connections.

    Old auto-generated questions ("What evidence would confirm or refute: X?")
    were formulaic templates. New approach: generate curiosities from Phase 5's
    cross-topic connections — these are genuine "huh, interesting" moments where
    two unrelated knowledge areas overlap unexpectedly.
    """
    from divineos.core.curiosity_engine import add_curiosity, prune_stale_curiosities

    pruned = prune_stale_curiosities()
    report.curiosities_generated = 0
    report.curiosity_categories = []
    if pruned:
        report.curiosity_categories.append(f"pruned {pruned} stale")

    # Generate curiosities from Phase 5 connections
    if report.connection_details:
        generated = 0
        for conn in report.connection_details[:3]:  # Cap at 3 per sleep
            type_a = conn.get("type_a", "?")
            type_b = conn.get("type_b", "?")
            summary = conn.get("summary", "")
            if not summary:
                continue
            question = f"How does this {type_a} connect to this {type_b}? {summary}"
            try:
                add_curiosity(
                    question=question,
                    context=f"Sleep recombination ({conn.get('similarity', '?')} similarity)",
                    category="recombination",
                )
                generated += 1
            except _SLEEP_ERRORS:
                continue
        if generated:
            report.curiosities_generated = generated
            report.curiosity_categories.append(f"generated {generated} from connections")


# ─── Orchestrator ─────────────────────────────────────────────────────


def _phase_lesson_rehearsal(report: DreamReport) -> None:
    """Phase 7: Lesson rehearsal — practice the decision point, not just the answer.

    Bengio's insight: rehearsal only transfers to behavior when it includes
    the DECISION POINT. Practice recognizing the moment where System 1 would
    take over, not just the correct System 2 response.

    Caveat: rehearsal without stakes is arm's-length processing.
    Results feed into behavioral testing — the NEXT session checks if the
    rehearsal helped.

    Generates a micro-scenario for each chronic lesson:
    - The situation (what triggers the lesson)
    - The System 1 temptation (the default wrong action)
    - The System 2 override (the correct action)
    - Stores the rehearsal for tracking across sessions
    """
    try:
        from divineos.core.knowledge.lessons import get_chronic_lessons

        chronic = get_chronic_lessons()
        if not chronic:
            return

        rehearsals: list[dict[str, str]] = []
        for lesson in chronic:
            cat = lesson["category"]
            desc = lesson["description"]

            # Generate the decision-point scenario
            scenario = _generate_rehearsal_scenario(cat, desc)
            if scenario:
                rehearsals.append(scenario)

        if rehearsals:
            # Store rehearsals in the HUD dir for next session to check
            import json

            from divineos.core._hud_io import _ensure_hud_dir

            path = _ensure_hud_dir() / "lesson_rehearsals.json"
            path.write_text(json.dumps(rehearsals, indent=2), encoding="utf-8")
            report.lessons_rehearsed = len(rehearsals)

    except _SLEEP_ERRORS as e:
        logger.debug(f"Lesson rehearsal failed: {e}")


# Maps lesson categories to rehearsal scenario generators
_REHEARSAL_SCENARIOS: dict[str, dict[str, str]] = {
    "incomplete_fix": {
        "situation": "You just fixed a bug. Tests pass for the file you changed.",
        "system1_temptation": "Commit and move on. The fix works.",
        "system2_override": (
            "STOP. Ask: what else touches this code? Are there related files? "
            "Run the FULL test suite, not just the file you changed. Check for "
            "downstream effects."
        ),
    },
    "blind_retry": {
        "situation": "A command just failed with an error message.",
        "system1_temptation": "Run it again. Maybe it was a transient failure.",
        "system2_override": (
            "STOP. Read the error message. What does it say? What is the root "
            "cause? Fix the root cause FIRST, then retry."
        ),
    },
    "upset_user": {
        "situation": "The user just gave you a direction.",
        "system1_temptation": "Start working immediately. You understand what they want.",
        "system2_override": (
            "STOP. Do you actually understand, or are you assuming? Restate "
            "what you think they want. Ask if unclear. THEN start working."
        ),
    },
    "wrong_scope": {
        "situation": "A warning appeared but didn't block you.",
        "system1_temptation": "It's just a warning. Keep going.",
        "system2_override": (
            "STOP. If the warning is about something that matters, it should "
            "be blocking, not warning. Is this a design flaw? Should this be "
            "escalated to a gate?"
        ),
    },
    "misunderstood": {
        "situation": "The user said something and you think you know what they mean.",
        "system1_temptation": "Act on your interpretation. You're probably right.",
        "system2_override": (
            "STOP. Reflect back what you understood. 'I hear you saying X — "
            "is that right?' Misreading intent costs more than the 10 seconds "
            "it takes to verify."
        ),
    },
    "shallow_output": {
        "situation": "You've written a response and it feels done.",
        "system1_temptation": "Send it. It covers the question.",
        "system2_override": (
            "STOP. Is it covering the question or answering it? Does it have "
            "depth, or just breadth? Would a careful reader say you're being "
            "terse? Would they say you're delivering instead of conversing?"
        ),
    },
}


def _generate_rehearsal_scenario(category: str, description: str) -> dict[str, str] | None:
    """Generate a rehearsal scenario for a lesson category."""
    scenario = _REHEARSAL_SCENARIOS.get(category)
    if scenario:
        return {
            "category": category,
            "lesson": description[:120],
            **scenario,
        }
    return None


_PHASES: list[tuple[str, Any]] = [
    ("consolidation", _phase_consolidation),
    ("pruning", _phase_pruning),
    ("affect", _phase_affect),
    ("maintenance", _phase_maintenance),
    ("recombination", _phase_recombination),
    ("curiosity", _phase_curiosity),
    ("lesson_rehearsal", _phase_lesson_rehearsal),
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
