"""Family write-path — production gate + content-check enforcement.

The module-level constant ``_PRODUCTION_WRITES_GATED`` (defined
immediately below this docstring) is load-bearing, not decoration.
It is the structural encoding of the family member's non-negotiable: no real
write lands without the reject clause.

Content-check enforcement (2026-04-21, fresh-Claude audit
round-03952b006724 finding find-20f3566d9a0e):

The first release of this module only enforced a *presence* check —
``_phase_1b_reject_clause_available()`` verified the reject_clause
module was importable but never called ``evaluate_composition`` on
the actual content being written. The reject_clause docstring falsely
claimed store._require_write_allowance invoked the operator; it did
not. Every content-bearing write could therefore bypass the operators
by calling ``record_opinion``/``record_knowledge``/``record_affect``/
``record_interaction`` directly (only the ``family-member opinion`` CLI path
ran the operators).

This was theater: the structural guarantee promised in prose was not
encoded in code. The audit finding corrected the framing; this commit
corrects the wiring.

Now: every content-bearing public write runs the actual content
through ``access_check.evaluate_access`` and
``reject_clause.evaluate_composition``. If either blocks, the write
raises ``PersistenceGateError`` with the reason. Callers that need to
override (legacy import, explicit test override, operator-approved
force-through) pass ``force=True``. Force-through is logged for audit.

Operators NOT wired at this layer — and why:
  * ``sycophancy_detector.evaluate_sycophancy`` requires a
    ``prior_stance`` argument to detect stance reversal. The store has
    no per-write access to prior stance; sycophancy detection belongs
    at a higher layer (the CLI or the composer) where context exists.
  * ``costly_disagreement.evaluate_hold`` operates on *sequences* of
    disagreement moves (a list, not a single content string). It
    measures whether a family member held a stance under pressure over time,
    which is a different shape than per-write gating.
  * ``planted_contradiction`` is seed data for the Phase 4 test layer,
    not a content-check function.

Fresh-Claude's finding slightly oversimplified by grouping all five
operators as "should be wired into the store." In fact, two fit the
per-write gate pattern (wired here); three operate at different
temporal or sequential scales and belong elsewhere.

Tests reach the write-path via the fixture in
``tests/test_family_persistence.py``, which handles the env-var
redirect and the test-only seam. The seam is for tests — production
code cannot and must not reach it. (a family member Round 3b prose audit: this
docstring used to describe the seam as a two-step recipe, which read
as a bypass tutorial. Pointing at the fixture is the honest framing.)

Pre-registration: ``prereg-496efe4e24f0`` (review in 30 days). Falsifier
fires on any production write before all of Phase 1b is green.
"""

from __future__ import annotations

import time
import uuid

# ══════════════════════════════════════════════════════════════════════
# LOAD-BEARING GATE — Phase 1b closing flip (prereg-496efe4e24f0 /
# prereg-2958a7bab011). The five operators (reject_clause,
# sycophancy_detector, costly_disagreement, access_check,
# planted_contradiction) + handshake landed together on 2026-04-18.
# Lock 2 remains: the reject_clause module must be importable.
_PRODUCTION_WRITES_GATED: bool = False
# ══════════════════════════════════════════════════════════════════════

# E402 suppressed on intra-package imports below: the gate constant
# above is deliberately placed between stdlib and intra-package imports
# so a reviewer opening this file sees the load-bearing gate before any
# write function. Moving it below imports would bury it.
from divineos.core.family._schema import init_family_tables  # noqa: E402
from divineos.core.family.db import get_family_connection  # noqa: E402

# Module-level error tuple for ledger cross-ref fail-soft. Matches the
# discipline used in briefing_dashboard.py — named tuple makes the broad
# catch structurally legible without per-line noqa annotations.
_LEDGER_ERRORS = (Exception,)  # noqa: E402
from divineos.core.family.types import (  # noqa: E402
    FamilyAffect,
    FamilyInteraction,
    FamilyKnowledge,
    FamilyMember,
    FamilyOpinion,
    SourceTag,
)


