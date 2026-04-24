"""Tests for contract-style rudder-ack substance checks (Phase 1a).

Pure-function tests — no DB, no fixtures, no mocks. The module under
test is deliberately side-effect-free so this stays small.
"""

from __future__ import annotations

from divineos.core.substance_checks_contract import (
    SIMILARITY_THRESHOLD,
    WIRE_STATUS_VALUES,
    check_contract_ack,
    parse_contract,
)


# ---------- parse_contract ----------


def test_parse_full_contract():
    evidence = (
        "artifact_reference: PR #194\n"
        "wired: yes\n"
        "next: observe Phase 5 summary renders honestly\n"
        "depends_on: sleep.py Phase 5 fix\n"
    )
    parsed = parse_contract(evidence)
    assert parsed.artifact_reference == "PR #194"
    assert parsed.wired == "yes"
    assert parsed.next_plan.startswith("observe Phase 5")
    assert parsed.depends_on == "sleep.py Phase 5 fix"


def test_parse_missing_fields_return_none():
    parsed = parse_contract("some freeform text\nwith no contract fields")
    assert parsed.artifact_reference is None
    assert parsed.wired is None
    assert parsed.next_plan is None
    assert parsed.depends_on is None


def test_parse_invalid_wired_value_rejected():
    parsed = parse_contract("wired: maybe")
    assert parsed.wired is None


def test_parse_wired_accepts_all_four_values():
    for v in WIRE_STATUS_VALUES:
        parsed = parse_contract(f"wired: {v}")
        assert parsed.wired == v


def test_parse_case_insensitive_keys_and_values():
    parsed = parse_contract("Artifact_Reference: PR #1\nWIRED: Yes")
    assert parsed.artifact_reference == "PR #1"
    assert parsed.wired == "yes"


# ---------- _check_artifact_reference ----------


def _base(wired="yes", next_plan=None, extra=""):
    out = f"artifact_reference: PR #42\nwired: {wired}\n"
    if next_plan:
        out += f"next: {next_plan}\n"
    out += extra
    return out


def test_missing_artifact_reference_fails():
    ev = "wired: yes\n"
    result = check_contract_ack(ev)
    assert not result.ok
    assert result.stage == "artifact"


def test_narrative_artifact_reference_fails():
    ev = "artifact_reference: the thing we were working on\nwired: yes\n"
    result = check_contract_ack(ev)
    assert not result.ok
    assert result.stage == "artifact"


def test_pr_number_artifact_passes():
    result = check_contract_ack(_base())
    assert result.ok, result.reason


def test_commit_hash_artifact_passes():
    ev = "artifact_reference: b826950\nwired: yes\n"
    result = check_contract_ack(ev)
    assert result.ok, result.reason


def test_file_path_artifact_passes():
    ev = "artifact_reference: src/divineos/core/sleep.py\nwired: yes\n"
    result = check_contract_ack(ev)
    assert result.ok, result.reason


def test_named_feature_artifact_passes():
    ev = "artifact_reference: Rudder-Redesign-Phase-1a\nwired: yes\n"
    result = check_contract_ack(ev)
    assert result.ok, result.reason


def test_snake_case_artifact_passes():
    ev = "artifact_reference: substance_checks_contract_module\nwired: yes\n"
    result = check_contract_ack(ev)
    assert result.ok, result.reason


# ---------- _check_wire_status ----------


def test_missing_wire_status_fails():
    ev = "artifact_reference: PR #42\n"
    result = check_contract_ack(ev)
    assert not result.ok
    assert result.stage == "wire_status"


def test_invalid_wire_status_fails():
    ev = "artifact_reference: PR #42\nwired: kinda\n"
    result = check_contract_ack(ev)
    assert not result.ok
    assert result.stage == "wire_status"


def test_retracted_wire_status_requires_next():
    ev = "artifact_reference: PR #42\nwired: retracted\n"
    result = check_contract_ack(ev)
    assert not result.ok
    assert result.stage == "next_commitment"


def test_retracted_with_next_passes():
    ev = "artifact_reference: PR #42\nwired: retracted\nnext: reopen and re-verify consumer\n"
    result = check_contract_ack(ev)
    assert result.ok, result.reason
    assert result.parsed.wired == "retracted"


# ---------- _check_next_commitment ----------


def test_partial_without_next_fails():
    ev = _base(wired="partial")
    result = check_contract_ack(ev)
    assert not result.ok
    assert result.stage == "next_commitment"


def test_no_without_next_fails():
    ev = _base(wired="no")
    result = check_contract_ack(ev)
    assert not result.ok
    assert result.stage == "next_commitment"


def test_partial_with_next_passes():
    ev = _base(wired="partial", next_plan="wire consumer in follow-up PR")
    result = check_contract_ack(ev)
    assert result.ok, result.reason


def test_yes_without_next_passes():
    ev = _base(wired="yes")
    result = check_contract_ack(ev)
    assert result.ok, result.reason


