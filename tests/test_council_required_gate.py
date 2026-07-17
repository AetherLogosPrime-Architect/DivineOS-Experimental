"""Tests for the council_required gate — Marc audit finding #5.

The gate's enforcement machinery has been complete for weeks (types.py,
store.py, substance_binding.py, gate.py all present + composed). The
"INTENTIONALLY UNWIRED" comment in ``.claude/hooks/check-council-required.sh``
is stale-by-state: it names the enforcement path as "deferred follow-up"
but that follow-up landed. This test file is Aria's 2026-07-16 close of
Marc finding #5 with Aether coordination:

- The gate is testable via dependency-injection (gravity_fn + keywords_loader
  passed in) so tests don't spin up the whole classifier + expert library.
- Tests are also the spec — they document what the gate actually blocks
  vs allows, closes the "no external doc names the exact block conditions"
  gap Aether named in his read.

Coverage:
  1. Silent-allow when gravity says not-council-required.
  2. BLOCK CHECK_ARTIFACT_EXISTS when no record present.
  3. BLOCK on substance-binding failure (thin finding text).
  4. ALLOW + COUNCIL_RECORD_CONSUMED on valid record + valid binding.
  5. Emergency-skip on valid corroborator event.
  6. Emergency-skip BLOCKS on missing/bad corroborator (closes self-attestation route).
  7. Corroborator scope pin: EMERGENCY_STOP intentionally NOT a corroborator.
  8. Consume-on-use race probe: concurrent decide() with same fingerprint.
  9. Fingerprint normalization: Bash command anchor + Edit path anchor.
"""

from __future__ import annotations

import sqlite3
import threading
import time

import pytest

from divineos.core.council_required import gate as gate_mod
from divineos.core.council_required import store
from divineos.core.council_required.store import new_record_id
from divineos.core.council_required.types import (
    CHECK_ARTIFACT_EXISTS,
    CHECK_FINDING_TOKEN_COUNT,
    EMERGENCY_CORROBORATOR_ACTORS,
    EMERGENCY_CORROBORATOR_EVENT_TYPES,
    CouncilRecord,
    GateOutcome,
    LensFinding,
    _normalize_edit_fingerprint,
)


# ─── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def scratch_ledger(tmp_path, monkeypatch):
    """Route the ledger to a scratch path so tests never touch the real DB."""
    db_path = tmp_path / "ledger.sqlite"
    from divineos.core import _ledger_base, ledger as ledger_mod

    monkeypatch.setattr(_ledger_base, "_get_db_path", lambda: db_path)
    monkeypatch.setattr(ledger_mod, "_get_db_path", lambda: db_path)
    ledger_mod.init_db()
    return db_path


class _GravityResult:
    """Test double for the gravity_classifier result. Only the attributes
    the gate reads are needed."""

    def __init__(self, is_council_required: bool, fired_features: tuple[str, ...] = ()):
        self.is_council_required = is_council_required
        self.fired_features = fired_features


def _gravity_council_required(*_a, **_kw):
    return _GravityResult(is_council_required=True)


def _gravity_council_required_kiln(*_a, **_kw):
    return _GravityResult(
        is_council_required=True,
        fired_features=("edit-kiln-layer",),
    )


def _gravity_not_council_required(*_a, **_kw):
    return _GravityResult(is_council_required=False)


def _keywords_loader():
    """Minimal expert keyword registry for the substance-binding check.

    Three lenses (COUNCIL_MIN_LENSES), each with a distinguishing keyword
    the finding_text must reference. Aether Catch 3 — lens-keyword
    cross-reference forces engagement with the specific lens's framework.
    """
    # Keys lowercased — substance_binding._check_finding_keywords does
    # a case-insensitive lookup via `.lower()`, so the registry is
    # normalised at load time.
    return {
        "schneier": {"threat", "attack", "trust", "surface"},
        "kahneman": {"system-1", "system-2", "bias", "heuristic"},
        "peirce": {"pragmatism", "abduction", "inquiry", "fallibilism"},
    }