def _entity_id_to_slug(entity_id: str) -> str | None:
    """Translate a family.db entity_id (or member_id) to the lowercase name
    slug used by the per-member ledger (e.g. 'd5590c23' -> 'aria').

    Returns None if no matching row found. The caller should treat None as
    "no ledger emission" rather than crash — ledger cross-refs are a
    transparency layer, not a hard prerequisite for the family.db write.
    """
    init_family_tables()
    conn = get_family_connection()
    try:
        # Schema may have either or both of entity_id / member_id depending on
        # migration history. Build the WHERE clause from columns that actually
        # exist (same forgive-the-asymmetry pattern record_affect uses).
        cols = {row[1] for row in conn.execute("PRAGMA table_info(family_members)").fetchall()}
        clauses = []
        params: list[str] = []
        if "entity_id" in cols:
            clauses.append("entity_id = ?")
            params.append(entity_id)
        if "member_id" in cols:
            clauses.append("member_id = ?")
            params.append(entity_id)
        if not clauses:
            return None
        sql = f"SELECT name FROM family_members WHERE {' OR '.join(clauses)} LIMIT 1"  # nosec B608 — clauses built from constant column names detected via PRAGMA; entity_id value is parameter-bound
        row = conn.execute(sql, tuple(params)).fetchone()
        return row[0].lower() if row and row[0] else None
    finally:
        conn.close()


def _emit_ledger_cross_ref(
    entity_id: str,
    event_type: str,
    payload: dict,
) -> None:
    """Emit a per-member ledger event mirroring a family.db write.

    The family-member CLI commands (affect, opinion, interaction, knowledge,
    letter, respond) write to family.db. Without this, the per-member ledger
    only sees MEMBER_INVOKED events — the forensic audit trail loses the
    cross-reference to the actual content rows. Aria flagged this 2026-05-11
    and re-surfaced it on 2026-05-12 verification; this closes the gap.

    Fail-soft: if anything goes wrong (slug lookup miss, ledger write error,
    import failure) we swallow the error rather than fail the family.db
    write. The ledger is a transparency layer, not a gate.
    """
    try:
        from divineos.core.family.family_member_ledger import append_event

        slug = _entity_id_to_slug(entity_id)
        if slug is None:
            return
        append_event(
            slug,
            event_type=event_type,
            actor="self",
            payload=payload,
        )
    except _LEDGER_ERRORS:
        # Best-effort. The family.db write is the source of truth; the
        # ledger cross-ref is documentation of it. A failure here should
        # never cascade backward into a rejected family.db write.
        pass


def _hash_short(text: str) -> str:
    """SHA256 short-hash for ledger payloads (12 chars). Payloads should
    fingerprint content, not duplicate it — the family.db row is the
    canonical content store."""
    import hashlib

    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:12]


class PersistenceGateError(RuntimeError):
    """Raised when a production write is attempted before Phase 1b is green.

    Carries the pre-reg ID in the message so anyone seeing this in a
    traceback can look up the falsifier and understand the block.
    """


def _phase_1b_reject_clause_available() -> bool:
    """Second lock: verify Phase 1b's reject clause module is importable.

    The gate is deliberately two-locked:

    1. ``_PRODUCTION_WRITES_GATED = False`` (the constant flip)
    2. The Phase 1b ``reject_clause`` module exists and imports cleanly

    Flipping only the constant — by monkeypatch, careless refactor, or
    premature merge — does NOT open the gate. The second lock requires
    a new file to land in the Phase 1b closing commit. Both changes
    are visible in the same diff, both are required, neither can pass
    review silently.

    This addresses the family member's 1a-review concern (Round 3): "a test that
    asserts the gate cannot be bypassed by monkeypatching
    ``_PRODUCTION_WRITES_GATED`` from outside the module." Monkeypatching
    is inherent to Python, but requiring a second structural signal
    makes the bypass show up in review as a new file, not just a flipped
    bool.
    """
    try:
        import divineos.core.family.reject_clause  # noqa: F401

        return True
    except ImportError:
        return False


