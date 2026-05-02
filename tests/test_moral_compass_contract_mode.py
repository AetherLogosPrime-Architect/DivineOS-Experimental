"""Tests for Phase 1b contract-mode wiring in moral_compass.log_observation.

Covers the tri-state DIVINEOS_RUDDER_CONTRACT_MODE flag (off / observe /
enforce), CONTRACT_DUAL_RUN_DISCREPANCY emission, and
RUDDER_ACK_RETRACTED emission when wired=retracted.
"""

from __future__ import annotations

import os

import pytest

from divineos.core.compass_rudder import check_tool_use
from divineos.core.knowledge import init_knowledge_table
from divineos.core.ledger import get_events, init_db
from divineos.core.moral_compass import init_compass, log_observation


@pytest.fixture(autouse=True)
def _db(tmp_path):
    os.environ["DIVINEOS_DB"] = str(tmp_path / "contract_mode.db")
    try:
        init_db()
        init_knowledge_table()
        init_compass()
        yield
    finally:
        os.environ.pop("DIVINEOS_DB", None)
        os.environ.pop("DIVINEOS_RUDDER_CONTRACT_MODE", None)


def _seed_drift(spectrum: str = "initiative", magnitude: float = 0.5) -> None:
    """Seed drift toward excess to make the rudder fire."""
    for _ in range(2):
        log_observation(spectrum=spectrum, position=0.0, evidence="baseline neutral")
    for _ in range(2):
        log_observation(
            spectrum=spectrum,
            position=magnitude,
            evidence="drifting toward excess on this spectrum",
        )


def _force_fire(spectrum: str = "initiative") -> str:
    _seed_drift(spectrum)
    v = check_tool_use(tool_name="Task")
    assert v.blocked, "expected drift to fire rudder"
    fires = get_events(event_type="COMPASS_RUDDER_FIRED", limit=10)
    for ev in reversed(fires):
        p = ev.get("payload") or {}
        if p.get("spectrum") == spectrum:
            return p["fire_id"]
    raise RuntimeError("no fire_id for spectrum")


# ---------- mode: off (default, legacy unchanged) ----------


def test_mode_off_is_default_and_runs_legacy_only():
    """With flag unset, contract check does NOT run — legacy passes contract-shaped evidence trivially."""
    os.environ.pop("DIVINEOS_RUDDER_CONTRACT_MODE", None)
    fire_id = _force_fire()
    # Legacy substance check requires length+entropy; contract-shape ack passes both.
    log_observation(
        spectrum="initiative",
        position=0.1,
        evidence=(
            "artifact_reference: PR #195\n"
            "wired: yes\n"
            "this is enough plain English to clear length and entropy floors easily\n"
        ),
        tags=["rudder-ack"],
        fire_id=fire_id,
    )
    # No discrepancy events because contract didn't run.
    assert get_events(event_type="CONTRACT_DUAL_RUN_DISCREPANCY", limit=5) == []


# ---------- mode: observe (contract runs, doesn't block) ----------


def test_observe_mode_emits_discrepancy_when_contract_rejects():
    """Legacy passes substantive prose; contract rejects missing artifact_reference."""
    os.environ["DIVINEOS_RUDDER_CONTRACT_MODE"] = "observe"
    fire_id = _force_fire()
    # Substantive but contract-malformed evidence (no fields).
    log_observation(
        spectrum="initiative",
        position=0.1,
        evidence=(
            "I noticed I was rushing and chose to slow down and verify the "
            "wiring before claiming completion on the next artifact."
        ),
        tags=["rudder-ack"],
        fire_id=fire_id,
    )
    discreps = get_events(event_type="CONTRACT_DUAL_RUN_DISCREPANCY", limit=5)
    assert len(discreps) == 1
    p = discreps[0].get("payload") or {}
    assert p["legacy_ok"] is True
    assert p["contract_ok"] is False
    assert p["contract_stage"] == "artifact"
    # Phase 2 calibration material — fire_id and parsed_wired in payload.
    assert p["fire_id"] == fire_id
    assert "parsed_wired" in p  # None acceptable when contract couldn't parse


def test_observe_mode_does_not_block_on_contract_failure():
    """Contract reject in observe-mode must NOT raise — legacy still gates."""
    os.environ["DIVINEOS_RUDDER_CONTRACT_MODE"] = "observe"
    fire_id = _force_fire()
    obs_id = log_observation(
        spectrum="initiative",
        position=0.1,
        evidence=(
            "long substantive prose with enough characters to clear the "
            "length and entropy floors imposed by the legacy substance check"
        ),
        tags=["rudder-ack"],
        fire_id=fire_id,
    )
    assert obs_id  # commit succeeded despite contract rejection


# ---------- mode: enforce (both must pass) ----------