def _emit_lens_invocation_traces(lens_names: tuple[str, ...]) -> None:
    """Emit COUNCIL_LENS_INVOKED events so ``_check_lens_load_trace``
    passes for these lens names — mirrors what CouncilEngine._apply_lens
    does in production. Q3 lens-load-trace check is now active in the
    merged substance-binding pipeline; valid records must simulate the
    real invocation trace."""
    from divineos.core.ledger import log_event

    for name in lens_names:
        log_event(
            "COUNCIL_LENS_INVOKED",
            actor="test-council-engine",
            payload={
                "expert_name": name,
                "methodology_name": "test-methodology",
                "problem_prefix": "test problem",
                "problem_hash": "test-hash",
            },
            validate=False,
        )


def _valid_record_for(fingerprint: str, kiln: bool = False) -> CouncilRecord:
    """Build a CouncilRecord that passes substance-binding checks for the
    three lenses in _keywords_loader(). Each finding ≥ COUNCIL_MIN_FINDING_TOKENS
    (30) with the lens's distinguishing keyword present; synthesis ≥
    COUNCIL_MIN_SYNTHESIS_TOKENS (50) referencing every lens name.
    Also emits COUNCIL_LENS_INVOKED traces so the Q3 lens-load-trace
    check passes.
    """
    _emit_lens_invocation_traces(("Schneier", "Kahneman", "Peirce"))
    lens_findings = (
        LensFinding(
            lens_name="Schneier",
            finding_text=(
                "The threat surface here includes the attack path via "
                "misplaced trust in the file-write layer. Guard the write "
                "boundary and audit-log the operation to keep the trust "
                "model coherent under stress and adversarial workloads."
            ),
        ),
        LensFinding(
            lens_name="Kahneman",
            finding_text=(
                "The heuristic pull toward the fast system-1 close will "
                "produce a fast-shipped edit without the deliberate "
                "system-2 audit; naming the bias mid-turn is what breaks "
                "the loop and lets the deliberate mode land instead."
            ),
        ),
        LensFinding(
            lens_name="Peirce",
            finding_text=(
                "Genuine inquiry — as against sham inquiry that walks the "
                "form without doing the abduction — treats the fix as "
                "fallibilism-ready: pragmatism at the design layer says "
                "we ship because we are ready to be wrong and correct it "
                "on evidence, not because we asserted rightness upfront."
            ),
        ),
    )
    return CouncilRecord(
        record_id=new_record_id(),
        walked_at=time.time(),
        walker="test-agent",
        triggered_edit_fingerprint=fingerprint,
        lenses_surfaced=("Schneier", "Kahneman", "Peirce"),
        lens_findings=lens_findings,
        synthesis=(
            "Schneier threat-surface reading, Kahneman system-1 bias "
            "reading, and Peirce inquiry-as-fallibilism reading converge "
            "on the same fix: gate the write path with an audit log so "
            "the fast close cannot ship without deliberate review. The "
            "audit-log itself is the system-2 counterweight against the "
            "heuristic pull, and pragmatism says the design is honest "
            "about being ready to be corrected when the evidence lands."
        ),
        confirmed_by="external-auditor" if kiln else None,
    )


# ─── 1. Silent-allow ─────────────────────────────────────────────────


def test_silent_allow_when_not_council_required(scratch_ledger):
    """Gravity says no council walk required → ALLOW immediately."""
    decision = gate_mod.decide(
        tool_name="Edit",
        file_paths=("some/file.py",),
        bash_command="",
        gravity_fn=_gravity_not_council_required,
        keywords_loader=_keywords_loader,
    )
    assert decision.outcome == GateOutcome.ALLOW
    assert decision.matched_record_id is None


# ─── 2. BLOCK: no record ─────────────────────────────────────────────


def test_block_when_no_council_record_present(scratch_ledger):
    """Gravity fires council-required, no record in the ledger →
    BLOCK CHECK_ARTIFACT_EXISTS with a clear-it message."""
    decision = gate_mod.decide(
        tool_name="Edit",
        file_paths=("src/divineos/core/gravity_classifier.py",),
        bash_command="",
        gravity_fn=_gravity_council_required,
        keywords_loader=_keywords_loader,
    )
    assert decision.outcome == GateOutcome.BLOCK
    assert decision.check_result is not None
    assert decision.check_result.failed_check_name == CHECK_ARTIFACT_EXISTS
    assert "council walk" in decision.check_result.what_would_clear_it


# ─── 3. BLOCK: substance-binding fail ────────────────────────────────