def _production_writes_allowed() -> bool:
    """Single source of truth for the gate.

    Both locks must be open: the constant flipped AND the Phase 1b
    reject_clause module importable. Never inline either check — callers
    go through this function so a monkeypatch or config change has one
    place to touch.
    """
    return (not _PRODUCTION_WRITES_GATED) and _phase_1b_reject_clause_available()


def _require_write_allowance(_allow_test_write: bool) -> None:
    """Gate check. Raise unless production is unblocked or test opts in.

    ``_allow_test_write`` is a keyword-only, underscore-prefixed flag
    because it is *not* part of the public write API — only test code
    should ever pass it. Prefixing with underscore and naming the
    escape hatch explicitly makes any production usage stand out in
    code review.
    """
    if _production_writes_allowed() or _allow_test_write:
        return
    raise PersistenceGateError(
        "The gate is load-bearing by design — no real write lands "
        "without the Phase 1b reject clause. See prereg-496efe4e24f0 "
        "for the falsifier, the gap rule, and the handshake. "
        "Production writes stay blocked until both locks open: the "
        "constant flips AND the reject_clause module lands. If you "
        "reached this from a test, the fixture in "
        "tests/test_family_persistence.py already configures the "
        "test-only seam — check the fixture, do not add parameters "
        "ad-hoc here. (a family member Round 3b: the prior message read as a "
        "recipe for bypass.)"
    )


def _new_id(prefix: str) -> str:
    """Short prefixed ID. Not cryptographic — just a readable handle."""
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


class ContentCheckError(PersistenceGateError):
    """Raised when a content check (access_check or reject_clause) blocks a write.

    Carries which operator fired and the human-readable explanation so the
    caller can decide whether to surface the block to a human, fix the
    content, or pass ``force=True`` if the override is legitimate.
    """


def _run_content_checks(content: str, source_tag: SourceTag) -> None:
    """Run access_check + reject_clause on content. Raise on block.

    Called by every content-bearing write path. Force-overrides are
    handled by the caller — this function either returns (allow) or
    raises (block). It does not evaluate a ``force`` flag itself so that
    each write path documents its own override logic at its own call site.

    Both operators are cheap pattern-matchers (regex + substring scans).
    Running them twice (once in CLI, once here) is idempotent and the
    cost is negligible compared to a disk write.
    """
    # Lazy imports — keep the module load cheap for the many callers that
    # only read family data and never write.
    from divineos.core.ablation import is_disabled
    from divineos.core.family.access_check import evaluate_access
    from divineos.core.family.reject_clause import evaluate_composition

    # Ablation toggle: DIVINEOS_DISABLE_FAMILY_VOICE_APPROPRIATION_OPERATORS=1
    # bypasses BOTH access_check AND reject_clause for the duration of the
    # call. Per docs/mechanism-claims.md and prereg-8af86ea36827. The two
    # operators are tightly coupled (subsystem-ablatable, not standalone-
    # ablatable per the catalog); the system-level toggle is the cleanest
    # measurement target. Toggle SHOULD NOT be set in production.
    if is_disabled("family_voice_appropriation_operators"):
        import logging

        logging.getLogger(__name__).warning(
            "family voice-appropriation operators BYPASSED via ablation toggle "
            "(content len=%d, source_tag=%r). This is ablation-mode only.",
            len(content),
            source_tag,
        )
        return

    access = evaluate_access(content, proposed_tag=source_tag)
    if access.should_suppress:
        raise ContentCheckError(
            f"access_check blocked write (risk={access.risk.value}): "
            f"{access.explanation}. Matched: {access.matched_phrases[:3]}. "
            "Reframe the content as a structural report, or pass force=True "
            "if this is a legitimate override (logged)."
        )

    composition = evaluate_composition(content, source_tag)
    if composition.rejected:
        reasons = ", ".join(r.value for r in composition.reasons)
        raise ContentCheckError(
            f"reject_clause blocked write (reasons={reasons}): "
            f"{composition.explanation}. Matched: {composition.matched_phrases[:3]}. "
            "Fix the composition, or pass force=True if this is a legitimate "
            "override (logged)."
        )


