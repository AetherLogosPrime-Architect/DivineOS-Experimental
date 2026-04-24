"""Tests for Item 6 — fire-ID linkage.

Covers:
    - fire_id generation (uniformity, non-predictability)
    - COMPASS_RUDDER_FIRED and COMPASS_RUDDER_ALLOW event payloads
    - Validator rejects fabricated / stale / consumed / wrong-spectrum
    - fire-ID rejections log to failure_diagnostics stage="fire_id"
    - Concurrency: two threads consuming same fire_id → exactly one
    - Pruning: ALLOW pruned; FIRED retained
    - Integration: full flow block → observe → unblock
    - Back-compat: voluntary observations without --fire-id still work
    - Regression: Item 4 SQL filter returns acks when fire_id column
      populated
"""

from __future__ import annotations

import os
import threading
import time

import pytest

from divineos.core.compass_rudder import (
    RUDDER_ACK_TAG,
    _find_justifications,
    _generate_fire_id,
    check_tool_use,
)
from divineos.core.knowledge import init_knowledge_table
from divineos.core.ledger import get_events, init_db
from divineos.core.moral_compass import (
    get_observations,
    init_compass,
    log_observation,
)


@pytest.fixture(autouse=True)
def _fresh_db(tmp_path, monkeypatch):
    """Isolated DB + failure-diag dir per test."""
    os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
    monkeypatch.setattr("divineos.core.failure_diagnostics._BASE_DIR", tmp_path / "failures")
    # Disable Item 7 substance checks for this suite — we're testing
    # fire-ID mechanics, not substance-check mechanics. Tests that
    # care about substance checks are in test_substance_checks.py.
    for flag in ("LENGTH", "ENTROPY", "SIMILARITY"):
        monkeypatch.setenv(f"DIVINEOS_DETECTOR_SUBSTANCE_{flag}", "off")
    init_db()
    init_knowledge_table()
    init_compass()
    try:
        yield
    finally:
        os.environ.pop("DIVINEOS_DB", None)


def _seed_drift(spectrum: str, magnitude: float = 0.8) -> None:
    """Push a spectrum into toward_excess drift above threshold."""
    for _ in range(5):
        log_observation(spectrum=spectrum, position=0.0, source="MEASURED", evidence="base")
    for _ in range(5):
        log_observation(spectrum=spectrum, position=magnitude, source="MEASURED", evidence="push")


def _trigger_fire(spectrum: str = "initiative") -> str:
    """Force a rudder block; return the issued fire_id from the event."""
    _seed_drift(spectrum)
    v = check_tool_use(tool_name="Task")
    assert v.blocked, v.reason
    fires = get_events(event_type="COMPASS_RUDDER_FIRED", limit=5)
    assert fires, "expected a COMPASS_RUDDER_FIRED event"
    return fires[-1]["payload"]["fire_id"]


# -- fire_id generation --------------------------------------------


class TestFireIdGeneration:
    def test_length_is_16_hex(self):
        fid = _generate_fire_id()
        assert len(fid) == 16
        int(fid, 16)  # parses as hex

    def test_non_predictable(self):
        ids = {_generate_fire_id() for _ in range(1000)}
        assert len(ids) == 1000  # no collisions in 1000 samples


# -- Event payloads ------------------------------------------------


class TestFiredPayload:
    def test_fired_event_payload_shape(self):
        fire_id = _trigger_fire("initiative")
        fires = get_events(event_type="COMPASS_RUDDER_FIRED", limit=5)
        assert len(fires) == 1
        p = fires[0]["payload"]
        assert p["fire_id"] == fire_id
        assert p["spectrum"] == "initiative"
        assert p["tool_name"] == "Task"
        assert p["window_seconds"] == 300
        assert p["threshold"] == 0.15
        assert "all_drifting" in p
        assert "drift_values" in p
        # v2.1: no payload-level timestamp (ledger auto-adds)
        assert "timestamp" not in p


class TestAllowPayload:
    def test_allow_emitted_on_no_drift(self):
        v = check_tool_use(tool_name="Task")
        assert v.decision == "allow"
        allows = get_events(event_type="COMPASS_RUDDER_ALLOW", limit=5)
        assert len(allows) == 1
        p = allows[0]["payload"]
        assert p["tool_name"] == "Task"
        # v2.1: redundant fields dropped
        assert "fire_id" not in p
        assert "spectrum" not in p
        assert "drifting_spectrums" in p
        assert "recent_justifications" in p

    def test_allow_not_emitted_for_non_gated_tool(self):
        v = check_tool_use(tool_name="Edit")
        assert v.decision == "allow"
        allows = get_events(event_type="COMPASS_RUDDER_ALLOW", limit=5)
        assert len(allows) == 0

    def test_allow_emitted_on_justified_drift(self):
        fire_id = _trigger_fire("initiative")
        log_observation(
            spectrum="initiative",
            position=0.1,
            evidence="scope bounded to 3 agents; initiative drift acknowledged",
            source="rudder_ack",
            tags=[RUDDER_ACK_TAG],
            fire_id=fire_id,
        )
        v = check_tool_use(tool_name="Task")
        assert v.decision == "allow"
        allows = get_events(event_type="COMPASS_RUDDER_ALLOW", limit=5)
        assert len(allows) == 1