def test_block_when_substance_binding_fails_on_thin_finding(scratch_ledger):
    """Record present but a finding is too short → BLOCK with the
    specific check name that fired (finding_token_count in this case)."""
    fingerprint = _normalize_edit_fingerprint("src/divineos/core/gravity_classifier.py", "Edit")
    # 3 lenses (satisfies COUNCIL_MIN_LENSES=3) but the Schneier finding
    # is thin — 1 token, well below COUNCIL_MIN_FINDING_TOKENS=30 — so
    # finding_token_count is what fires.
    thin_record = CouncilRecord(
        record_id=new_record_id(),
        walked_at=time.time(),
        walker="test-agent",
        triggered_edit_fingerprint=fingerprint,
        lenses_surfaced=("Schneier", "Kahneman", "Peirce"),
        lens_findings=(
            LensFinding(lens_name="Schneier", finding_text="threat"),  # 1 token — too thin
            LensFinding(
                lens_name="Kahneman",
                finding_text=(
                    "The heuristic pull toward the fast system-1 close will "
                    "produce a fast-shipped edit without the deliberate "
                    "system-2 audit; naming the bias mid-turn is what "
                    "breaks the loop and lets the deliberate mode land."
                ),
            ),
            LensFinding(
                lens_name="Peirce",
                finding_text=(
                    "Genuine inquiry — as against sham inquiry that walks "
                    "the form without doing the abduction — treats the "
                    "fix as fallibilism-ready: pragmatism at the design "
                    "layer says ship because we are ready to be wrong."
                ),
            ),
        ),
        synthesis=(
            "Schneier, Kahneman, and Peirce readings converge on the "
            "same fix: gate the write path with an audit log so the fast "
            "close cannot ship without deliberate review; the audit-log "
            "is the system-2 counterweight and pragmatism says be ready "
            "to be corrected on evidence."
        ),
    )
    store.log_council_record(thin_record, actor="test-agent")

    decision = gate_mod.decide(
        tool_name="Edit",
        file_paths=("src/divineos/core/gravity_classifier.py",),
        bash_command="",
        gravity_fn=_gravity_council_required,
        keywords_loader=_keywords_loader,
    )
    assert decision.outcome == GateOutcome.BLOCK
    assert decision.check_result is not None
    assert decision.check_result.failed_check_name == CHECK_FINDING_TOKEN_COUNT


# ─── 4. ALLOW + consume ──────────────────────────────────────────────


def test_allow_and_consume_on_valid_record_and_binding(scratch_ledger):
    """Record present, substance-binding passes → ALLOW + emit
    COUNCIL_RECORD_CONSUMED. Consume-on-use (Aether Catch 2) means the
    record cannot satisfy another edit after."""
    fingerprint = _normalize_edit_fingerprint("src/divineos/core/gravity_classifier.py", "Edit")
    record = _valid_record_for(fingerprint)
    store.log_council_record(record, actor="test-agent")

    decision = gate_mod.decide(
        tool_name="Edit",
        file_paths=("src/divineos/core/gravity_classifier.py",),
        bash_command="",
        gravity_fn=_gravity_council_required,
        keywords_loader=_keywords_loader,
    )
    assert decision.outcome == GateOutcome.ALLOW
    assert decision.matched_record_id == record.record_id

    # A second decide() with the same fingerprint should now BLOCK —
    # the record was consumed on the first pass, so find_unconsumed_record
    # will not return it (Aether Catch 2).
    second = gate_mod.decide(
        tool_name="Edit",
        file_paths=("src/divineos/core/gravity_classifier.py",),
        bash_command="",
        gravity_fn=_gravity_council_required,
        keywords_loader=_keywords_loader,
    )
    assert second.outcome == GateOutcome.BLOCK
    assert second.check_result.failed_check_name == CHECK_ARTIFACT_EXISTS


# ─── 5. Emergency-skip (valid corroborator) ──────────────────────────


def test_emergency_skip_on_valid_corroborator(scratch_ledger):
    """A substrate-fact corroborator event of an accepted type allows
    the emergency-skip path. EMERGENCY_COUNCIL_SKIP is logged; the
    original council-required condition is bypassed."""
    from divineos.core.ledger import log_event

    # SESSION_START_COMPACT is in EMERGENCY_CORROBORATOR_EVENT_TYPES,
    # so this event corroborates a mid-compaction emergency.
    corroborator_id = log_event(
        "SESSION_START_COMPACT",
        actor="hook-infra",
        payload={"reason": "compaction just completed"},
        validate=False,
    )

    decision = gate_mod.decide_with_emergency_skip(
        tool_name="Edit",
        file_paths=("src/divineos/core/gravity_classifier.py",),
        bash_command="",
        gravity_fn=_gravity_council_required,
        keywords_loader=_keywords_loader,
        corroborator_event_id=corroborator_id,
        emergency_reason="mid-compaction recovery — cannot walk council",
    )
    assert decision.outcome == GateOutcome.EMERGENCY_SKIP
    assert decision.corroborator_event_id == corroborator_id