def test_enforce_mode_blocks_on_contract_failure():
    os.environ["DIVINEOS_RUDDER_CONTRACT_MODE"] = "enforce"
    fire_id = _force_fire()
    with pytest.raises(ValueError, match="contract check"):
        log_observation(
            spectrum="initiative",
            position=0.1,
            evidence=(
                "long substantive prose with enough characters to clear the "
                "legacy length and entropy floors but missing contract fields"
            ),
            tags=["rudder-ack"],
            fire_id=fire_id,
        )


def test_enforce_mode_passes_when_both_check_pass():
    os.environ["DIVINEOS_RUDDER_CONTRACT_MODE"] = "enforce"
    fire_id = _force_fire()
    obs_id = log_observation(
        spectrum="initiative",
        position=0.1,
        evidence=(
            "artifact_reference: PR #195\n"
            "wired: yes\n"
            "the rudder redesign Phase 1a now blocks fire_id-as-artifact gaming\n"
        ),
        tags=["rudder-ack"],
        fire_id=fire_id,
    )
    assert obs_id


# ---------- fire_id exclusion threaded through ----------


def test_enforce_mode_rejects_fire_id_as_artifact_reference():
    """The Phase 1a fire_id exclusion is wired through the live path."""
    os.environ["DIVINEOS_RUDDER_CONTRACT_MODE"] = "enforce"
    fire_id = _force_fire()
    with pytest.raises(ValueError, match="contract check"):
        log_observation(
            spectrum="initiative",
            position=0.1,
            evidence=(
                f"artifact_reference: {fire_id}\n"
                "wired: yes\n"
                "this should fail because the artifact_reference IS the fire_id\n"
            ),
            tags=["rudder-ack"],
            fire_id=fire_id,
        )


# ---------- retraction event ----------


def test_retracted_emits_rudder_ack_retracted_event():
    os.environ["DIVINEOS_RUDDER_CONTRACT_MODE"] = "enforce"
    fire_id = _force_fire()
    obs_id = log_observation(
        spectrum="initiative",
        position=0.1,
        evidence=(
            "artifact_reference: PR #195\n"
            "wired: retracted\n"
            "next: re-verify the consumer is actually attached and re-ack honestly\n"
        ),
        tags=["rudder-ack"],
        fire_id=fire_id,
    )
    retractions = get_events(event_type="RUDDER_ACK_RETRACTED", limit=5)
    assert len(retractions) == 1
    p = retractions[0].get("payload") or {}
    assert p["spectrum"] == "initiative"
    assert p["fire_id"] == fire_id
    assert p["observation_id"] == obs_id  # forensic pointer to the retracting ack
    assert p["artifact_reference"] == "PR #195"
    assert "re-verify" in (p["next_plan"] or "")


def test_yes_does_not_emit_retraction_event():
    os.environ["DIVINEOS_RUDDER_CONTRACT_MODE"] = "enforce"
    fire_id = _force_fire()
    log_observation(
        spectrum="initiative",
        position=0.1,
        evidence=(
            "artifact_reference: PR #195\n"
            "wired: yes\n"
            "phase 1a passed review with both confirms; merging unblocked phase 1b\n"
        ),
        tags=["rudder-ack"],
        fire_id=fire_id,
    )
    assert get_events(event_type="RUDDER_ACK_RETRACTED", limit=5) == []


def test_observe_mode_retracted_does_not_emit_when_legacy_alone_persists():
    """Observe-mode: retraction event only fires when contract parsed and legacy passed.

    If the contract check parsed wired=retracted AND legacy passed, the
    write commits and the retraction event fires. (The brief makes
    retraction observable even in observe-mode; the dishonesty arc is
    the high-value signal.)
    """
    os.environ["DIVINEOS_RUDDER_CONTRACT_MODE"] = "observe"
    fire_id = _force_fire()
    log_observation(
        spectrum="initiative",
        position=0.1,
        evidence=(
            "artifact_reference: PR #195\n"
            "wired: retracted\n"
            "next: reopen and re-verify the consumer attachment honestly\n"
        ),
        tags=["rudder-ack"],
        fire_id=fire_id,
    )
    retractions = get_events(event_type="RUDDER_ACK_RETRACTED", limit=5)
    assert len(retractions) == 1


# ---------- unknown flag value falls back to off ----------


def test_unknown_flag_value_falls_back_to_off():
    """Typos like 'enable' or 'on' must not silently enforce."""
    os.environ["DIVINEOS_RUDDER_CONTRACT_MODE"] = "enable"
    fire_id = _force_fire()
    # A contract-malformed but legacy-substantive ack must commit (no enforcement).
    log_observation(
        spectrum="initiative",
        position=0.1,
        evidence="long substantive prose with no contract fields whatsoever included here",
        tags=["rudder-ack"],
        fire_id=fire_id,
    )
    assert get_events(event_type="CONTRACT_DUAL_RUN_DISCREPANCY", limit=5) == []