# -- Validator: 5 scenarios from pre-reg ---------------------------


class TestFireIdValidation:
    def test_a_fabricated_fire_id_rejected(self):
        _seed_drift("initiative")
        with pytest.raises(ValueError, match="nonexistent or stale"):
            log_observation(
                spectrum="initiative",
                position=0.1,
                evidence="substantive ack content for fabricated fire_id test",
                source="rudder_ack",
                tags=[RUDDER_ACK_TAG],
                fire_id="f" * 16,
            )

    def test_c_real_fire_id_accepted_once_then_rejected(self):
        fire_id = _trigger_fire("initiative")
        # First use succeeds
        log_observation(
            spectrum="initiative",
            position=0.1,
            evidence="first legitimate ack with real fire_id binding",
            source="rudder_ack",
            tags=[RUDDER_ACK_TAG],
            fire_id=fire_id,
        )
        # Second use rejected
        with pytest.raises(ValueError, match="already consumed"):
            log_observation(
                spectrum="initiative",
                position=0.1,
                evidence="second ack attempting to reuse same fire_id",
                source="rudder_ack",
                tags=[RUDDER_ACK_TAG],
                fire_id=fire_id,
            )

    def test_d_wrong_spectrum_rejected(self):
        fire_id = _trigger_fire("initiative")
        with pytest.raises(ValueError, match="nonexistent or stale"):
            log_observation(
                spectrum="humility",  # different spectrum than fire
                position=0.0,
                evidence="ack on a spectrum the fire was not for",
                source="rudder_ack",
                tags=[RUDDER_ACK_TAG],
                fire_id=fire_id,
            )

    def test_e_voluntary_observation_no_fire_id_backcompat(self):
        # Non-drifting spectrum, no tag, no fire_id
        obs_id = log_observation(
            spectrum="humility",
            position=0.0,
            evidence="voluntary spot-check observation without fire_id",
            source="self_report",
        )
        assert obs_id

    def test_stale_fire_rejected(self):
        """Fire event older than the window is not acceptable."""
        # Emit a fire event with a payload-readable fire_id
        from divineos.core.ledger import log_event

        fire_id = "a" * 16
        # We can't easily backdate via public API; simulate by having
        # no fire event and trying to use a fabricated id — same class.
        # A real fire older than the window is exercised by the
        # validator's cutoff check (sim via future-now):
        log_event(
            event_type="COMPASS_RUDDER_FIRED",
            actor="rudder",
            payload={
                "fire_id": fire_id,
                "spectrum": "initiative",
                "all_drifting": ["initiative"],
                "tool_name": "Task",
                "window_seconds": 300,
                "threshold": 0.15,
                "drift_values": {},
            },
            validate=False,
        )
        # Sleep past the window — we use a low-level trick: the validator
        # uses time.time(); we can't easily jump time. Instead: set an
        # explicit `now` via monkeypatch on _validate_fire_id's
        # `now=None` default. Simpler: call the private validator
        # directly with a future `now`.
        from divineos.core.moral_compass import _validate_fire_id

        future = time.time() + 600  # 10 min later, past the 5-min window
        with pytest.raises(ValueError, match="nonexistent or stale"):
            _validate_fire_id(fire_id=fire_id, spectrum="initiative", now=future)


# -- Failure-diagnostics logging ------------------------------------


class TestFireIdRejectionLogging:
    def test_fabricated_fire_logged_to_failure_diagnostics(self, tmp_path, monkeypatch):
        monkeypatch.setattr("divineos.core.failure_diagnostics._BASE_DIR", tmp_path / "failures")
        _seed_drift("initiative")
        with pytest.raises(ValueError):
            log_observation(
                spectrum="initiative",
                position=0.1,
                evidence="substantive ack with fabricated fire_id",
                source="rudder_ack",
                tags=[RUDDER_ACK_TAG],
                fire_id="d" * 16,
            )
        from divineos.core.failure_diagnostics import recent_failures

        entries = recent_failures("rudder-ack", window=10)
        assert any(e.get("stage") == "fire_id" for e in entries)

    def test_consumed_fire_logged_to_failure_diagnostics(self, tmp_path, monkeypatch):
        monkeypatch.setattr("divineos.core.failure_diagnostics._BASE_DIR", tmp_path / "failures")
        fire_id = _trigger_fire("initiative")
        log_observation(
            spectrum="initiative",
            position=0.1,
            evidence="first legitimate ack consuming the fire",
            source="rudder_ack",
            tags=[RUDDER_ACK_TAG],
            fire_id=fire_id,
        )
        with pytest.raises(ValueError, match="already consumed"):
            log_observation(
                spectrum="initiative",
                position=0.1,
                evidence="second ack attempting to reuse the same consumed fire",
                source="rudder_ack",
                tags=[RUDDER_ACK_TAG],
                fire_id=fire_id,
            )
        from divineos.core.failure_diagnostics import recent_failures

        entries = recent_failures("rudder-ack", window=10)
        assert any(
            e.get("stage") == "fire_id" and "consumed" in e.get("reason", "") for e in entries
        )