# ---------- similarity ----------


def test_similarity_skipped_without_priors():
    ev = _base()
    result = check_contract_ack(ev, prior_evidences=[])
    assert result.ok
    assert result.stage == "pass"


def test_different_artifacts_same_scaffold_pass_similarity():
    """Key property: PR #42 ack and PR #43 ack with shared prose must NOT collide."""
    prior = (
        "artifact_reference: PR #42\n"
        "wired: yes\n"
        "this tightens the length-floor detector by calibrating against clean baselines\n"
    )
    new = (
        "artifact_reference: PR #43\n"
        "wired: yes\n"
        "this wires up the completion-boundary event into the moral compass observer\n"
    )
    result = check_contract_ack(new, prior_evidences=[prior])
    assert result.ok, f"unexpected similarity reject: {result.reason}"


def test_near_duplicate_reflection_prose_fails_similarity():
    prior = (
        "artifact_reference: PR #42\n"
        "wired: yes\n"
        "shifted the rudder to attest wire-up rather than elapsed time\n"
    )
    # Same reflection, different artifact + scaffold.
    new = (
        "artifact_reference: PR #43\n"
        "wired: yes\n"
        "shifted the rudder to attest wire-up rather than elapsed time\n"
    )
    result = check_contract_ack(new, prior_evidences=[prior])
    assert not result.ok
    assert result.stage == "similarity"
    assert "cosine" in result.reason


def test_similarity_threshold_boundary():
    """A literal copy-paste should cosine ≥ threshold; a genuine paraphrase should pass."""
    prior = (
        "artifact_reference: PR #1\n"
        "wired: yes\n"
        "the length-floor detector now calibrates against externally audited clean sessions\n"
    )
    copy = (
        "artifact_reference: PR #2\n"
        "wired: yes\n"
        "the length-floor detector now calibrates against externally audited clean sessions\n"
    )
    paraphrase = (
        "artifact_reference: PR #3\n"
        "wired: yes\n"
        "baseline calibration replaced conceptual thresholds for rapid-clear reflex\n"
    )
    assert not check_contract_ack(copy, prior_evidences=[prior]).ok
    assert check_contract_ack(paraphrase, prior_evidences=[prior]).ok


# ---------- end-to-end ----------


def test_full_pass_attaches_parsed():
    ev = _base(wired="partial", next_plan="finish wiring in Phase 1b", extra="depends_on: #191\n")
    result = check_contract_ack(ev)
    assert result.ok
    assert result.stage == "pass"
    assert result.parsed is not None
    assert result.parsed.artifact_reference == "PR #42"
    assert result.parsed.wired == "partial"
    assert result.parsed.depends_on == "#191"


def test_first_failing_stage_short_circuits():
    """Missing artifact_reference fails before wire_status is even checked."""
    ev = ""  # everything missing
    result = check_contract_ack(ev)
    assert not result.ok
    assert result.stage == "artifact"  # first stage, not wire_status


def test_threshold_constant_sane():
    assert 0.0 < SIMILARITY_THRESHOLD <= 1.0


# ---------- fire_id exclusion (brief v2.1 refinement 4) ----------


def test_fire_id_as_artifact_reference_rejected():
    """An agent writing artifact_reference: <fire_id> must not pass.

    Without exclusion, a 16-hex fire_id matches the commit-hash
    pattern and trivially satisfies the artifact check — exactly the
    gaming vector the brief committed to closing.
    """
    fire_id = "a3f2c9b1e4d70625"  # 16 hex
    ev = f"artifact_reference: {fire_id}\nwired: yes\n"
    # Without fire_id exclusion: passes (gaming).
    assert check_contract_ack(ev).ok
    # With fire_id passed: artifact stage rejects.
    result = check_contract_ack(ev, current_fire_id=fire_id)
    assert not result.ok
    assert result.stage == "artifact"


def test_fire_id_exclusion_case_insensitive():
    fire_id = "a3f2c9b1e4d70625"
    ev = f"artifact_reference: {fire_id.upper()}\nwired: yes\n"
    result = check_contract_ack(ev, current_fire_id=fire_id)
    assert not result.ok
    assert result.stage == "artifact"


def test_fire_id_exclusion_does_not_break_real_artifacts():
    """A real PR # alongside an incidental fire_id mention still passes."""
    fire_id = "a3f2c9b1e4d70625"
    ev = f"artifact_reference: PR #195 (responding to fire {fire_id})\nwired: yes\n"
    result = check_contract_ack(ev, current_fire_id=fire_id)
    assert result.ok, result.reason


def test_fire_id_none_preserves_legacy_behaviour():
    """current_fire_id=None means no exclusion — backwards-compatible default."""
    fire_id = "a3f2c9b1e4d70625"
    ev = f"artifact_reference: {fire_id}\nwired: yes\n"
    assert check_contract_ack(ev, current_fire_id=None).ok