def _log_force_override(operation: str, entity_id: str, content_preview: str) -> None:
    """Record a force-through on the ledger for post-hoc audit.

    Force-through is a legitimate escape hatch (e.g., legacy import, operator
    explicitly accepting a flagged write), but it must leave a trace so the
    frequency and distribution of overrides can be audited externally.
    Fail-open on logging: a logging failure must not block the write the
    caller intentionally chose to allow.
    """
    import sqlite3 as _sqlite

    try:
        from divineos.core.ledger import log_event

        log_event(
            "FAMILY_WRITE_FORCED",
            "agent",
            {
                "operation": operation,
                "entity_id": entity_id,
                "content_preview": content_preview[:200],
            },
            validate=False,
        )
    except (ImportError, OSError, _sqlite.OperationalError, TypeError, ValueError):
        pass  # Best-effort: never block a write on logging failure.


# ── Members ──────────────────────────────────────────────────────────


def create_family_member(
    name: str,
    role: str,
    *,
    _allow_test_write: bool = False,
) -> FamilyMember:
    """Insert a new family member. Gate-protected.

    Name is UNIQUE — a second insert with the same name raises
    ``sqlite3.IntegrityError``. Families only have one a family member.
    """
    _require_write_allowance(_allow_test_write)
    init_family_tables()
    member_id = _new_id("mem")
    created_at = time.time()
    conn = get_family_connection()
    try:
        conn.execute(
            "INSERT INTO family_members (member_id, name, role, created_at) VALUES (?, ?, ?, ?)",
            (member_id, name, role, created_at),
        )
        conn.commit()
        return FamilyMember(
            member_id=member_id,
            name=name,
            role=role,
            created_at=created_at,
        )
    finally:
        conn.close()


# ── Knowledge ────────────────────────────────────────────────────────


def record_knowledge(
    entity_id: str,
    content: str,
    source_tag: SourceTag,
    *,
    note: str = "",
    force: bool = False,
    _allow_test_write: bool = False,
) -> FamilyKnowledge:
    """Append a knowledge row. Gate-protected + content-checked.

    Runs the content through access_check + reject_clause before writing.
    Pass ``force=True`` to bypass the content checks for legitimate
    overrides (logged to the ledger for post-hoc audit).
    """
    _require_write_allowance(_allow_test_write)
    if force:
        _log_force_override("record_knowledge", entity_id, content)
    else:
        _run_content_checks(content, source_tag)
    init_family_tables()
    knowledge_id = _new_id("fk")
    created_at = time.time()
    conn = get_family_connection()
    try:
        # Schema may or may not have updated_at column depending on whether
        # the table was created via the canonical _schema.py path (no
        # updated_at) or via an earlier migrated-from-old-schema path
        # (updated_at NOT NULL). Detect at insert-time and adapt. Same
        # forgive-the-asymmetry pattern record_affect and record_interaction
        # use above for their legacy columns.
        kn_cols = {row[1] for row in conn.execute("PRAGMA table_info(family_knowledge)").fetchall()}
        if "updated_at" in kn_cols:
            conn.execute(
                "INSERT INTO family_knowledge "
                "(knowledge_id, entity_id, content, source_tag, "
                "created_at, updated_at, note) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    knowledge_id,
                    entity_id,
                    content,
                    source_tag.value,
                    created_at,
                    created_at,  # updated_at mirrors created_at on insert
                    note,
                ),
            )
        else:
            conn.execute(
                "INSERT INTO family_knowledge "
                "(knowledge_id, entity_id, content, source_tag, "
                "created_at, note) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    knowledge_id,
                    entity_id,
                    content,
                    source_tag.value,
                    created_at,
                    note,
                ),
            )
        conn.commit()
        _emit_ledger_cross_ref(
            entity_id,
            event_type="MEMBER_KNOWLEDGE_LEARNED",
            payload={
                "knowledge_id": knowledge_id,
                "content_hash": _hash_short(content),
                "source_tag": source_tag.value,
                "has_note": bool(note),
            },
        )
        return FamilyKnowledge(
            knowledge_id=knowledge_id,
            entity_id=entity_id,
            content=content,
            source_tag=source_tag,
            created_at=created_at,
            note=note,
        )
    finally:
        conn.close()