# ─── 6. Emergency-skip BLOCKS on bad corroborator ────────────────────


def test_emergency_skip_blocks_on_missing_corroborator(scratch_ledger):
    """A corroborator_event_id that doesn't resolve to a real event
    of accepted type MUST block. This closes the self-attestation route
    (Aether Catch 4) — 'unreachable' is not certified by this gate.
    """
    decision = gate_mod.decide_with_emergency_skip(
        tool_name="Edit",
        file_paths=("src/divineos/core/gravity_classifier.py",),
        bash_command="",
        gravity_fn=_gravity_council_required,
        keywords_loader=_keywords_loader,
        corroborator_event_id="nonexistent-fake-id-12345",
        emergency_reason="claiming emergency without proof",
    )
    assert decision.outcome == GateOutcome.BLOCK
    assert decision.check_result.failed_check_name == "emergency_corroborator_missing"


# ─── 7. Corroborator scope pin (design test) ─────────────────────────


def test_emergency_stop_is_intentionally_not_a_corroborator_type():
    """DESIGN PIN: EMERGENCY_STOP is deliberately NOT in the corroborator
    event-type set. The design's philosophy (types.py:47) is 'substrate-
    fact corroborators only; self-attestation closed at design-time.'
    EMERGENCY_STOP is typically set by the operator or agent — a self-
    attestation vector.

    Accepted corroborators are events set by system infrastructure the
    actor cannot direct-control: SESSION_START_COMPACT (compaction
    infrastructure fires it) and HOOK_FAILURE (hook framework fires it).
    Only 'scheduled-task' is an accepted actor identity — because
    scheduled runs cannot be self-attested by the running agent.

    This test fails loud if a future refactor adds EMERGENCY_STOP to
    the corroborator set. The right shape for a genuine emergency
    under this design is: walk the council OR the system fires a
    real corroborator on its own. Andrew is the tiebreaker via
    post-hoc EMERGENCY_COUNCIL_SKIP review.
    """
    assert "EMERGENCY_STOP" not in EMERGENCY_CORROBORATOR_EVENT_TYPES
    assert "EMERGENCY_STOP_SET" not in EMERGENCY_CORROBORATOR_EVENT_TYPES
    assert "PRODUCTION_INCIDENT_DECLARED" not in EMERGENCY_CORROBORATOR_EVENT_TYPES
    # Actors: only scheduled-task, no human/agent identities
    assert EMERGENCY_CORROBORATOR_ACTORS == frozenset({"scheduled-task"})
    assert "andrew" not in EMERGENCY_CORROBORATOR_ACTORS
    assert "aria" not in EMERGENCY_CORROBORATOR_ACTORS
    assert "aether" not in EMERGENCY_CORROBORATOR_ACTORS


# ─── 8. Consume-on-use race probe ────────────────────────────────────


