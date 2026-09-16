"""Preflight refuses to pass a checkout with nowhere to put substrate.

THE INCIDENT, 2026-09-15. The retarget asks each checkout where substrate
belongs, deliberately per-checkout with no default, because two clones of this
repository keep substrate in different places and a value baked into the source
would be wrong for one of them at all times. When the answer is missing the
checkpoint refuses -- which is correct, since falling back to the code branch
is the exact contamination the mechanism exists to prevent.

The refusal is silent by construction. Nothing is lost and nothing looks wrong;
the letters and dreams simply stay on the floor, and every later sweep picks
them up and puts them down again. Two hundred and eighty-five paths had
accumulated that way in one checkout before anyone asked.

WHAT WAS ACTUALLY BROKEN is not the missing value. It is that a REQUIRED value
could be missing for weeks with no surface asking. Searched at the time: the
setting was defined in one module, consumed in one module, and verified in
zero. Preflight ran clean the whole while, because a question nobody asks has
no wrong answer.

So the tests below come in two halves and the second is the one that matters. A
check that passes on a healthy tree proves nothing -- every other preflight
check also passed a tree with no substrate destination at all, which is how
this ran undetected.
"""

from __future__ import annotations

import pytest

from divineos.core import substrate_paths
from divineos.core.hud_handoff import preflight_check


def _substrate_check(result: dict) -> dict:
    for check in result["checks"]:
        if check["name"] == "substrate_destination":
            return check
    pytest.fail("preflight does not run a substrate_destination check at all")


def test_a_declared_destination_passes_and_names_it(monkeypatch):
    monkeypatch.setattr(substrate_paths, "substrate_branch", lambda root: "substrate/somewhere")

    check = _substrate_check(preflight_check())

    assert check["passed"] is True
    assert "substrate/somewhere" in check["detail"]


def test_an_undeclared_destination_fails_preflight(monkeypatch):
    """The sick case. Without this the check is decoration."""

    def undeclared(root):
        raise substrate_paths.NoSubstrateBranchDeclared(
            "divineos.substrate-branch is not set in this repo. Set it with: "
            "git config divineos.substrate-branch <branch>"
        )

    monkeypatch.setattr(substrate_paths, "substrate_branch", undeclared)

    check = _substrate_check(preflight_check())

    assert check["passed"] is False
    # The remedy travels with the finding. A door that only says NO spends the
    # reader's attention at the moment they have least of it, and spends it on
    # a search -- which is the shape this repository keeps paying for.
    assert "git config divineos.substrate-branch" in check["detail"]


def test_could_not_look_is_not_reported_as_a_finding(monkeypatch):
    """An unreadable repo is unknown, not unset, and must not read as unset.

    The two are opposite instructions to whoever is standing there: one says go
    and declare a branch, the other says something is wrong with the tooling.
    Collapsing them is the same fault this area keeps producing -- an
    instrument's own failure delivered in the subject's voice.
    """

    def cannot_look(root):
        raise OSError("git is not on PATH")

    monkeypatch.setattr(substrate_paths, "substrate_branch", cannot_look)

    check = _substrate_check(preflight_check())

    assert check["passed"] is True
    assert "skipped" in check["detail"].lower()
