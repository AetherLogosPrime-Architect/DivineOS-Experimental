"""Tests for validate_external_confirm_inputs — the both-bind (tree-hash +
patch-id) integrity ladder for filing/holding relayed external-AI CONFIRMs.

Aletheia's correction 2026-06-02: bind BOTH tree-hash and patch-id, never
replace tree with patch-id (that would recreate the diff-hash cross-vantage
trap, claim 1d0f9e7b). Validation is a ladder:
  1. tree-hash matches            -> 'tree-exact'              (strongest)
  2. tree differs, patch-id match -> 'patch-id-after-catchup'  (treadmill-killer)
  3. patch-id differs             -> refuse                    (safety: re-sign)
"""

from divineos.cli.audit_commands import (
    _EXTERNAL_AI_ACTORS,
    validate_external_confirm_inputs,
)

TREE = "86e5ef9193abcb3fe05596eb08931c52374d1e38"
TREE2 = "c853630cf073d03ec5735bfa39bc1edde641aa97"  # a different (caught-up) tree
PATCH = "7466992d29ebfe37b4eda0f5381771f52c680cff"
TIP = "30cc70570279f2deb162efd28fff49b91b8becd9"


# ── Rung 1: tree-exact ────────────────────────────────────────────────────
def test_rung1_tree_exact_match():
    ok, reason, basis = validate_external_confirm_inputs(
        actor="aletheia", claimed_tree=TREE, actual_tree=TREE
    )
    assert ok is True
    assert basis == "tree-exact"


def test_rung1_tree_exact_is_case_insensitive():
    ok, _, basis = validate_external_confirm_inputs(
        actor="aletheia", claimed_tree=TREE.upper(), actual_tree=TREE.lower()
    )
    assert ok is True
    assert basis == "tree-exact"


# ── Rung 2: patch-id-after-catchup (the treadmill-killer) ─────────────────
def test_rung2_tree_differs_but_patch_id_matches_after_catchup():
    # The catch-up moved the tree; the reviewed change (patch-id) is unchanged.
    ok, reason, basis = validate_external_confirm_inputs(
        actor="aletheia",
        claimed_tree=TREE,
        actual_tree=TREE2,  # tree moved (caught up)
        claimed_patch_id=PATCH,
        actual_patch_id=PATCH,  # but the change is the same
    )
    assert ok is True
    assert basis == "patch-id-after-catchup"
    assert "no re-sign" in reason


# ── Rung 3: patch-id differs -> refuse (the safety property) ──────────────
def test_rung3_patch_id_differs_refuses_resign_required():
    # A conflict-resolution during catch-up altered a guardrail file.
    ok, reason, basis = validate_external_confirm_inputs(
        actor="aletheia",
        claimed_tree=TREE,
        actual_tree=TREE2,
        claimed_patch_id=PATCH,
        actual_patch_id="0000000000000000000000000000000000000000",
    )
    assert ok is False
    assert basis == ""
    assert "re-sign required" in reason


# ── Actor gating ──────────────────────────────────────────────────────────
def test_rejects_non_external_ai_actor():
    ok, reason, basis = validate_external_confirm_inputs(
        actor="user", claimed_tree=TREE, actual_tree=TREE
    )
    assert ok is False
    assert "external-AI" in reason


def test_rejects_audited_agent_actor():
    ok, reason, _ = validate_external_confirm_inputs(
        actor="aether", claimed_tree=TREE, actual_tree=TREE
    )
    assert ok is False
    assert "external-AI" in reason


# ── Anchor requirements ───────────────────────────────────────────────────
def test_rejects_when_no_anchor_supplied():
    ok, reason, _ = validate_external_confirm_inputs(
        actor="aletheia", claimed_tree="", claimed_patch_id=""
    )
    assert ok is False
    assert "anchor" in reason


def test_tree_unresolved_but_patch_id_matches_is_still_valid():
    # tree couldn't be resolved (None) but patch-id matches -> catch-up rung.
    ok, _, basis = validate_external_confirm_inputs(
        actor="aletheia",
        claimed_tree=TREE,
        actual_tree=None,
        claimed_patch_id=PATCH,
        actual_patch_id=PATCH,
    )
    assert ok is True
    assert basis == "patch-id-after-catchup"


def test_no_match_on_either_anchor_refuses():
    ok, reason, _ = validate_external_confirm_inputs(
        actor="aletheia",
        claimed_tree=TREE,
        actual_tree=TREE2,  # tree differs
        # no patch-id supplied -> nothing to fall back to
    )
    assert ok is False
    assert "no anchor matched" in reason


# ── tip cross-check on the tree-exact rung ────────────────────────────────
def test_tree_exact_with_tip_mismatch_refuses():
    ok, reason, _ = validate_external_confirm_inputs(
        actor="aletheia",
        claimed_tree=TREE,
        actual_tree=TREE,
        claimed_tip="deadbeef" + "0" * 32,
        actual_tip=TIP,
    )
    assert ok is False
    assert "tip" in reason.lower()


# ── roster ────────────────────────────────────────────────────────────────
def test_all_canonical_external_ai_actors_accepted_on_tree_exact():
    for actor in _EXTERNAL_AI_ACTORS:
        ok, _, basis = validate_external_confirm_inputs(
            actor=actor, claimed_tree=TREE, actual_tree=TREE
        )
        assert ok is True and basis == "tree-exact", f"{actor} should be accepted"
