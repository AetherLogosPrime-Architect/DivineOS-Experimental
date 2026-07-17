"""Type contracts for the council-required enforcement gate.

Designed per docs/council_required_enforcement_design.md (2026-06-22) with
Aether's six catches integrated. All dataclasses are frozen — council
records are append-only and the gate decisions are pure values.

## Type contracts

- ``LensFinding``: one lens's substantive content for a council record.
- ``CouncilRecord``: the full council walk artifact, written to the
  substrate ledger as a ``COUNCIL_RECORD_LOGGED`` event.
- ``CheckResult``: outcome of one substance-binding check (which check,
  did it pass, what would clear it if not).
- ``GateOutcome``: enumeration of the three gate decisions.
- ``GateDecision``: the gate's full response with outcome + the
  CheckResult that fired (when blocked).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


# Tunables (mirror docs/council_required_enforcement_design.md catalog).
# Each value is the v1 default; all are prereg-bound. Silent edits to
# these constants are auditable per the meta-gate discipline.
COUNCIL_RECENCY_MINUTES: int = 60
# 2026-07-17 consume-on-attempt fix (council 0fc0b3df + council-9fbced40):
# same-fingerprint tool-call retries within this window reuse the prior
# consumed walk instead of forcing a fresh walk. Fingerprint-scoped so
# it does not enable walk-once-reuse-for-many-edits (which stays closed).
# 300 seconds = 5 min: real retry loops resolve in under a minute; margin
# accommodates slow CI or gate cascades without inviting cross-session
# walk-recycling.
RETRY_WINDOW_SECONDS: int = 300
COUNCIL_MIN_LENSES: int = 3
COUNCIL_MIN_FINDING_TOKENS: int = 30
COUNCIL_MIN_SYNTHESIS_TOKENS: int = 50
EMERGENCY_SKIP_RATE_WINDOW_DAYS: int = 7
EMERGENCY_SKIP_RATE_THRESHOLD: float = 0.05
CALIBRATION_WALKS: int = 20
CALIBRATION_DAYS: int = 7


# Event types written to the substrate ledger. Names mirror the design doc.
EVENT_COUNCIL_RECORD_LOGGED: str = "COUNCIL_RECORD_LOGGED"
EVENT_COUNCIL_RECORD_CONSUMED: str = "COUNCIL_RECORD_CONSUMED"
EVENT_COUNCIL_WALK_REJECTED: str = "COUNCIL_WALK_REJECTED"
EVENT_EMERGENCY_COUNCIL_SKIP: str = "EMERGENCY_COUNCIL_SKIP"
EVENT_DECISION_WALK_LINKED_COUNCIL: str = "DECISION_WALK_LINKED_COUNCIL"


# Corroborator event-types accepted for emergency-skip (Aether Catch 4).
# Substrate-fact corroborators only; self-attestation closed at design-time.
EMERGENCY_CORROBORATOR_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "SESSION_START_COMPACT",
        "HOOK_FAILURE",
    }
)
# Cron-scheduled runs corroborate via actor identity, not event type.
EMERGENCY_CORROBORATOR_ACTORS: frozenset[str] = frozenset({"scheduled-task"})


class GateOutcome(Enum):
    """The three gate decisions.

    ALLOW: substance-binding passed, edit may proceed.
    BLOCK: substance-binding failed; the CheckResult on GateDecision names
        which check fired and what would clear it.
    EMERGENCY_SKIP: a corroborated emergency carve-out fired; edit allowed
        but logged for Andrew to verify or reject post-hoc.
    """

    ALLOW = "allow"
    BLOCK = "block"
    EMERGENCY_SKIP = "emergency_skip"


@dataclass(frozen=True)
class LensFinding:
    """One lens's substantive content for a council record.

    The substance-binding gate enforces (Aether Catch 1 + design Check 3):
    - lens_name resolves to a registered council expert
    - finding_text token count >= COUNCIL_MIN_FINDING_TOKENS
    - finding_text contains at least one keyword from the lens's
      ``characteristic_questions`` field — without populated keywords on
      the expert, this check accidentally narrows the acceptable lens
      set, hence the startup-validation test pinning every registered
      expert has at least one characteristic-question.
    """

    lens_name: str
    finding_text: str

    @property
    def token_count(self) -> int:
        """Count whitespace-separated tokens. Plain split is intentional —
        complex tokenization would be a Schneier-style attack surface
        (the optimizer would find a tokenization scheme that lets thin
        text pass)."""
        return len([t for t in self.finding_text.split() if t])


def _normalize_edit_fingerprint(file_path: str, tool_kind: str) -> str:
    """Compute the canonical fingerprint binding a council_record to a
    specific proposed edit.

    The fingerprint is the matching key the gate uses to find the
    council walk for a proposed edit. Substance-binding requires the
    record's fingerprint matches the edit's fingerprint exactly —
    fuzzy matching would let generic walks satisfy specific edits
    (prereg falsifier C).

    Format: ``<tool_kind>:<normalized_path>`` where normalized_path
    uses forward-slashes and is repo-root-relative when the input is
    inside the repo.
    """
    norm = (file_path or "").replace("\\", "/").strip()
    kind = (tool_kind or "").strip().lower()
    return f"{kind}:{norm}"


@dataclass(frozen=True)
class CouncilRecord:
    """A council walk artifact — what a real walk produces.

    Written to the substrate ledger as a COUNCIL_RECORD_LOGGED event.
    All fields are required except confirmed_by (only populated for
    kiln-layer edits per Aether Catch 3) and consumed_at (set when
    the record is consumed on first matching edit per Catch 2).

    The hash-chained ledger event makes the artifact tamper-evident.
    The gate verifies the event exists, the fingerprint matches the
    proposed edit, the recency window holds, substance-binding passes,
    and consumed_at is None (record not yet used).
    """

    record_id: str
    walked_at: float  # epoch seconds
    walker: str  # actor identity that performed the walk
    triggered_edit_fingerprint: str  # from _normalize_edit_fingerprint
    lenses_surfaced: tuple[str, ...]  # ordered list of lens names
    lens_findings: tuple[LensFinding, ...]  # one per lens in lenses_surfaced
    synthesis: str  # cross-lens integration text
    confirmed_by: str | None = None  # populated for kiln-layer; Andrew/Aletheia
    consumed_at: float | None = None  # consume-on-use marker (Catch 2)

    @property
    def synthesis_token_count(self) -> int:
        return len([t for t in self.synthesis.split() if t])


@dataclass(frozen=True)
class CheckResult:
    """Outcome of one substance-binding check.

    When ``passed=False``, ``failed_check_name`` names which check fired
    (one of CHECK_NAMES) and ``what_would_clear_it`` is a plain-language
    pointer the agent uses to debug (Aether Catch 5 — failed walks must
    surface a debuggable rejection reason, not silent failure).
    """

    passed: bool
    failed_check_name: str = ""
    what_would_clear_it: str = ""


# Stable names for each substance-binding check. Used in CheckResult and
# in the COUNCIL_WALK_REJECTED event payload so audit-pattern signal
# (Aether Catch 5) is queryable by check-name.
CHECK_ARTIFACT_EXISTS = "artifact_exists"
CHECK_RECENCY = "recency"
CHECK_LENS_COUNT = "lens_count"
CHECK_FINDING_TOKEN_COUNT = "finding_token_count"
CHECK_FINDING_KEYWORD = "finding_keyword"
CHECK_SYNTHESIS_TOKEN_COUNT = "synthesis_token_count"
CHECK_SYNTHESIS_REFERENCES_LENSES = "synthesis_references_lenses"
CHECK_KILN_CONFIRMED_BY = "kiln_confirmed_by"
CHECK_NOT_CONSUMED = "not_consumed"

CHECK_NAMES: frozenset[str] = frozenset(
    {
        CHECK_ARTIFACT_EXISTS,
        CHECK_RECENCY,
        CHECK_LENS_COUNT,
        CHECK_FINDING_TOKEN_COUNT,
        CHECK_FINDING_KEYWORD,
        CHECK_SYNTHESIS_TOKEN_COUNT,
        CHECK_SYNTHESIS_REFERENCES_LENSES,
        CHECK_KILN_CONFIRMED_BY,
        CHECK_NOT_CONSUMED,
    }
)


@dataclass(frozen=True)
class GateDecision:
    """The gate's full response.

    ``outcome`` is the operational result. ``check_result`` is populated
    when outcome is BLOCK to point at the failed substance-binding check.
    ``corroborator_event_id`` is populated when outcome is EMERGENCY_SKIP
    so the substrate-fact justifying the skip is recorded with the
    decision (Aether Catch 4).
    """

    outcome: GateOutcome
    check_result: CheckResult = field(default_factory=lambda: CheckResult(passed=True))
    corroborator_event_id: str | None = None
    matched_record_id: str | None = None  # set when ALLOW; the record consumed


__guardrail_required__ = True