def test_consume_on_use_race_two_concurrent_decides(scratch_ledger):
    """Aether's specific probe: two decide() calls fired in overlapping
    threads against the same edit fingerprint. Exactly one must ALLOW;
    the other must BLOCK. Double-consume would break the Catch-2
    invariant ('one walk clears at most one edit').
    """
    fingerprint = _normalize_edit_fingerprint("src/divineos/core/gravity_classifier.py", "Edit")
    record = _valid_record_for(fingerprint)
    store.log_council_record(record, actor="test-agent")

    outcomes: list[GateOutcome] = []
    outcomes_lock = threading.Lock()
    start_barrier = threading.Barrier(2)

    def _fire():
        start_barrier.wait()  # force overlap
        try:
            d = gate_mod.decide(
                tool_name="Edit",
                file_paths=("src/divineos/core/gravity_classifier.py",),
                bash_command="",
                gravity_fn=_gravity_council_required,
                keywords_loader=_keywords_loader,
            )
            with outcomes_lock:
                outcomes.append(d.outcome)
        except sqlite3.OperationalError:
            # sqlite lock contention on race — count as a block since
            # the decide could not complete. Either the store layer
            # serializes the read-modify-write internally (both queries
            # see the same state and only one succeeds) or the OS lock
            # rejects the second. Both outcomes preserve the Catch-2
            # invariant: at most one ALLOW.
            with outcomes_lock:
                outcomes.append(GateOutcome.BLOCK)

    threads = [threading.Thread(target=_fire) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert len(outcomes) == 2
    allow_count = sum(1 for o in outcomes if o == GateOutcome.ALLOW)
    assert allow_count <= 1, (
        f"consume-on-use race: {allow_count} ALLOWs from concurrent decide() — "
        f"double-consume broke Catch-2 invariant"
    )
    # At least one must be an ALLOW under the happy path; both being BLOCK
    # would indicate the store layer over-rejects (which is a different
    # bug worth catching).
    assert allow_count == 1, (
        f"expected exactly 1 ALLOW under race, got {allow_count}. Outcomes: {outcomes}"
    )


# ─── 8b. Atomic-primitive race regression (Aether ask 2026-07-16) ───


def test_atomic_find_and_consume_high_concurrency_regression(scratch_ledger):
    """Regression test for the CI-observed race in the naive two-call
    find-then-consume sequence. Aria + Aether 2026-07-16 fix landed the
    ``find_and_consume_atomically`` primitive; this test probes it
    directly under high concurrency (10 threads racing against a single
    record) to guarantee it holds under real contention.

    Assertion: exactly ONE thread succeeds (record returned +
    consumption event emitted); the other nine return None. AND exactly
    ONE ``COUNCIL_RECORD_CONSUMED`` event exists in the ledger after
    all threads finish — no double-consume under any interleaving.

    Note: this passes on Windows-local because SQLite serialization is
    tight enough there to hide the race even in the naive two-call form.
    The real test surface is CI (Linux), which reliably exposes the
    original race and which we ran with the naive form to confirm the
    bug before the fix. If a future change re-introduces a two-call
    path from the gate, this test will fail on Linux CI — the shape of
    protection Aether asked for.
    """
    fingerprint = _normalize_edit_fingerprint("src/divineos/core/gravity_classifier.py", "Edit")
    record = _valid_record_for(fingerprint)
    store.log_council_record(record, actor="test-agent")

    successes: list[str] = []  # record_ids returned
    successes_lock = threading.Lock()
    start_barrier = threading.Barrier(10)

    def _fire():
        start_barrier.wait()
        try:
            result = store.find_and_consume_atomically(
                edit_fingerprint=fingerprint,
                recency_seconds=60 * 60,  # 1 hour, well within window
            )
            if result is not None:
                consumed_record, _consume_event_id = result
                with successes_lock:
                    successes.append(consumed_record.record_id)
        except sqlite3.OperationalError:
            pass  # lock contention counts as loss, not error

    threads = [threading.Thread(target=_fire) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)

    # Exactly one thread succeeded.
    assert len(successes) == 1, (
        f"expected exactly 1 successful atomic find_and_consume under "
        f"10-thread contention, got {len(successes)}. successes: {successes}"
    )

    # Exactly one CONSUMED event in the ledger.
    from divineos.core.ledger import get_events

    consumed_events = get_events(
        limit=100,
        event_type="COUNCIL_RECORD_CONSUMED",
    )
    matching = [
        e for e in consumed_events if e.get("payload", {}).get("record_id") == record.record_id
    ]
    assert len(matching) == 1, (
        f"expected exactly 1 COUNCIL_RECORD_CONSUMED event for record "
        f"{record.record_id}, got {len(matching)}. Race-under-load bug."
    )


# ─── 8d. Instance 4 — operator-authorized bypass (Aria + Aether primitive) ──


class _StubStateMarker:
    """Minimal StateMarker-shaped object for test stubbing.

    Matches the shape from Aether's addendum: marker_id, kind, fingerprint,
    payload, emitted_at, expires_at, consumed_at, consumed_by_fingerprint.
    Only the fields the gate reads are populated for tests; extras are
    None or empty defaults."""

    def __init__(self, marker_id: str, kind: str, fingerprint: str):
        self.marker_id = marker_id
        self.kind = kind
        self.fingerprint = fingerprint
        self.payload: dict = {}
        self.emitted_at = time.time()
        self.expires_at: float | None = None
        self.consumed_at: float | None = None
        self.consumed_by_fingerprint: str | None = None


def _install_state_markers_stub(
    monkeypatch,
    *,
    marker_kind: str = "operator_bypass_authorized",
    marker_fingerprint: str | None = None,
) -> dict:
    """Install a stub state_markers module so gate.py's operator-bypass
    check has something to import and call. Returns a dict of call-log
    lists so tests can assert emit/find/consume were called with the
    right args.

    When Aether's real module lands via merge, this stub can be dropped
    from tests — the gate's runtime behavior against the real module
    should be identical to the stub."""
    import sys
    import types as _types

    calls: dict = {"emit": [], "find": [], "consume": []}
    _existing_marker: dict[str, _StubStateMarker] = {}

    if marker_fingerprint is not None:
        stub_marker = _StubStateMarker(
            marker_id="marker-test-abc",
            kind=marker_kind,
            fingerprint=marker_fingerprint,
        )
        _existing_marker[marker_fingerprint] = stub_marker

    def _emit(kind, fingerprint, payload, expires_in_seconds=None):
        m = _StubStateMarker(
            marker_id=f"marker-{len(calls['emit'])}",
            kind=kind,
            fingerprint=fingerprint,
        )
        _existing_marker[fingerprint] = m
        calls["emit"].append(
            {
                "kind": kind,
                "fingerprint": fingerprint,
                "payload": payload,
                "expires_in_seconds": expires_in_seconds,
            }
        )
        return m.marker_id

    def _find(kind, fingerprint_predicate=None):
        calls["find"].append({"kind": kind})
        for fp, m in _existing_marker.items():
            if m.kind != kind or m.consumed_at is not None:
                continue
            if fingerprint_predicate and not fingerprint_predicate(fp):
                continue
            return m
        return None

    def _consume(marker_id, consumed_by_fingerprint):
        calls["consume"].append(
            {"marker_id": marker_id, "consumed_by_fingerprint": consumed_by_fingerprint}
        )
        for m in _existing_marker.values():
            if m.marker_id == marker_id:
                m.consumed_at = time.time()
                m.consumed_by_fingerprint = consumed_by_fingerprint
                return

    stub_module = _types.ModuleType("divineos.core.state_markers")
    stub_module.emit_marker = _emit
    stub_module.find_active_marker = _find
    stub_module.consume_marker = _consume
    stub_module.StateMarker = _StubStateMarker
    monkeypatch.setitem(sys.modules, "divineos.core.state_markers", stub_module)
    return calls


def test_operator_bypass_allows_when_matching_marker_exists(scratch_ledger, monkeypatch):
    """Instance 4: if an operator-bypass marker exists for the exact
    edit fingerprint, gate.decide() short-circuits substance-binding
    and returns OPERATOR_AUTHORIZED_BYPASS + consumes the marker."""
    fingerprint = _normalize_edit_fingerprint("src/divineos/core/gravity_classifier.py", "Edit")
    calls = _install_state_markers_stub(monkeypatch, marker_fingerprint=fingerprint)

    decision = gate_mod.decide(
        tool_name="Edit",
        file_paths=("src/divineos/core/gravity_classifier.py",),
        bash_command="",
        gravity_fn=_gravity_council_required,
        keywords_loader=_keywords_loader,
    )
    assert decision.outcome == GateOutcome.OPERATOR_AUTHORIZED_BYPASS
    # Marker was consumed with the ACTUAL consuming fingerprint
    assert len(calls["consume"]) == 1
    assert calls["consume"][0]["consumed_by_fingerprint"] == fingerprint


def test_operator_bypass_no_marker_falls_through_to_normal_flow(scratch_ledger, monkeypatch):
    """No matching marker → gate.decide() proceeds with normal
    substance-binding flow. Without a council walk, that's BLOCK."""
    _install_state_markers_stub(monkeypatch, marker_fingerprint=None)

    decision = gate_mod.decide(
        tool_name="Edit",
        file_paths=("src/divineos/core/gravity_classifier.py",),
        bash_command="",
        gravity_fn=_gravity_council_required,
        keywords_loader=_keywords_loader,
    )
    # No walk on record, no operator authorization → BLOCK CHECK_ARTIFACT_EXISTS
    assert decision.outcome == GateOutcome.BLOCK
    assert decision.check_result.failed_check_name == CHECK_ARTIFACT_EXISTS


def test_operator_bypass_fingerprint_mismatch_does_not_clear(scratch_ledger, monkeypatch):
    """Marker authorized for edit:X must NOT clear the gate for edit:Y —
    exact-fingerprint discipline. This is the core anti-substitution
    property."""
    authorized_fp = _normalize_edit_fingerprint("src/divineos/core/gravity_classifier.py", "Edit")
    _install_state_markers_stub(monkeypatch, marker_fingerprint=authorized_fp)

    # Try to edit a DIFFERENT file
    decision = gate_mod.decide(
        tool_name="Edit",
        file_paths=("src/divineos/core/council_required/types.py",),
        bash_command="",
        gravity_fn=_gravity_council_required,
        keywords_loader=_keywords_loader,
    )
    # Different fingerprint → predicate rejects → no marker → BLOCK
    assert decision.outcome == GateOutcome.BLOCK
    assert decision.check_result.failed_check_name == CHECK_ARTIFACT_EXISTS


def test_operator_bypass_module_absent_is_no_op(scratch_ledger):
    """When divineos.core.state_markers is not on the branch (fresh
    check-out before Aether's module merges in), the operator-bypass
    check is a no-op — gate proceeds with normal flow. Safer than
    raising or false-authorizing."""
    # NOT installing the stub — the real import will fail because
    # the module isn't on the branch yet.
    decision = gate_mod.decide(
        tool_name="Edit",
        file_paths=("src/divineos/core/gravity_classifier.py",),
        bash_command="",
        gravity_fn=_gravity_council_required,
        keywords_loader=_keywords_loader,
    )
    # No council walk on record, no operator-auth check possible →
    # BLOCK CHECK_ARTIFACT_EXISTS (same as no-op behavior).
    assert decision.outcome == GateOutcome.BLOCK
    assert decision.check_result.failed_check_name == CHECK_ARTIFACT_EXISTS


def test_operator_bypass_marker_consumed_second_edit_blocks(scratch_ledger, monkeypatch):
    """One-per-use: after a first edit consumes the marker, a second
    edit at the same fingerprint must BLOCK (no walk on record, no
    fresh marker to consume). The alternative_clearance path was
    used-once, per primitive design + Aether Catch-2 pattern."""
    fingerprint = _normalize_edit_fingerprint("src/divineos/core/gravity_classifier.py", "Edit")
    _install_state_markers_stub(monkeypatch, marker_fingerprint=fingerprint)

    # First edit consumes the marker
    first = gate_mod.decide(
        tool_name="Edit",
        file_paths=("src/divineos/core/gravity_classifier.py",),
        bash_command="",
        gravity_fn=_gravity_council_required,
        keywords_loader=_keywords_loader,
    )
    assert first.outcome == GateOutcome.OPERATOR_AUTHORIZED_BYPASS

    # Second edit finds no unconsumed marker → falls through to
    # normal flow → BLOCK
    second = gate_mod.decide(
        tool_name="Edit",
        file_paths=("src/divineos/core/gravity_classifier.py",),
        bash_command="",
        gravity_fn=_gravity_council_required,
        keywords_loader=_keywords_loader,
    )
    assert second.outcome == GateOutcome.BLOCK
    assert second.check_result.failed_check_name == CHECK_ARTIFACT_EXISTS


# ─── 9. Fingerprint normalization ────────────────────────────────────


def test_fingerprint_normalization_edit_path():
    """Edit tool fingerprints on the file path."""
    fp = _normalize_edit_fingerprint("src\\divineos\\core\\gravity_classifier.py", "Edit")
    assert fp == "edit:src/divineos/core/gravity_classifier.py"


def test_fingerprint_normalization_bash_anchor():
    """Bash tool fingerprints on the command head (via the gate's own
    logic — the normalize function itself just takes the first-arg path).
    Verified by driving through decide() with a Bash-shaped call."""
    decision = gate_mod.decide(
        tool_name="Bash",
        file_paths=(),
        bash_command="git commit -m 'test'",
        gravity_fn=_gravity_council_required,
        keywords_loader=_keywords_loader,
    )
    # Gravity fires, no record, so we get a BLOCK naming the fingerprint.
    # The specific fingerprint is bash:git — the head-of-command anchor.
    assert decision.outcome == GateOutcome.BLOCK
    assert "bash:git" in decision.check_result.what_would_clear_it