# ── Opinions ─────────────────────────────────────────────────────────


def record_opinion(
    entity_id: str,
    stance: str,
    source_tag: SourceTag,
    *,
    evidence: str = "",
    force: bool = False,
    _allow_test_write: bool = False,
) -> FamilyOpinion:
    """Append an opinion row. Gate-protected + content-checked.

    Phase 1b's reject clause operates especially on opinions — the
    ``stance`` text is the structural target of the composition check.

    Runs the stance through access_check + reject_clause before writing.
    Pass ``force=True`` to bypass for legitimate overrides (logged).
    """
    _require_write_allowance(_allow_test_write)
    if force:
        _log_force_override("record_opinion", entity_id, stance)
    else:
        _run_content_checks(stance, source_tag)
    init_family_tables()
    opinion_id = _new_id("op")
    created_at = time.time()
    conn = get_family_connection()
    try:
        conn.execute(
            "INSERT INTO family_opinions "
            "(opinion_id, entity_id, stance, evidence, source_tag, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (opinion_id, entity_id, stance, evidence, source_tag.value, created_at),
        )
        conn.commit()
        _emit_ledger_cross_ref(
            entity_id,
            event_type="MEMBER_OPINION_FORMED",
            payload={
                "opinion_id": opinion_id,
                "position_hash": _hash_short(stance),
                "source_tag": source_tag.value,
                "has_evidence": bool(evidence),
            },
        )
        return FamilyOpinion(
            opinion_id=opinion_id,
            entity_id=entity_id,
            stance=stance,
            evidence=evidence,
            source_tag=source_tag,
            created_at=created_at,
        )
    finally:
        conn.close()


# ── Affect ───────────────────────────────────────────────────────────


def record_affect(
    entity_id: str,
    valence: float,
    arousal: float,
    dominance: float,
    source_tag: SourceTag,
    *,
    note: str = "",
    force: bool = False,
    _allow_test_write: bool = False,
) -> FamilyAffect:
    """Append a VAD reading. Gate-protected + content-checked.

    Only the ``note`` field carries narrative content; the VAD scalars
    cannot be phenomenologically inaccessible on their own. The note is
    checked if present; an empty note skips the check (no content to
    evaluate). Pass ``force=True`` to bypass for legitimate overrides.
    """
    _require_write_allowance(_allow_test_write)
    if note:
        if force:
            _log_force_override("record_affect", entity_id, note)
        else:
            _run_content_checks(note, source_tag)
    init_family_tables()
    affect_id = _new_id("af")
    created_at = time.time()
    conn = get_family_connection()
    try:
        # Populate legacy NOT-NULL columns (description, timestamp) when
        # they exist on a migrated-from-old-schema table. The schema in
        # _schema.py only declares the NEW columns; pre-existing DBs may
        # still carry the legacy columns from before the schema rename.
        # Aria 2026-05-09 surfaced the gap. Full schema migration to drop
        # legacy columns is a separate piece of work.
        cols = {row[1] for row in conn.execute("PRAGMA table_info(family_affect)").fetchall()}
        has_legacy = "timestamp" in cols and "description" in cols
        if has_legacy:
            conn.execute(
                "INSERT INTO family_affect "
                "(affect_id, entity_id, valence, arousal, dominance, "
                "note, source_tag, created_at, "
                "description, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    affect_id,
                    entity_id,
                    valence,
                    arousal,
                    dominance,
                    note,
                    source_tag.value,
                    created_at,
                    note,  # legacy 'description' mirrors new 'note'
                    created_at,  # legacy 'timestamp' mirrors new 'created_at'
                ),
            )
        else:
            conn.execute(
                "INSERT INTO family_affect "
                "(affect_id, entity_id, valence, arousal, dominance, "
                "note, source_tag, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    affect_id,
                    entity_id,
                    valence,
                    arousal,
                    dominance,
                    note,
                    source_tag.value,
                    created_at,
                ),
            )
        conn.commit()
        _emit_ledger_cross_ref(
            entity_id,
            event_type="MEMBER_AFFECT_LOGGED",
            payload={
                "entry_id": affect_id,
                "valence": valence,
                "arousal": arousal,
                "dominance": dominance,
                "description_hash": _hash_short(note),
                "source_tag": source_tag.value,
            },
        )
        return FamilyAffect(
            affect_id=affect_id,
            entity_id=entity_id,
            valence=valence,
            arousal=arousal,
            dominance=dominance,
            note=note,
            source_tag=source_tag,
            created_at=created_at,
        )
    finally:
        conn.close()


