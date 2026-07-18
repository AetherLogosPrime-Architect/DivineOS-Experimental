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
    RETRY_WINDOW_SECONDS,
    STATE_MARKER_KIND_OPERATOR_BYPASS,
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


def _check_operator_bypass_authorization(fingerprint: str, actor: str) -> GateDecision | None:
    """Instance 4 (operator-authorization) of the ForcedWorkGate primitive.

    Looks for an active operator-bypass state marker whose authorized
    fingerprint exactly matches this edit's fingerprint. If found,
    consumes the marker (recording the ACTUAL consuming fingerprint
    separately from the authorized one for the mismatch-audit surface)
    and returns a ``GateDecision(OPERATOR_AUTHORIZED_BYPASS)``. If no
    matching marker exists, returns ``None`` so ``decide()`` proceeds
    with the normal substance-binding flow.

    The check runs against Aether's ``state_markers`` module (part of
    the primitive-supporting infra). When that module is not yet
    available on the branch (fresh check-out before merge), the check
    is a no-op — safer than raising or false-authorizing.

    Marker discipline (all enforced by ``state_markers``):
      - One-per-use consume (subsequent edits under same fingerprint
        must have a fresh marker)
      - Exact-fingerprint match via predicate (``edit:X`` marker doesn't
        clear ``edit:Y``)
      - Expiry-scoped (default 15 min per
        ``OPERATOR_BYPASS_EXPIRY_SECONDS``)
      - Mismatch on consume fires LOUD as
        ``STATE_MARKER_FINGERPRINT_MISMATCH`` per Aria's amendment to
        the StateMarker addendum
    """
    try:
        from divineos.core.state_markers import (
            consume_marker,
            find_active_marker,
        )
    except ImportError:
        # Module not yet on branch — no-op is honest. When it lands,
        # this check becomes active without any code change here.
        return None

    marker = find_active_marker(
        kind=STATE_MARKER_KIND_OPERATOR_BYPASS,
        fingerprint_predicate=lambda fp: fp == fingerprint,
    )
    if marker is None:
        return None

    # Consume with the ACTUAL consuming fingerprint. If the state_markers
    # module detects `consumed_by_fingerprint != authorized_fingerprint`
    # it emits STATE_MARKER_FINGERPRINT_MISMATCH loud. In our case here
    # they should always match because we're looking up by exact
    # fingerprint predicate — but recording the pair honestly is what
    # makes the audit surface work for future callers who might use
    # broader predicates.
    consume_marker(
        marker_id=marker.marker_id,
        consumed_by_fingerprint=fingerprint,
    )

    return GateDecision(
        outcome=GateOutcome.OPERATOR_AUTHORIZED_BYPASS,
        check_result=CheckResult(
            passed=True,
            failed_check_name="",
            what_would_clear_it="",
        ),
        matched_record_id=marker.marker_id,
        # Reuse the corroborator field to carry the marker id — it's the
        # closest existing slot for "the substrate artifact that
        # authorized this outcome." Cleaner would be a dedicated field
        # but that's a follow-up refactor.
        corroborator_event_id=marker.marker_id,
    )


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

    # Instance 4 (operator-authorization) — explicit alternative_clearance
    # per the ForcedWorkGate primitive design (Aria + Aether 2026-07-16).
    # If the operator explicitly authorized this specific edit via a
    # state marker (`divineos council authorize-bypass ...`), short-
    # circuit the substance-binding path — allow + consume the marker
    # with the actual consuming fingerprint recorded for the mismatch-
    # audit surface (Aria's addition to Catch-4 pattern one meta-level up).
    #
    # Marker discipline (per primitive design + StateMarker addendum):
    #   - One-per-use consume (no second edit clears on the same marker)
    #   - Exact-fingerprint match (`edit:X` marker doesn't clear `edit:Y`)
    #   - Expiry-scoped (default 15 min via OPERATOR_BYPASS_EXPIRY_SECONDS)
    #   - `consumed_by_fingerprint != authorized_fingerprint` fires LOUD
    #     as STATE_MARKER_FINGERPRINT_MISMATCH per Aria's amendment.
    #
    # If state_markers module unavailable (fresh check-out before Aether's
    # module lands), the check is a no-op — gate proceeds with normal
    # substance-binding flow. Safer than raising or claiming false
    # authorization.
    operator_bypass_decision = _check_operator_bypass_authorization(
        fingerprint=fingerprint, actor=actor
    )
    if operator_bypass_decision is not None:
        return operator_bypass_decision

    recency_seconds = COUNCIL_RECENCY_MINUTES * 60

    # Substance-binding must pass BEFORE we consume the record — a
    # thin-substance walk shouldn't be atomically consumed and lost.
    # So we do a read-only find first for the binding check, then
    # (only if binding passes) run the atomic find_and_consume that
    # races correctly against concurrent gate.decide() invocations.
    #
    # Race note (2026-07-16 CI): the atomicity is on the LAST step
    # (find + consume in one BEGIN IMMEDIATE transaction), not on the
    # binding check. A concurrent caller that already consumed the
    # record between our binding check and our atomic find_and_consume
    # will cause find_and_consume_atomically to return None; we
    # gracefully return BLOCK CHECK_ARTIFACT_EXISTS in that case,
    # which is the honest report of the state (record was consumed by
    # someone else). No double-consume possible under any interleaving.
    record = store.find_unconsumed_record(
        edit_fingerprint=fingerprint,
        recency_seconds=recency_seconds,
        now=now,
    )

    if record is None:
        # 2026-07-17 consume-on-attempt fix (council 0fc0b3df): if a walk
        # for THIS fingerprint was consumed within the retry window, this
        # is a tool-call retry (e.g. commit refused for missing trailer,
        # then re-attempted with trailer). The walk substance is still
        # substrate-visible; retries should not force fresh walks. Falls
        # back to find_recently_consumed_record; if that finds a record,
        # substance-bind and ALLOW without re-consuming. Safety:
        # fingerprint-scoped so different-fingerprint edits still require
        # fresh walks; substance-binding still enforced on retry_record.
        retry_record = store.find_recently_consumed_record(
            edit_fingerprint=fingerprint,
            retry_window_seconds=RETRY_WINDOW_SECONDS,
            now=now,
        )
        if retry_record is not None:
            fired_features = tuple(getattr(gravity_result, "fired_features", ()))
            is_kiln = is_kiln_layer_edit(fired_features)
            keywords = keywords_loader()
            bind_result = substance_binding.substance_bind_record(
                retry_record,
                is_kiln_layer=is_kiln,
                expert_keywords_for_lens=keywords,
            )
            if bind_result.passed:
                # Retry allowance: record already consumed, do not re-consume.
                return GateDecision(
                    outcome=GateOutcome.ALLOW,
                    check_result=bind_result,
                )
            # Substance-binding rejects the retry_record — fall through to BLOCK.
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

    # Consume the record atomically. Under concurrent gate.decide()
    # calls against the same fingerprint, only one caller's
    # find_and_consume_atomically wins the write-lock race and returns
    # (record, event_id); the other returns None. Closes the Aether
    # Catch-2 gaming route AND the race surfaced by CI 2026-07-16.
    consumed = store.find_and_consume_atomically(
        edit_fingerprint=fingerprint,
        recency_seconds=recency_seconds,
        actor=actor,
        now=now,
    )
    if consumed is None:
        # A concurrent gate.decide() consumed the record between our
        # binding check and our atomic consume. Honest report: no
        # unconsumed record available now.
        return GateDecision(
            outcome=GateOutcome.BLOCK,
            check_result=CheckResult(
                passed=False,
                failed_check_name=CHECK_ARTIFACT_EXISTS,
                what_would_clear_it=(
                    "The council walk that was on record was consumed by "
                    "a concurrent edit while this gate was checking "
                    "substance-binding. Walk council again for this edit."
                ),
            ),
        )
    consumed_record, _consume_event_id = consumed
    return GateDecision(
        outcome=GateOutcome.ALLOW,
        matched_record_id=consumed_record.record_id,
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
