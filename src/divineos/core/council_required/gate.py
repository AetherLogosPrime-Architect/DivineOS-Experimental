"""The council-required enforcement gate — PreToolUse entry point.

Composes the pieces from types.py, store.py, and substance_binding.py
into a single decision per proposed edit:

1. Ask the gravity classifier whether this edit fires
   ``is_council_required``. If False, ALLOW immediately.
2. Otherwise, look up an unconsumed council_record for the edit's
   fingerprint within the recency window.
3. If no record exists, BLOCK with ``CHECK_ARTIFACT_EXISTS``.
4. If record exists, run substance-binding (cheap → expensive). If any
   check fails, BLOCK with that check's reason.
5. If substance-binding passes, consume the record and ALLOW.
6. Emergency-skip path is offered separately via ``decide_with_emergency_skip``;
   the caller (CLI / hook) decides whether to invoke it after a BLOCK.

The gate is read-mostly. The only ledger write on the default path is
the ``COUNCIL_RECORD_CONSUMED`` event written when a record is matched
and substance-binds. Failed lookups don't write — those are not
attempts at the gate; they're attempts at the edit.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from divineos.core.council_required import store, substance_binding
from divineos.core.council_required.types import (
    CHECK_ARTIFACT_EXISTS,
    COUNCIL_RECENCY_MINUTES,
    EMERGENCY_CORROBORATOR_ACTORS,
    EMERGENCY_CORROBORATOR_EVENT_TYPES,
    CheckResult,
    GateDecision,
    GateOutcome,
    _normalize_edit_fingerprint,
)


# Type alias for the gravity-classifier callable. Injected so the gate
# stays independent of the classifier's import surface; the hook script
# wires the real classifier in. Tests can pass a stub.
GravityFn = Callable[[str, tuple[str, ...], str], Any]

# Type alias for the expert-keywords-registry loader. Likewise injected.
KeywordsLoaderFn = Callable[[], dict[str, set[str]]]


def is_kiln_layer_edit(fired_features: tuple[str, ...]) -> bool:
    """Return True if the gravity-classifier fired the ``edit-kiln-layer``
    feature for the proposed edit.

    Kiln-layer is the highest-stakes tier — foundational truths,
    seed.json — which per Aether Catch 3 requires external-actor
    confirmation in addition to substance-binding.
    """
    return "edit-kiln-layer" in fired_features


def decide(
    tool_name: str,
    file_paths: tuple[str, ...],
    bash_command: str,
    gravity_fn: GravityFn,
    keywords_loader: KeywordsLoaderFn,
    now: float | None = None,
    actor: str = "agent",
) -> GateDecision:
    """Make a gate decision for a proposed edit.

    The gravity_fn and keywords_loader are passed in (dependency
    inversion) so the gate is testable without spinning up the full
    classifier + expert-library import graph.
    """
    gravity_result = gravity_fn(tool_name, file_paths, bash_command)
    is_council_required = bool(getattr(gravity_result, "is_council_required", False))
    if not is_council_required:
        return GateDecision(outcome=GateOutcome.ALLOW)

    # Pick the first file path as the fingerprint anchor. Multi-file
    # tools (MultiEdit) fingerprint on the first; this v1 design accepts
    # one council walk per primary file. A follow-up could fingerprint
    # the entire path-set, but doing so risks letting a generic walk on
    # an unrelated file in the same call clear the gate by collision.
    primary_path = file_paths[0] if file_paths else ""
    if not primary_path and bash_command:
        # For Bash tools the fingerprint anchors on the command head.
        primary_path = bash_command.strip().split(maxsplit=1)[0] if bash_command else ""
    fingerprint = _normalize_edit_fingerprint(primary_path, tool_name)

    recency_seconds = COUNCIL_RECENCY_MINUTES * 60
    record = store.find_unconsumed_record(
        edit_fingerprint=fingerprint,
        recency_seconds=recency_seconds,
        now=now,
    )

    if record is None:
        return GateDecision(
            outcome=GateOutcome.BLOCK,
            check_result=CheckResult(
                passed=False,
                failed_check_name=CHECK_ARTIFACT_EXISTS,
                what_would_clear_it=(
                    "No unconsumed council walk on record for this edit "
                    f"(fingerprint: {fingerprint!r}). Run `divineos mansion "
                    "council` for the question this edit raises, then log "
                    "the lens-by-lens record via `divineos council log` so "
                    "substance-binding can resolve."
                ),
            ),
        )

    fired_features = tuple(getattr(gravity_result, "fired_features", ()))
    is_kiln = is_kiln_layer_edit(fired_features)
    keywords = keywords_loader()

    bind_result = substance_binding.substance_bind_record(
        record,
        is_kiln_layer=is_kiln,
        expert_keywords_for_lens=keywords,
    )
    if not bind_result.passed:
        return GateDecision(
            outcome=GateOutcome.BLOCK,
            check_result=bind_result,
        )

    # Consume the record. From this point the record cannot satisfy a
    # subsequent edit; the consume-on-use semantics close the walk-once-
    # edit-many gaming route (Aether Catch 2).
    store.consume_record(
        record_id=record.record_id,
        edit_fingerprint=fingerprint,
        actor=actor,
        now=now,
    )
    return GateDecision(
        outcome=GateOutcome.ALLOW,
        matched_record_id=record.record_id,
    )


def decide_with_emergency_skip(
    tool_name: str,
    file_paths: tuple[str, ...],
    bash_command: str,
    gravity_fn: GravityFn,
    keywords_loader: KeywordsLoaderFn,
    corroborator_event_id: str,
    emergency_reason: str,
    now: float | None = None,
    actor: str = "agent",
) -> GateDecision:
    """Emergency-skip path: bypass substance-binding because a substrate-
    fact corroborates that the agent is unreachable / cannot defer.

    Aether Catch 4: ``corroborator_event_id`` must resolve to an actual
    substrate event of an accepted type (mid-compaction, hook-failure)
    or accepted actor (scheduled-task). Without resolution, the
    emergency-skip itself BLOCKS — closing the self-attestation route
    that would otherwise re-introduce the route-around through the
    emergency channel.
    """
    corroborator = store.find_corroborator_event(
        corroborator_event_id,
        accepted_event_types=EMERGENCY_CORROBORATOR_EVENT_TYPES,
        accepted_actors=EMERGENCY_CORROBORATOR_ACTORS,
    )
    if corroborator is None:
        return GateDecision(
            outcome=GateOutcome.BLOCK,
            check_result=CheckResult(
                passed=False,
                failed_check_name="emergency_corroborator_missing",
                what_would_clear_it=(
                    "Emergency-skip requires a substrate-fact corroborator. "
                    f"Provided event_id {corroborator_event_id!r} did not "
                    "resolve to an accepted-type event or accepted-actor "
                    "event in the ledger. Self-attested 'unreachable' is "
                    "not certified by this gate."
                ),
            ),
        )

    primary_path = file_paths[0] if file_paths else ""
    if not primary_path and bash_command:
        primary_path = bash_command.strip().split(maxsplit=1)[0] if bash_command else ""
    fingerprint = _normalize_edit_fingerprint(primary_path, tool_name)

    skip_event_id = store.log_emergency_skip(
        edit_fingerprint=fingerprint,
        reason=emergency_reason,
        corroborator_event_id=corroborator_event_id,
        actor=actor,
    )
    return GateDecision(
        outcome=GateOutcome.EMERGENCY_SKIP,
        corroborator_event_id=corroborator_event_id,
        matched_record_id=skip_event_id,
    )


def format_block_message(decision: GateDecision, fingerprint: str = "") -> str:
    """Human-readable block message for the hook script's stderr output.

    The hook captures stdout/stderr to surface to the agent at composition
    time. This formatter mirrors the substrate-modification-gravity hook
    style so the rejection reads consistently with other gates.
    """
    if decision.outcome != GateOutcome.BLOCK:
        return ""
    check = decision.check_result
    lines = [
        "## COUNCIL-REQUIRED GATE FIRED",
        "",
        "This edit fires the gravity classifier's council-required tier and",
        "no eligible council walk is on record. The gate blocks until",
        "substance-bound evidence of a real walk exists.",
        "",
        f"Failed check: {check.failed_check_name}",
        "",
        check.what_would_clear_it,
        "",
    ]
    if fingerprint:
        lines.append(f"Edit fingerprint: {fingerprint}")
    lines.extend(
        [
            "",
            "Emergency-skip (only with substrate-fact corroborator):",
            "  divineos council emergency-skip --reason '...' --corroborator <event-id>",
        ]
    )
    return "\n".join(lines)


def now_seconds() -> float:
    """Wall-clock now in epoch seconds. Indirection for tests."""
    return time.time()


__guardrail_required__ = True