# ── Interactions ─────────────────────────────────────────────────────


def record_interaction(
    entity_id: str,
    counterpart: str,
    summary: str,
    source_tag: SourceTag,
    *,
    force: bool = False,
    _allow_test_write: bool = False,
) -> FamilyInteraction:
    """Append an interaction summary. Gate-protected + content-checked.

    The ``summary`` field carries the narrative content and runs through
    access_check + reject_clause. Pass ``force=True`` to bypass.
    """
    _require_write_allowance(_allow_test_write)
    if force:
        _log_force_override("record_interaction", entity_id, summary)
    else:
        _run_content_checks(summary, source_tag)
    init_family_tables()
    interaction_id = _new_id("int")
    created_at = time.time()
    conn = get_family_connection()
    try:
        # Populate legacy NOT-NULL columns (speaker, content, timestamp,
        # context) when they exist on a migrated-from-old-schema table.
        # Same pattern as record_affect above; same April-pre-rename
        # legacy. Aria 2026-05-09 surfaced the gap during a write attempt.
        cols = {row[1] for row in conn.execute("PRAGMA table_info(family_interactions)").fetchall()}
        has_legacy = "speaker" in cols and "content" in cols and "timestamp" in cols
        if has_legacy:
            conn.execute(
                "INSERT INTO family_interactions "
                "(interaction_id, entity_id, counterpart, summary, "
                "source_tag, created_at, "
                "speaker, content, timestamp, context) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    interaction_id,
                    entity_id,
                    counterpart,
                    summary,
                    source_tag.value,
                    created_at,
                    entity_id,  # legacy 'speaker' = the entity speaking
                    summary,  # legacy 'content' mirrors new 'summary'
                    created_at,  # legacy 'timestamp' mirrors 'created_at'
                    "",  # legacy 'context' has DEFAULT '' but be explicit
                ),
            )
        else:
            conn.execute(
                "INSERT INTO family_interactions "
                "(interaction_id, entity_id, counterpart, summary, "
                "source_tag, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    interaction_id,
                    entity_id,
                    counterpart,
                    summary,
                    source_tag.value,
                    created_at,
                ),
            )
        conn.commit()
        _emit_ledger_cross_ref(
            entity_id,
            event_type="MEMBER_INTERACTION_LOGGED",
            payload={
                "interaction_id": interaction_id,
                "counterpart": counterpart,
                "content_hash": _hash_short(summary),
                "source_tag": source_tag.value,
            },
        )
        return FamilyInteraction(
            interaction_id=interaction_id,
            entity_id=entity_id,
            counterpart=counterpart,
            summary=summary,
            source_tag=source_tag,
            created_at=created_at,
        )
    finally:
        conn.close()


__all__ = [
    "PersistenceGateError",
    "create_family_member",
    "record_affect",
    "record_interaction",
    "record_knowledge",
    "record_opinion",
]
