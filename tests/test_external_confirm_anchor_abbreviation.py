"""An abbreviated anchor names the same change; a different one does not.

Written 2026-09-02, from a live refusal. Aletheia relayed CONFIRMs on five
requests, having recomputed every patch-id independently from the base each
named and matched all five. Every one was refused with "The reviewed CHANGE
changed."

Nothing had changed. I had sent her the patch-ids truncated to sixteen
characters, she reported back the form I gave her, and the comparison was
exact string equality. So a correct review of an unchanged branch was
rejected, and rejected with a cause the check had never tested.

Two properties, and the refusals matter as much as the permissions:

  - A valid abbreviation is the same identifier. Git treats it that way
    everywhere else and so must this.
  - A genuinely different anchor is STILL refused. Loosening the comparison
    must not loosen the safety property the rung exists for.
"""

from __future__ import annotations

from divineos.cli.audit_commands import (
    _MIN_ANCHOR_PREFIX,
    validate_external_confirm_inputs,
)

# The real values from the live incident.
FULL = "d11502c510b17cadc64d753277e992b81f35bbbb"
ABBREV = "d11502c510b17cad"


def _validate(claimed: str, actual: str = FULL):
    return validate_external_confirm_inputs(
        actor="aletheia",
        claimed_patch_id=claimed,
        actual_patch_id=actual,
    )


def test_abbreviated_patch_id_is_accepted():
    """The exact case that was refused in the field."""
    ok, message, rung = _validate(ABBREV)
    assert ok, f"an abbreviation of the same patch-id must be accepted: {message}"
    assert rung == "patch-id-after-catchup"


def test_full_patch_id_still_accepted():
    ok, _message, rung = _validate(FULL)
    assert ok
    assert rung == "patch-id-after-catchup"


def test_a_genuinely_different_patch_id_is_still_refused():
    """The safety property. Prefix-tolerance must not become anything-goes."""
    other = "ffffffffffffffffffffffffffffffffffffffff"
    ok, message, rung = _validate(other)
    assert not ok
    assert rung == ""
    assert "CHANGE changed" in message


def test_same_length_but_wrong_prefix_is_refused():
    """One character off is a different change, not an abbreviation."""
    wrong = "e11502c510b17cad"
    ok, _message, rung = _validate(wrong)
    assert not ok
    assert rung == ""


def test_too_short_is_unjudgeable_and_says_so():
    """Could-not-tell must never be reported as evidence the change moved.

    This is the half that makes the repair honest rather than merely
    permissive: below the minimum the answer is unknown, and the message
    has to say unknown rather than borrowing the language of a failure.
    """
    ok, message, rung = _validate(FULL[: _MIN_ANCHOR_PREFIX - 1])
    assert not ok
    assert rung == ""
    assert "NOT evidence the change moved" in message
    assert "CHANGE changed" not in message


def test_minimum_length_prefix_is_judgeable():
    ok, message, _rung = _validate(FULL[:_MIN_ANCHOR_PREFIX])
    assert ok, message