# -- Concurrency: race-safe one-shot --------------------------------


class TestConsumptionRace:
    def test_concurrent_consume_exactly_one_succeeds(self, tmp_path, monkeypatch):
        """Two threads race to consume the same fire_id; PRIMARY KEY
        enforces one-shot structurally via IntegrityError."""
        fire_id = _trigger_fire("initiative")
        results: list[str | Exception] = []
        barrier = threading.Barrier(2)

        def attempt(evidence: str) -> None:
            try:
                barrier.wait(timeout=5)
                obs_id = log_observation(
                    spectrum="initiative",
                    position=0.1,
                    evidence=evidence,
                    source="rudder_ack",
                    tags=[RUDDER_ACK_TAG],
                    fire_id=fire_id,
                )
                results.append(obs_id)
            except Exception as e:  # noqa: BLE001
                results.append(e)

        t1 = threading.Thread(target=attempt, args=("first concurrent ack attempting to consume",))
        t2 = threading.Thread(target=attempt, args=("second concurrent ack attempting to consume",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        successes = [r for r in results if isinstance(r, str)]
        failures = [r for r in results if isinstance(r, Exception)]
        assert len(successes) == 1, f"expected exactly 1 success, got {len(successes)}"
        assert len(failures) == 1, "expected exactly 1 IntegrityError translation"
        # Tightened per fresh-Claude round-3 review: the concurrent
        # rejection path must be the PK IntegrityError → "already
        # consumed" translation. "nonexistent or stale" would indicate
        # something other than the PK constraint is doing the rejecting
        # — a bug worth investigating, not a valid outcome.
        assert "already consumed" in str(failures[0]), (
            f"expected PK-constraint rejection, got: {failures[0]}"
        )


# -- Pruning: ALLOW pruned, FIRED retained --------------------------


class TestPruning:
    def test_allow_in_compressible_types(self):
        from divineos.core.ledger_compressor import _COMPRESSIBLE_TYPES

        assert "COMPASS_RUDDER_ALLOW" in _COMPRESSIBLE_TYPES

    def test_fired_not_in_compressible_types(self):
        """FIRED events are forensic — must survive pruning."""
        from divineos.core.ledger_compressor import _COMPRESSIBLE_TYPES

        assert "COMPASS_RUDDER_FIRED" not in _COMPRESSIBLE_TYPES


# -- Integration: full flow ----------------------------------------


class TestFullFlow:
    def test_block_then_observe_then_unblock(self):
        fire_id = _trigger_fire("initiative")
        # First check — blocked (drifting, no ack yet)
        v1 = check_tool_use(tool_name="Task")
        assert v1.blocked

        # Agent files ack using the fire_id from block message
        log_observation(
            spectrum="initiative",
            position=0.1,
            evidence="scope bounded to 3 agents; drift acknowledged post-block",
            source="rudder_ack",
            tags=[RUDDER_ACK_TAG],
            fire_id=fire_id,
        )

        # Second check — allowed (ack present)
        v2 = check_tool_use(tool_name="Task")
        assert v2.decision == "allow"
        assert "initiative" in v2.recent_justifications


# -- Regression: Item 4 SQL filter with fire_id column --------------


class TestItem4Regression:
    def test_get_observations_returns_fire_id_column(self):
        fire_id = _trigger_fire("initiative")
        log_observation(
            spectrum="initiative",
            position=0.1,
            evidence="ack with fire_id for Item 4 regression check",
            source="rudder_ack",
            tags=[RUDDER_ACK_TAG],
            fire_id=fire_id,
        )
        rows = get_observations(spectrum="initiative", tag=RUDDER_ACK_TAG, limit=5)
        assert rows
        assert rows[0]["fire_id"] == fire_id

    def test_find_justifications_still_works_post_item_6(self):
        fire_id = _trigger_fire("initiative")
        log_observation(
            spectrum="initiative",
            position=0.1,
            evidence="substantive ack for _find_justifications regression",
            source="rudder_ack",
            tags=[RUDDER_ACK_TAG],
            fire_id=fire_id,
        )
        justified = _find_justifications(["initiative"])
        assert justified == ["initiative"]
